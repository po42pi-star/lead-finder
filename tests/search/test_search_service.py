import pytest

from core.search.schemas import ExtraFields, SearchFilters, SearchRunRequest, SortOption
from services.search_service import SearchService


@pytest.mark.asyncio
async def test_demo_search_when_no_live_sources(settings, mocker):
    service = SearchService(settings)
    mock_session = mocker.AsyncMock()
    mock_session.add = mocker.Mock()
    mock_session.add_all = mocker.Mock()
    mock_session.commit = mocker.AsyncMock()

    request = SearchRunRequest(
        user_role="rop",
        filters=SearchFilters(
            checkboxes=["vent_mount", "gov_tenders"],
            extra=ExtraFields(geography="Самара", keywords="монтаж вентиляции"),
        ),
        sort_by=SortOption.SCORE_DESC,
    )
    mocker.patch.object(service, "_collect_candidates", return_value=[])
    response = await service.run_search(mock_session, request)
    assert response.total_count >= 1
    assert response.leads
    assert response.session_id
    await service.close()
