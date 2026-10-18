from core.search.okved_mapping import resolve_okved_codes
from core.search.schemas import ExtraFields, SearchFilters
from core.search.scoring import LeadScorer, RawLeadCandidate


def test_scoring_okved_and_penalties(settings):
    scorer = LeadScorer(settings)
    filters = SearchFilters(
        checkboxes=["vent_mount", "vent_mention"],
        extra=ExtraFields(),
    )
    candidate = RawLeadCandidate(
        company_name='ООО "Тест"',
        okved_codes=resolve_okved_codes(["vent_mount"]),
        has_tenders_12m=True,
        turnover_mln=80,
        vent_mention=False,
    )
    result = scorer.score(candidate, filters)
    assert result.score >= 25
    assert any("ОКВЭД" in item.reason for item in result.breakdown)
    assert any("вентиляции" in item.reason for item in result.breakdown)


def test_region_match_bonus(settings):
    scorer = LeadScorer(settings)
    filters = SearchFilters(extra=ExtraFields(geography="Самарская область"))
    near = scorer.score(RawLeadCandidate(company_name="A", region="Самарская обл"), filters)
    far = scorer.score(RawLeadCandidate(company_name="B", region="Пермский край"), filters)
    assert near.score - far.score == settings.score_region_match
