import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlencode

from core.config.settings import Settings
from core.search.connectors.http_client import PoliteHttpClient
from core.search.schemas import SearchFilters
from core.search.scoring import RawLeadCandidate

logger = logging.getLogger(__name__)


class ZakupkiConnector:
    source = "zakupki_gov_ru"

    def __init__(self, settings: Settings, http: PoliteHttpClient) -> None:
        self._settings = settings
        self._http = http

    async def fetch(self, filters: SearchFilters) -> list[RawLeadCandidate]:
        if not self._settings.search_use_live_sources:
            return []
        keywords = self._build_query(filters)
        if not keywords:
            return []

        if self._settings.zakupki_open_api_url:
            return await self._fetch_open_api(keywords)

        return await self._fetch_rss(keywords)

    def _build_query(self, filters: SearchFilters) -> str:
        parts = [
            filters.extra.keywords,
            filters.extra.adjacent_industries,
            filters.extra.project_types,
            "вентиляция",
            "ОВиК",
        ]
        if "gov_tenders" in filters.checkboxes:
            parts.append("монтаж инженерных систем")
        return " ".join(part.strip() for part in parts if part and part.strip())

    async def _fetch_open_api(self, query: str) -> list[RawLeadCandidate]:
        params = {
            "q": query,
            "limit": min(self._settings.search_max_results, 50),
        }
        url = f"{self._settings.zakupki_open_api_url.rstrip('/')}/{urlencode(params)}"
        headers = {}
        if self._settings.zakupki_open_api_key:
            headers["Authorization"] = f"Bearer {self._settings.zakupki_open_api_key}"
        try:
            response = await self._http.get(url, headers=headers)
            payload = response.json()
            items = payload if isinstance(payload, list) else payload.get("items", [])
            return [self._map_open_api_item(item) for item in items if isinstance(item, dict)]
        except Exception as exc:
            logger.warning("Zakupki open API failed, fallback to RSS: %s", exc)
            return await self._fetch_rss(query)

    def _map_open_api_item(self, item: dict) -> RawLeadCandidate:
        return RawLeadCandidate(
            company_name=str(item.get("supplier_name") or item.get("customer_name") or "Неизвестно"),
            inn=str(item.get("inn")) if item.get("inn") else None,
            region=str(item.get("region")) if item.get("region") else None,
            segment="contractor",
            source=self.source,
            has_tenders_12m=True,
            vent_mention="вентил" in str(item).lower() or "овик" in str(item).lower(),
            raw_data=item,
        )

    async def _fetch_rss(self, query: str) -> list[RawLeadCandidate]:
        params = {
            "searchString": query,
            "morphology": "on",
            "sortDirection": "false",
            "recordsPerPage": "_50",
            "publishDateFrom": (datetime.utcnow() - timedelta(days=365)).strftime("%d.%m.%Y"),
        }
        url = f"{self._settings.zakupki_api_base_url.rstrip('/')}{self._settings.zakupki_rss_path}?{urlencode(params)}"
        try:
            response = await self._http.get(url)
            return self._parse_rss(response.text)
        except Exception as exc:
            logger.warning("Zakupki RSS fetch failed: %s", exc)
            return []

    def _parse_rss(self, content: str) -> list[RawLeadCandidate]:
        leads: list[RawLeadCandidate] = []
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return leads

        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").lower()
            if not title:
                continue
            company_name = title.split("|")[0].strip()[:512]
            leads.append(
                RawLeadCandidate(
                    company_name=company_name,
                    segment="contractor",
                    source=self.source,
                    has_tenders_12m=True,
                    vent_mention=any(
                        token in description
                        for token in ("вентил", "овик", "кондицион", "воздуховод")
                    ),
                    raw_data={"title": title, "description": description[:500]},
                )
            )
        return leads
