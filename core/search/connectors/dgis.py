import logging
from typing import Any

from core.config.settings import Settings
from core.search.connectors.http_client import PoliteHttpClient
from core.search.schemas import SearchFilters
from core.search.scoring import RawLeadCandidate

logger = logging.getLogger(__name__)


class DGISConnector:
    """2GIS (dgis.ru) async data connector. Free tier: 1000 requests/day.

    Notes on free/demo tier limitations:
    - contacts/phones/emails are NOT available
    - address is minimal (only location comment)
    - rubrics are available
    """

    def __init__(self, settings: Settings, http_client: PoliteHttpClient):
        self._settings = settings
        self._http = http_client
        self._api_key = settings.dgis_api_key

    async def fetch(self, filters: SearchFilters) -> list[RawLeadCandidate]:
        if not self._api_key:
            logger.warning("DGIS_API_KEY not set, skipping 2GIS")
            return []

        queries = self._get_search_queries(filters.checkboxes, filters.extra.geography)

        candidates: list[RawLeadCandidate] = []
        for query in queries:
            try:
                params: dict[str, Any] = {
                    "q": query,
                    "key": self._api_key,
                    "fields": "items.point,items.address,items.rubrics",
                }

                url = f"{self._settings.dgis_base_url.rstrip('/')}/3.0/items"
                response = await self._http.get(url, params=params)
                data = response.json()

                meta = data.get("meta", {})
                if meta.get("code") != 200:
                    logger.warning("2GIS API error: %s", meta)
                    continue

                companies = self._parse_response(data, filters.checkboxes)
                logger.info("2GIS query '%s' returned %s items", query, len(companies))
                candidates.extend(companies)

                import asyncio
                await asyncio.sleep(0.5)

            except Exception as exc:
                logger.warning("2GIS fetch failed for query %s: %s", query, exc)
                continue

        seen: set[str] = set()
        unique: list[RawLeadCandidate] = []
        for c in candidates:
            key = c.company_name.lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        return unique[: self._settings.search_max_results]

    def _get_search_queries(self, checkboxes: list[str], geography: str | None) -> list[str]:
        region = f" {geography}" if geography else ""

        base_queries = [
            f"монтаж систем вентиляции{region}",
            f"вентиляция и кондиционирование{region}",
            f"системы вентиляции{region}",
        ]

        segment_queries = {
            "installer": [f"монтаж вентиляции{region}", f"монтажники вентиляции{region}", f"монтаж ВК{region}"],
            "designer": [f"проектирование вентиляции{region}", f"проектировщики вентиляции{region}", f"проектная организация ВК{region}"],
            "contractor": [f"генподрядчик строительство{region}", f"строительная компания{region}", f"генподряд{region}"],
            "industrial": [f"производство вентиляции{region}", f"завод вентиляционного оборудования{region}", f"промышленная вентиляция{region}"],
        }

        queries = list(base_queries)
        for segment, segment_qs in segment_queries.items():
            if segment in [c.lower() for c in checkboxes]:
                queries.extend(segment_qs)

        if not checkboxes:
            queries.extend(segment_queries["installer"])

        return queries[:6]

    def _parse_response(self, data: dict, checkboxes: list[str]) -> list[RawLeadCandidate]:
        candidates: list[RawLeadCandidate] = []
        items = data.get("result", {}).get("items", []) if "result" in data else data.get("items", [])

        for item in items[:50]:
            name = item.get("name") or item.get("full_name")
            if not name:
                continue

            # Extract address from new structure
            address = ""
            addr_obj = item.get("address")
            if isinstance(addr_obj, dict):
                # Try formatted name first
                address = addr_obj.get("name") or ""
                if not address:
                    # Build from components
                    comps = addr_obj.get("components", [])
                    parts = []
                    for comp in comps:
                        if isinstance(comp, dict):
                            val = comp.get("name") or comp.get("comment") or ""
                            if val:
                                parts.append(val)
                    address = ", ".join(parts)

            region = address.split(",")[0] if address else None

            # Extract rubrics
            rubrics = item.get("rubrics", [])
            category_names = [r.get("name", "").lower() for r in rubrics if isinstance(r, dict)]
            segment = self._detect_segment(category_names, checkboxes)

            candidates.append(
                RawLeadCandidate(
                    company_name=name,
                    inn=None,
                    segment=segment,
                    region=region,
                    source="dgis",
                    okved_codes=[],
                    turnover_mln=None,
                    employees=None,
                    website=None,  # Not available in free tier
                    contact_name=None,
                    contact_phone=None,
                    contact_email=None,
                    has_tenders_12m=False,
                    has_website=False,
                    has_sro=False,
                    vent_mention=self._is_ventilation_company(category_names),
                    company_age_years=None,
                    is_legal_entity=True,
                    not_bankrupt=True,
                    has_portfolio=False,
                    multi_region=False,
                    raw_data={"address": address, "categories": category_names},
                )
            )

        return candidates

    def _detect_segment(self, categories: list[str], checkboxes: list[str]) -> str:
        for cat in categories:
            if any(kw in cat for kw in ["проект", "проектирование", "дизайн"]):
                return "designer"
            if any(kw in cat for kw in ["производство", "завод", "фабрика"]):
                return "industrial"
            if any(kw in cat for kw in ["генподряд", "строитель", "застройщик"]):
                return "contractor"
            if any(kw in cat for kw in ["монтаж", "установка", "сервис"]):
                return "installer"

        checkbox_map = {
            "installer": "installer",
            "designer": "designer",
            "contractor": "contractor",
            "industrial": "industrial",
            "vent_mount": "installer",
            "ovik_design": "designer",
            "general_contract": "contractor",
            "industrial_prod": "industrial",
            "commercial_build": "contractor",
            "residential_build": "contractor",
        }
        for cb in checkboxes:
            if cb in checkbox_map:
                return checkbox_map[cb]
        return "installer"

    def _is_ventilation_company(self, categories: list[str]) -> bool:
        keywords = ["вентил", "кондицион", "климат", "воздух", "овик", "овкв", "тепловое"]
        for cat in categories:
            if any(kw in cat for kw in keywords):
                return True
        return False
