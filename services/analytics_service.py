import csv
import io
import logging
import uuid
from datetime import datetime, timezone

# from openpyxl import Workbook  # Disabled
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.question_generator import QuestionGenerator
from core.analytics.report_builder import ReportBuilder
from core.analytics.schemas import (
    AnalyticsExportRequest,
    AnalyticsReport,
    AnalyticsRunRequest,
    AnalyticsRunResponse,
    MarkInWorkRequest,
    RecommendedQuestion,
)
from core.config.settings import Settings
from core.db.models import AnalyticsReportORM, LeadORM, QuestionLogORM, QuestionSetORM
from core.dependencies import get_retrieval_pipeline

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            pipeline = get_retrieval_pipeline()
        except Exception:
            pipeline = None
        self._questions = QuestionGenerator(settings, pipeline)
        self._builder = ReportBuilder()

    async def run(
        self,
        session: AsyncSession,
        request: AnalyticsRunRequest,
    ) -> AnalyticsRunResponse:
        if len(request.lead_ids) > 5:
            raise ValueError("Пакетная аналитика ограничена 5 компаниями")

        result = await session.execute(
            select(LeadORM).where(LeadORM.id.in_(request.lead_ids))
        )
        leads = {lead.id: lead for lead in result.scalars().all()}
        missing = [str(lid) for lid in request.lead_ids if lid not in leads]
        if missing:
            raise ValueError(f"Leads not found: {', '.join(missing)}")

        reports: list[AnalyticsReport] = []
        for lead_id in request.lead_ids:
            lead = leads[lead_id]
            report = await self._analyze_lead(session, lead, request.user_role)
            reports.append(report)
        await session.commit()
        return AnalyticsRunResponse(reports=reports)

    async def get_report(
        self,
        session: AsyncSession,
        report_id: uuid.UUID,
    ) -> AnalyticsReport | None:
        row = await session.get(AnalyticsReportORM, report_id)
        if not row:
            return None
        return self._orm_to_schema(row)

    async def list_for_leads(
        self,
        session: AsyncSession,
        lead_ids: list[uuid.UUID],
    ) -> list[AnalyticsReport]:
        result = await session.execute(
            select(AnalyticsReportORM)
            .where(AnalyticsReportORM.lead_id.in_(lead_ids))
            .order_by(AnalyticsReportORM.created_at.desc())
        )
        rows = result.scalars().all()
        latest: dict[uuid.UUID, AnalyticsReportORM] = {}
        for row in rows:
            if row.lead_id not in latest:
                latest[row.lead_id] = row
        return [self._orm_to_schema(row) for row in latest.values()]

    async def mark_in_work(
        self,
        session: AsyncSession,
        request: MarkInWorkRequest,
    ) -> int:
        result = await session.execute(
            select(LeadORM).where(LeadORM.id.in_(request.lead_ids))
        )
        count = 0
        for lead in result.scalars().all():
            lead.status = "in_work"
            count += 1
        await session.commit()
        return count

    async def mark_question_used(
        self,
        session: AsyncSession,
        question_id: uuid.UUID,
        used: bool = True,
    ) -> bool:
        row = await session.get(QuestionLogORM, question_id)
        if not row:
            return False
        row.used_in_call = datetime.now(timezone.utc) if used else None
        if used:
            question_set = await session.get(QuestionSetORM, row.question_set_id)
            if question_set and not question_set.used_in_call:
                question_set.used_in_call = datetime.now(timezone.utc)
        await session.commit()
        return True

    async def export_reports(
        self,
        session: AsyncSession,
        request: AnalyticsExportRequest,
    ) -> tuple[bytes, str, str]:
        result = await session.execute(
            select(AnalyticsReportORM).where(AnalyticsReportORM.id.in_(request.report_ids))
        )
        rows = list(result.scalars().all())
        if False:  # xlsx disabled
            pass  # xlsx disabled
        return self._export_csv(rows), "text/csv; charset=utf-8", "analytics.csv"

    async def _analyze_lead(
        self,
        session: AsyncSession,
        lead: LeadORM,
        user_role: str,
    ) -> AnalyticsReport:
        question_payload = await self._questions.generate(
            lead_id=lead.id,
            segment=lead.segment,
            company_name=lead.company_name,
            region=lead.region,
            user_role=user_role,
        )
        mandatory = self._builder.build_mandatory(lead)
        optional = self._builder.build_optional(lead, question_payload)

        report_body = {
            "mandatory": {key: block.model_dump() for key, block in mandatory.items()},
            "optional": optional,
        }
        report_row = AnalyticsReportORM(
            id=uuid.uuid4(),
            lead_id=lead.id,
            user_role=user_role,
            company_name=lead.company_name,
            segment=lead.segment,
            score=lead.score,
            region=lead.region,
            report=report_body,
        )
        session.add(report_row)

        question_set = QuestionSetORM(
            id=uuid.uuid4(),
            lead_id=lead.id,
            analytics_report_id=report_row.id,
            segment=lead.segment,
            questions=question_payload,
        )
        session.add(question_set)

        for item in question_payload:
            session.add(
                QuestionLogORM(
                    id=uuid.UUID(item["question_id"]),
                    question_set_id=question_set.id,
                    lead_id=lead.id,
                    question_text=item["text"],
                    methodology_tag=item.get("methodology_tag"),
                    category=item.get("category"),
                    source=item.get("source"),
                )
            )

        questions = [
            RecommendedQuestion(
                question_id=uuid.UUID(item["question_id"]),
                text=item["text"],
                source=item.get("source", ""),
                methodology_tag=item.get("methodology_tag"),
                category=item.get("category"),
            )
            for item in question_payload
        ]

        return AnalyticsReport(
            report_id=report_row.id,
            lead_id=lead.id,
            company_name=lead.company_name,
            segment=lead.segment,
            score=lead.score,
            region=lead.region,
            mandatory=mandatory,
            optional=optional,
            question_set_id=question_set.id,
            questions=questions,
            created_at=datetime.now(timezone.utc),
        )

    def _orm_to_schema(self, row: AnalyticsReportORM) -> AnalyticsReport:
        from core.analytics.schemas import AnalyticsBlock

        mandatory_raw = row.report.get("mandatory", {})
        mandatory = {
            key: AnalyticsBlock.model_validate(value) for key, value in mandatory_raw.items()
        }
        optional = row.report.get("optional", {})
        questions_raw = optional.get("questions", [])
        questions = [
            RecommendedQuestion(
                question_id=uuid.UUID(item["question_id"]),
                text=item["text"],
                source=item.get("source", ""),
                methodology_tag=item.get("methodology_tag"),
                category=item.get("category"),
            )
            for item in questions_raw
            if isinstance(item, dict)
        ]
        return AnalyticsReport(
            report_id=row.id,
            lead_id=row.lead_id,
            company_name=row.company_name,
            segment=row.segment,
            score=row.score,
            region=row.region,
            mandatory=mandatory,
            optional=optional,
            questions=questions,
            created_at=row.created_at,
        )

    def _export_csv(self, rows: list[AnalyticsReportORM]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["report_id", "lead_id", "company_name", "segment", "score", "region", "tender_summary", "lpr"]
        )
        for row in rows:
            contacts = row.report.get("mandatory", {}).get("contacts", {})
            summary = contacts.get("summary", "")
            tenders = row.report.get("mandatory", {}).get("tenders", {}).get("summary", "")
            writer.writerow(
                [
                    str(row.id),
                    str(row.lead_id),
                    row.company_name,
                    row.segment,
                    row.score,
                    row.region or "",
                    tenders,
                    summary,
                ]
            )
        return buffer.getvalue().encode("utf-8-sig")

    def _export_xlsx_disabled(rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Analytics"
        sheet.append(
            ["report_id", "lead_id", "company_name", "segment", "score", "region", "tender_summary", "lpr"]
        )
        for row in rows:
            contacts = row.report.get("mandatory", {}).get("contacts", {})
            tenders = row.report.get("mandatory", {}).get("tenders", {})
            sheet.append(
                [
                    str(row.id),
                    str(row.lead_id),
                    row.company_name,
                    row.segment,
                    row.score,
                    row.region or "",
                    tenders.get("summary", ""),
                    contacts.get("summary", ""),
                ]
            )
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()
