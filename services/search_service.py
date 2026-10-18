import asyncio
import csv
import io
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import Settings
from core.db.models import LeadORM, SearchSessionORM
from core.search.connectors.dadata import DaDataConnector
from core.search.connectors.dgis import DGISConnector
from core.search.connectors.fns_egr import FnsEgrConnector
from core.search.connectors.http_client import PoliteHttpClient
from core.search.connectors.registry import RegistryConnector
from core.search.connectors.zakupki import ZakupkiConnector
from core.search.constants import CHECKBOX_GROUPS, EXTRA_FIELDS
from core.search.okved_mapping import resolve_primary_segment
from core.search.schemas import (
    ExportRequest,
    FiltersMetaResponse,
    GroupOption,
    LeadCard,
    LeadGroup,
    ScoreBreakdownItem,
    SearchFilters,
    SearchMoreRequest,
    SearchRunRequest,
    SearchRunResponse,
    SortOption,
)
from core.search.scoring import LeadScorer, RawLeadCandidate, ScoredLead

logger = logging.getLogger(__name__)

SEGMENT_TITLES = {
    "installer": "Монтаж",
    "designer": "Проектирование",
    "contractor": "Генподряд / строительство",
    "industrial": "Промышленность",
}

REGION_BUCKETS = {
    "поволж": "Поволжье",
    "самар": "Поволжье",
    "урал": "Урал",
    "екатеринбург": "Урал",
    "сибир": "Сибирь",
    "моск": "ЦФО",
    "цфо": "ЦФО",
}


