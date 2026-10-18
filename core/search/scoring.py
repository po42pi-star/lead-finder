from dataclasses import dataclass, field

from core.config.settings import Settings
from core.search.okved_mapping import ACTIVITY_OKVED
from core.search.schemas import ScoreBreakdownItem, SearchFilters


@dataclass
class RawLeadCandidate:
    company_name: str
    inn: str | None = None
    ogrn: str | None = None
    segment: str = "installer"
    region: str | None = None
    source: str = "unknown"
    okved_codes: list[str] = field(default_factory=list)
    turnover_mln: float | None = None
    employees: int | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    has_tenders_12m: bool = False
    has_sro: bool = False
    has_website: bool = False
    web_active_6m: bool = False
    vent_mention: bool = False
    company_age_years: float | None = None
    is_legal_entity: bool = True
    not_bankrupt: bool = True
    has_portfolio: bool = False
    multi_region: bool = False
    raw_data: dict = field(default_factory=dict)


@dataclass
class ScoredLead:
    candidate: RawLeadCandidate
    score: int
    breakdown: list[ScoreBreakdownItem]


class LeadScorer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def score(self, candidate: RawLeadCandidate, filters: SearchFilters) -> ScoredLead:
        breakdown: list[ScoreBreakdownItem] = []
        total = 0

        target_okved = {
            code
            for checkbox_id in filters.checkboxes
            for code in ACTIVITY_OKVED.get(checkbox_id, [])
        }
        if target_okved and set(candidate.okved_codes) & target_okved:
            delta = self._settings.score_okved_match
            total += delta
            breakdown.append(
                ScoreBreakdownItem(
                    delta=delta,
                    reason=f"ОКВЭД {', '.join(sorted(set(candidate.okved_codes) & target_okved))}",
                )
            )

        if candidate.has_tenders_12m:
            delta = self._settings.score_tenders_12m
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="участие в тендерах за 12 мес.")
            )

        if candidate.has_website or candidate.web_active_6m:
            delta = self._settings.score_active_website
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="сайт активен / есть активность")
            )

        if candidate.turnover_mln and candidate.turnover_mln >= 200:
            delta = self._settings.score_revenue_200m
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="оборот >200 млн ₽")
            )
        elif candidate.turnover_mln and candidate.turnover_mln >= 50:
            delta = self._settings.score_revenue_50m
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="оборот >50 млн ₽")
            )

        if candidate.has_sro:
            delta = self._settings.score_sro
            total += delta
            breakdown.append(ScoreBreakdownItem(delta=delta, reason="наличие СРО"))

        if candidate.vent_mention:
            delta = self._settings.score_ventilation_mention
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="упоминание вентиляции / ОВиК")
            )

        if candidate.company_age_years and candidate.company_age_years >= 2:
            delta = self._settings.score_company_age_2y
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason="срок регистрации ≥ 2 лет")
            )

        if self._region_matches(filters.extra.geography, candidate.region):
            delta = self._settings.score_region_match
            total += delta
            breakdown.append(
                ScoreBreakdownItem(delta=delta, reason=f"регион совпадает: {candidate.region}")
            )

        if "vent_mention" in filters.checkboxes and not candidate.vent_mention:
            delta = -self._settings.score_no_vent_penalty
            total += delta
            breakdown.append(
                ScoreBreakdownItem(
                    delta=delta,
                    reason="нет упоминания вентиляции на сайте",
                    matched=False,
                )
            )

        total = max(0, min(100, total))
        return ScoredLead(candidate=candidate, score=total, breakdown=breakdown)

    @staticmethod
    def _region_matches(geography: str, region: str | None) -> bool:
        if not geography.strip() or not region:
            return False
        region_lower = region.lower()
        # Сравниваем по основе слова: «Самарская область» ~ «Самарская обл», «Самара»
        stems = [word[:5] for word in geography.lower().replace(",", " ").split() if len(word) >= 4]
        stems = [stem for stem in stems if stem not in {"облас", "респу", "город", "район"}]
        return any(stem in region_lower for stem in stems)
