import logging
import re
from urllib.parse import quote_plus, urljoin

try:
    from selectolax.parser import HTMLParser
except ImportError:
    class HTMLParser:
        def __init__(self, html): self._html = html
        def css(self, selector): return []

from core.config.settings import Settings
from core.search.connectors.http_client import PoliteHttpClient
from core.search.okved_mapping import resolve_primary_segment
from core.search.schemas import SearchFilters
from core.search.scoring import RawLeadCandidate

logger = logging.getLogger(__name__)

COMPANY_PATTERN = re.compile(
    r"(ООО|АО|ПАО|ЗАО)\s+[\"«]([^\"»]+)[\"»]",
    re.IGNORECASE,
)


class RegistryConnector:
    source = "industry_registry"

    def __init__(self, settings: Settings, http: PoliteHttpClient) -> None:
        self._settings = settings
        self._http = http

    async def fetch(self, filters: SearchFilters) -> list[RawLeadCandidate]:
        if not self._settings.search_use_live_sources:
            return []
        query = filters.extra.keywords or "вентиляция"
        leads: list[RawLeadCandidate] = []
        leads.extend(await self._fetch_abok(query, filters))
        return leads

    async def _fetch_abok(self, query: str, filters: SearchFilters) -> list[RawLeadCandidate]:
        search_url = urljoin(
            self._settings.registry_abok_url.rstrip("/") + "/",
            f"?s={quote_plus(query)}",
        )
        try:
            response = await self._http.get(search_url)
            return self._parse_html(response.text, filters)
        except Exception as exc:
            logger.warning("ABOK registry fetch failed: %s", exc)
            return []

    def _parse_html(self, html: str, filters: SearchFilters) -> list[RawLeadCandidate]:
        parser = HTMLParser(html)
        text_blocks = [
            node.text(strip=True)
            for node in parser.css("article, .post, .entry, li, p")
            if node.text(strip=True)
        ]
        leads: list[RawLeadCandidate] = []
        seen: set[str] = set()
        for block in text_blocks:
            for match in COMPANY_PATTERN.finditer(block):
                company_name = f'{match.group(1)} "{match.group(2)}"'
                if company_name in seen:
                    continue
                seen.add(company_name)
                lower = block.lower()
                leads.append(
                    RawLeadCandidate(
                        company_name=company_name,
                        segment=resolve_primary_segment(filters.checkboxes),
                        region=filters.extra.geography or None,
                        source=self.source,
                        has_website="http" in lower,
                        vent_mention=any(
                            token in lower
                            for token in ("вентил", "овик", "воздуховод", "кондицион")
                        ),
                        has_portfolio="проект" in lower or "портфолио" in lower,
                        raw_data={"snippet": block[:300]},
                    )
                )
        return leads[: self._settings.search_max_results]