class SearchService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._scorer = LeadScorer(settings)
        self._http = PoliteHttpClient(settings)
        self._zakupki = ZakupkiConnector(settings, self._http)
        self._fns = FnsEgrConnector(settings, self._http)
        self._registry = RegistryConnector(settings, self._http)
        self._dgis = DGISConnector(settings, self._http)
        self._dadata = DaDataConnector(settings)

    async def close(self) -> None:
        await self._http.close()

    def filters_meta(self) -> FiltersMetaResponse:
        return FiltersMetaResponse(
            checkbox_groups=CHECKBOX_GROUPS,
            extra_fields=EXTRA_FIELDS,
            sort_options=[
                {"id": SortOption.SCORE_DESC.value, "label": "По скорингу (сначала горячие)"},
                {"id": SortOption.NAME_ASC.value, "label": "По алфавиту"},
                {"id": SortOption.REGION_ASC.value, "label": "По региону"},
                {"id": SortOption.UPDATED_DESC.value, "label": "По дате обновления"},
            ],
            group_options=[
                {"id": GroupOption.NONE.value, "label": "Без группировки"},
                {"id": GroupOption.SEGMENT.value, "label": "По сегменту"},
                {"id": GroupOption.REGION.value, "label": "По региону"},
            ],
        )

    async def run_search(
        self,
        session: AsyncSession,
        request: SearchRunRequest,
    ) -> SearchRunResponse:
        session_id = uuid.uuid4()
        candidates = await self._collect_candidates(request.filters)
        scored = self._score_and_filter(candidates, request.filters)
        if not scored:
            scored = self._demo_candidates(request.filters)

        db_session = SearchSessionORM(
            id=session_id,
            user_role=request.user_role,
            filters=request.filters.model_dump(),
            comment=request.filters.extra.search_comment,
            total_found=len(scored),
        )
        session.add(db_session)
        lead_rows = [self._to_orm(session_id, item) for item in scored]
        session.add_all(lead_rows)
        await session.commit()

        page = self._paginate_rows(
            lead_rows,
            exclude_ids=set(),
            sort_by=request.sort_by,
            group_by=request.group_by,
        )
        return SearchRunResponse(
            session_id=session_id,
            leads=page["leads"],
            groups=page.get("groups"),
            shown_count=page["shown_count"],
            total_count=page["total_count"],
            has_more=page["has_more"],
        )

    async def load_more(
        self,
        session: AsyncSession,
        request: SearchMoreRequest,
    ) -> SearchRunResponse:
        result = await session.execute(
            select(LeadORM).where(LeadORM.session_id == request.session_id)
        )
        all_rows = list(result.scalars().all())
        if not all_rows:
            raise ValueError(f"Session {request.session_id} not found")

        exclude_ids = {UUID(str(i)) for i in request.exclude_lead_ids}
        page = self._paginate_rows(
            all_rows,
            exclude_ids=exclude_ids,
            sort_by=request.sort_by,
            group_by=request.group_by,
        )
        return SearchRunResponse(
            session_id=request.session_id,
            leads=page["leads"],
            groups=page.get("groups"),
            shown_count=len(all_rows) - len(exclude_ids),
            total_count=len(all_rows),
            has_more=page["has_more"],
        )

    async def export(
        self,
        session: AsyncSession,
        request: ExportRequest,
    ) -> tuple[bytes, str, str]:
        result = await session.execute(
            select(LeadORM).where(LeadORM.session_id == request.session_id)
        )
        rows = list(result.scalars().all())
        if request.lead_ids:
            rows = [r for r in rows if r.id in request.lead_ids]

        return self._export_csv(rows), "text/csv; charset=utf-8", "search.csv"

    async def _collect_candidates(
        self,
        filters: SearchFilters,
    ) -> list[RawLeadCandidate]:
        if not self._settings.search_use_live_sources:
            return []

        results = await asyncio.gather(
            self._zakupki.fetch(filters),
            self._fns.fetch(filters),
            self._registry.fetch(filters),
            self._dgis.fetch(filters),
            self._dadata.fetch(filters),
            return_exceptions=True,
        )
        merged: dict[str, RawLeadCandidate] = {}
        for batch in results:
            if isinstance(batch, Exception):
                logger.warning("Connector error: %s", batch)
                continue
            for candidate in batch:
                key = candidate.inn or candidate.company_name.lower()
                existing = merged.get(key)
                if existing:
                    merged[key] = self._merge_candidates(existing, candidate)
                else:
                    merged[key] = candidate
        candidates = list(merged.values())
        await self._dadata.enrich(candidates)
        return candidates

    def _merge_candidates(
        self,
        left: RawLeadCandidate,
        right: RawLeadCandidate,
    ) -> RawLeadCandidate:
        return RawLeadCandidate(
            company_name=left.company_name or right.company_name,
            inn=left.inn or right.inn,
            ogrn=left.ogrn or right.ogrn,
            segment=left.segment or right.segment,
            region=left.region or right.region,
            source=f"{left.source}+{right.source}",
            okved_codes=sorted(set(left.okved_codes + right.okved_codes)),
            turnover_mln=left.turnover_mln or right.turnover_mln,
            employees=left.employees or right.employees,
            website=left.website or right.website,
            contact_name=left.contact_name or right.contact_name,
            contact_phone=left.contact_phone or right.contact_phone,
            contact_email=left.contact_email or right.contact_email,
            has_tenders_12m=left.has_tenders_12m or right.has_tenders_12m,
            has_sro=left.has_sro or right.has_sro,
            has_website=left.has_website or right.has_website,
            web_active_6m=left.web_active_6m or right.web_active_6m,
            vent_mention=left.vent_mention or right.vent_mention,
            company_age_years=left.company_age_years or right.company_age_years,
            is_legal_entity=left.is_legal_entity and right.is_legal_entity,
            not_bankrupt=left.not_bankrupt and right.not_bankrupt,
            has_portfolio=left.has_portfolio or right.has_portfolio,
            multi_region=left.multi_region or right.multi_region,
            raw_data={**left.raw_data, **right.raw_data},
        )

    def _score_and_filter(
        self,
        candidates: list[RawLeadCandidate],
        filters: SearchFilters,
    ) -> list[ScoredLead]:
        scored = []
        for candidate in candidates:
            scored_item = self._scorer.score(candidate, filters)
            if scored_item.score >= 10:
                scored.append(scored_item)
        return scored

    def _to_orm(
        self,
        session_id: UUID,
        scored_item: ScoredLead,
    ) -> LeadORM:
        c = scored_item.candidate
        return LeadORM(
            id=uuid.uuid4(),
            session_id=session_id,
            company_name=c.company_name,
            inn=c.inn,
            ogrn=c.ogrn,
            segment=c.segment,
            region=c.region,
            source=c.source,
            score=scored_item.score,
            score_breakdown=[item.model_dump() for item in scored_item.breakdown],
            turnover_mln=Decimal(str(c.turnover_mln)) if c.turnover_mln else None,
            employees=c.employees,
            website=c.website,
            contact_name=c.contact_name,
            contact_phone=c.contact_phone,
            contact_email=c.contact_email,
            okved_codes=c.okved_codes,
            raw_data=c.raw_data,
        )

    def _paginate_rows(
        self,
        lead_rows: list[LeadORM],
        exclude_ids: set[UUID],
        sort_by: SortOption,
        group_by: GroupOption,
        page_size: int = 20,
    ) -> dict[str, Any]:
        visible = [r for r in lead_rows if r.id not in exclude_ids]
        visible = self._sort_rows(visible, sort_by)

        if group_by != GroupOption.NONE:
            groups = self._group_rows(visible, group_by)
            all_leads = [lead for g in groups for lead in g.leads]
            page = all_leads[:page_size]
            return {
                "leads": page,
                "groups": groups,
                "shown_count": len(page),
                "total_count": len(visible),
                "has_more": len(all_leads) > page_size,
            }

        page = [self._orm_to_card(r) for r in visible[:page_size]]
        return {
            "leads": page,
            "shown_count": len(page),
            "total_count": len(visible),
            "has_more": len(visible) > page_size,
        }

    def _group_rows(
        self,
        lead_rows: list[LeadORM],
        group_by: GroupOption,
    ) -> list[LeadGroup]:
        buckets: defaultdict[str, list[LeadORM]] = defaultdict(list)
        for row in lead_rows:
            if group_by == GroupOption.SEGMENT:
                key = row.segment or "unknown"
            elif group_by == GroupOption.REGION:
                key = self._region_bucket(row.region) or "unknown"
            else:
                key = "all"
            buckets[key].append(row)

        groups = []
        for key, rows in sorted(buckets.items()):
            title = SEGMENT_TITLES.get(key, key) if group_by == GroupOption.SEGMENT else key
            groups.append(
                LeadGroup(
                    key=key,
                    title=title,
                    leads=[self._orm_to_card(r) for r in rows],
                )
            )
        return groups

    def _sort_rows(
        self,
        lead_rows: list[LeadORM],
        sort_by: SortOption,
    ) -> list[LeadORM]:
        if sort_by == SortOption.SCORE_DESC:
            return sorted(lead_rows, key=lambda r: (-r.score, r.company_name))
        if sort_by == SortOption.NAME_ASC:
            return sorted(lead_rows, key=lambda r: r.company_name or "")
        if sort_by == SortOption.REGION_ASC:
            return sorted(lead_rows, key=lambda r: r.region or "")
        if sort_by == SortOption.UPDATED_DESC:
            return sorted(lead_rows, key=lambda r: r.created_at or datetime.min, reverse=True)
        return lead_rows

    def _demo_candidates(self, filters: SearchFilters) -> list[ScoredLead]:
        segment = resolve_primary_segment(filters.checkboxes)
        demos = [
            RawLeadCandidate(
                company_name="ООО ВентПроект",
                inn="6312345678",
                segment=segment,
                region="Самарская область",
                source="demo",
                okved_codes=["43.22", "71.12"],
                turnover_mln=120.5,
                employees=85,
                website="https://ventproekt.ru",
                contact_name="Иванов А.В.",
                contact_phone="+7 (846) 123-45-67",
                contact_email="info@ventproekt.ru",
                has_tenders_12m=True,
                has_sro=True,
                has_website=True,
                web_active_6m=True,
                vent_mention=True,
                company_age_years=8,
                is_legal_entity=True,
                not_bankrupt=True,
                has_portfolio=True,
                multi_region=False,
            ),
            RawLeadCandidate(
                company_name="АО МонтажСтрой",
                inn="7709876543",
                segment="contractor",
                region="Москва",
                source="demo",
                okved_codes=["41.20", "43.22"],
                turnover_mln=450.0,
                employees=320,
                website="https://montazhstroy.ru",
                contact_name="Петров С.И.",
                contact_phone="+7 (495) 987-65-43",
                has_tenders_12m=True,
                has_sro=True,
                has_website=True,
                vent_mention=True,
                company_age_years=15,
                is_legal_entity=True,
                not_bankrupt=True,
            ),
            RawLeadCandidate(
                company_name="ООО УралВент",
                inn="6601234567",
                segment="installer",
                region="Свердловская область",
                source="demo",
                okved_codes=["43.22"],
                turnover_mln=65.0,
                employees=42,
                website="https://uralvent.ru",
                contact_name="Сидоров М.П.",
                contact_phone="+7 (343) 111-22-33",
                has_tenders_12m=False,
                has_sro=True,
                has_website=True,
                vent_mention=True,
                company_age_years=5,
                is_legal_entity=True,
                not_bankrupt=True,
            ),
        ]
        scored = []
        for candidate in demos:
            scored_item = self._scorer.score(candidate, filters)
            scored.append(scored_item)
        return scored

    def _region_bucket(self, region: str | None) -> str | None:
        if not region:
            return None
        region_lower = region.lower()
        for key, bucket in REGION_BUCKETS.items():
            if key in region_lower:
                return bucket
        return region

    def _orm_to_card(self, row: LeadORM) -> LeadCard:
        breakdown = [
            ScoreBreakdownItem(**item) if isinstance(item, dict) else item
            for item in (row.score_breakdown or [])
        ]
        return LeadCard(
            lead_id=row.id,
            company_name=row.company_name,
            inn=row.inn,
            segment=row.segment,
            region=row.region,
            score=row.score,
            score_breakdown=breakdown,
            turnover_mln=float(row.turnover_mln) if row.turnover_mln else None,
            employees=row.employees,
            website=row.website,
            contact_name=row.contact_name,
            contact_phone=row.contact_phone,
            contact_email=row.contact_email,
            source=row.source,
            updated_at=row.updated_at_source.isoformat() if row.updated_at_source else None,
        )

    def _export_csv(self, rows: list[LeadORM]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "lead_id",
                "company_name",
                "inn",
                "segment",
                "region",
                "score",
                "turnover_mln",
                "employees",
                "website",
                "contact_name",
                "contact_phone",
                "contact_email",
                "source",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    str(row.id),
                    row.company_name,
                    row.inn or "",
                    row.segment,
                    row.region or "",
                    row.score,
                    float(row.turnover_mln) if row.turnover_mln else "",
                    row.employees or "",
                    row.website or "",
                    row.contact_name or "",
                    row.contact_phone or "",
                    row.contact_email or "",
                    row.source,
                ]
            )
        return buffer.getvalue().encode("utf-8-sig")
