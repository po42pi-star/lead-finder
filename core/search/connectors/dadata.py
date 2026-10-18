import asyncio
import logging

from core.config.settings import Settings
from core.search.schemas import SearchFilters
from core.search.scoring import RawLeadCandidate

logger = logging.getLogger(__name__)


class DaDataConnector:
    """DaData.ru async data connector. Free tier: 1000 requests/day."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._api_key = settings.dadata_api_key
        self._secret_key = settings.dadata_secret_key

    async def fetch(self, filters: SearchFilters) -> list[RawLeadCandidate]:
        if not self._api_key:
            logger.warning("DADATA_API_KEY not set, skipping DaData")
            return []

        query = self._build_query(filters)
        if not query:
            return []

        try:
            from dadata import DadataAsync
        except ImportError:
            logger.warning("dadata package not installed. Run: pip install dadata")
            return []

        candidates: list[RawLeadCandidate] = []
        try:
            async with DadataAsync(self._api_key, self._secret_key) as dadata:
                kwargs = {}
                if filters.extra.geography.strip():
                    kwargs["locations"] = [{"region": filters.extra.geography.strip()}]
                result = await dadata.suggest("party", query, count=20, **kwargs)
                for item in result or []:
                    candidate = self._parse_party(item, filters)
                    if candidate:
                        candidates.append(candidate)
        except Exception as exc:
            logger.warning("DaData fetch failed: %s", exc)
            return []

        seen: set[str] = set()
        unique: list[RawLeadCandidate] = []
        for c in candidates:
            key = c.inn or c.company_name.lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        return unique[: self._settings.search_max_results]

    def _build_query(self, filters: SearchFilters) -> str:
        # Подсказки DaData ищут по названию: лишние слова (регион и т.п.) обнуляют выдачу,
        # поэтому регион передаётся отдельным фильтром locations
        return filters.extra.keywords.strip() or "вентиляция"

    async def enrich(self, candidates: list[RawLeadCandidate], limit: int = 30) -> None:
        """Дозаполняет ОКВЭД, регион, руководителя и статус по ИНН."""
        if not self._api_key:
            return
        targets = [c for c in candidates if c.inn and not c.okved_codes][:limit]
        if not targets:
            return
        try:
            from dadata import DadataAsync
        except ImportError:
            return

        async with DadataAsync(self._api_key, self._secret_key) as dadata:
            async def enrich_one(candidate: RawLeadCandidate) -> None:
                try:
                    result = await dadata.find_by_id("party", candidate.inn)
                except Exception as exc:
                    logger.warning("DaData enrich failed for %s: %s", candidate.inn, exc)
                    return
                if not result:
                    return
                parsed = self._parse_party(result[0], SearchFilters())
                if not parsed:
                    return
                candidate.okved_codes = parsed.okved_codes
                candidate.region = candidate.region or parsed.region
                candidate.contact_name = candidate.contact_name or parsed.contact_name
                candidate.employees = candidate.employees or parsed.employees
                candidate.company_age_years = candidate.company_age_years or parsed.company_age_years
                candidate.not_bankrupt = candidate.not_bankrupt and parsed.not_bankrupt
                if parsed.okved_codes and candidate.segment == "installer":
                    candidate.segment = self._detect_segment(parsed.okved_codes, [])
                candidate.source = f"{candidate.source}+dadata"

            await asyncio.gather(*(enrich_one(c) for c in targets))

    def _parse_party(self, item: dict, filters: SearchFilters) -> RawLeadCandidate | None:
        data = item.get("data") or {}
        name = data.get("name", {}).get("short_with_opf") or data.get("name", {}).get("short") or item.get("value")
        if not name:
            return None

        inn = data.get("inn")
        ogrn = data.get("ogrn")
        address_obj = data.get("address") or {}
        address = address_obj.get("value", "")
        region = (address_obj.get("data") or {}).get("region_with_type") or self._extract_region(address)

        okved = data.get("okved")
        okved_codes = [okved] if okved else []

        status = data.get("state", {}).get("status", "")
        is_active = status == "ACTIVE"

        reg_date = data.get("state", {}).get("registration_date")
        company_age = self._calculate_age(reg_date)

        segment = self._detect_segment(okved_codes, filters.checkboxes)
        vent_mention = self._is_ventilation_company(name, okved_codes)

        return RawLeadCandidate(
            company_name=name,
            inn=inn,
            ogrn=ogrn,
            segment=segment,
            region=region,
            source="dadata",
            okved_codes=okved_codes,
            turnover_mln=None,
            employees=data.get("employee_count"),
            website=None,
            contact_name=(data.get("management") or {}).get("name"),
            contact_phone=None,
            contact_email=None,
            has_tenders_12m=False,
            has_sro=False,
            has_website=False,
            web_active_6m=False,
            vent_mention=vent_mention,
            company_age_years=company_age,
            is_legal_entity=True,
            not_bankrupt=is_active,
            has_portfolio=False,
            multi_region=False,
            raw_data={"address": address, "status": status, "okved": okved},
        )

    def _extract_region(self, address: str | None) -> str | None:
        if not address:
            return None
        region_keywords = [
            "Москва", "Московская область", "Санкт-Петербург", "Ленинградская область",
            "Самара", "Самарская", "Новосибирск", "Новосибирская",
            "Екатеринбург", "Свердловская", "Казань", "Татарстан",
            "Краснодар", "Краснодарский", "Воронеж", "Воронежская",
        ]
        for region in region_keywords:
            if region in address:
                return region
        return None

    def _calculate_age(self, reg_date: str | None) -> float | None:
        if not reg_date:
            return None
        try:
            from datetime import datetime
            date_obj = datetime.strptime(str(reg_date)[:10], "%Y-%m-%d")
            return round((datetime.now() - date_obj).days / 365.25, 1)
        except (ValueError, TypeError):
            return None

    def _detect_segment(self, okved_codes: list[str], checkboxes: list[str]) -> str:
        installer_codes = ["43.22", "43.22.1", "43.29", "43.99"]
        designer_codes = ["71.12", "71.12.1", "71.12.2", "71.12.3"]
        industrial_codes = ["28.23", "25.62", "28.29", "27.90"]
        contractor_codes = ["41.20", "42.99", "43.11", "43.21"]

        for code in okved_codes:
            if any(code.startswith(prefix) for prefix in installer_codes):
                return "installer"
            if any(code.startswith(prefix) for prefix in designer_codes):
                return "designer"
            if any(code.startswith(prefix) for prefix in industrial_codes):
                return "industrial"
            if any(code.startswith(prefix) for prefix in contractor_codes):
                return "contractor"

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

    def _is_ventilation_company(self, name: str, okved_codes: list[str]) -> bool:
        keywords = ["вентил", "кондицион", "климат", "воздух", "овик", "овкв"]
        name_lower = name.lower()
        for kw in keywords:
            if kw in name_lower:
                return True
        return False
