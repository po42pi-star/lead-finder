import logging
from datetime import datetime
from urllib.parse import urljoin

from core.config.settings import Settings
from core.search.connectors.http_client import PoliteHttpClient
from core.search.okved_mapping import resolve_primary_segment
from core.search.schemas import SearchFilters
from core.search.scoring import RawLeadCandidate

logger = logging.getLogger(__name__)


class FnsEgrConnector:
    source = "egr_nalog_ru"

    def __init__(self, settings: Settings, http: PoliteHttpClient) -> None:
        self._settings = settings
        self._http = http

    async def fetch(self, filters: SearchFilters) -> list[RawLeadCandidate]:
        if not self._settings.search_use_live_sources:
            return []
        query = self._build_query(filters)
        if not query:
            return []
        try:
            token_response = await self._http.post(
                urljoin(self._settings.fns_egrul_base_url + "/", ""),
                data={"query": query},
            )
            token = token_response.json().get("t")
            if not token:
                return []
            result_response = await self._http.get(
                urljoin(self._settings.fns_egrul_base_url + "/", f"search-result/{token}")
            )
            rows = result_response.json().get("rows", [])
            return [self._map_row(row, filters) for row in rows if isinstance(row, dict)]
        except Exception as exc:
            logger.warning("FNS EGRUL fetch failed: %s", exc)
            return []

    def _build_query(self, filters: SearchFilters) -> str:
        parts = [filters.extra.keywords, filters.extra.geography]
        if filters.extra.adjacent_industries:
            parts.append(filters.extra.adjacent_industries)
        if not parts:
            parts.append("вентиляция")
        return " ".join(part.strip() for part in parts if part.strip())

    def _map_row(self, row: dict, filters: SearchFilters) -> RawLeadCandidate:
        # Поля ответа ЕГРЮЛ: n — полное название, c — краткое, i — ИНН, o — ОГРН,
        # rn — регион, r — дата регистрации, g — руководитель, k — тип лица (ul/fl)
        name = str(row.get("c") or row.get("n") or "Без названия")
        inn = str(row.get("i")) if row.get("i") else None
        ogrn = str(row.get("o")) if row.get("o") else None
        region = str(row.get("rn")) if row.get("rn") else None
        director = self._parse_director(row.get("g"))
        return RawLeadCandidate(
            company_name=name[:512],
            inn=inn,
            ogrn=ogrn,
            segment=resolve_primary_segment(filters.checkboxes),
            region=region,
            source=self.source,
            contact_name=director,
            company_age_years=self._calculate_age(row.get("r")),
            is_legal_entity=row.get("k") == "ul",
            not_bankrupt=not row.get("e"),
            vent_mention=any(
                token in name.lower()
                for token in ("вентил", "овик", "кондицион", "воздухов")
            ),
            raw_data=row,
        )

    @staticmethod
    def _parse_director(value: object) -> str | None:
        if not value:
            return None
        text = str(value)
        return text.split(":", 1)[1].strip() if ":" in text else text.strip()

    @staticmethod
    def _calculate_age(reg_date: object) -> float | None:
        if not reg_date:
            return None
        try:
            date_obj = datetime.strptime(str(reg_date), "%d.%m.%Y")
        except ValueError:
            return None
        return round((datetime.now() - date_obj).days / 365.25, 1)
