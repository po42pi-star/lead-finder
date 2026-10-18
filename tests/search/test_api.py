import pytest
from fastapi.testclient import TestClient

from handlers import search_router
from main import app
from services.search_service import SearchService


@pytest.fixture
def client(mocker):
    mock_service = mocker.Mock(spec=SearchService)
    from core.search.constants import CHECKBOX_GROUPS, EXTRA_FIELDS
    from core.search.schemas import FiltersMetaResponse, GroupOption, SortOption

    mock_service.filters_meta.return_value = FiltersMetaResponse(
        checkbox_groups=CHECKBOX_GROUPS,
        extra_fields=EXTRA_FIELDS,
        sort_options=[{"id": SortOption.SCORE_DESC.value, "label": "По скорингу"}],
        group_options=[{"id": GroupOption.NONE.value, "label": "Без группировки"}],
    )

    from uuid import uuid4

    from core.search.schemas import LeadCard, ScoreBreakdownItem, SearchRunResponse

    lead_id = uuid4()
    mock_service.run_search = mocker.AsyncMock(
        return_value=SearchRunResponse(
            session_id=uuid4(),
            leads=[
                LeadCard(
                    lead_id=lead_id,
                    company_name='ООО "ВентМонтаж"',
                    segment="installer",
                    region="Самара",
                    score=82,
                    score_breakdown=[
                        ScoreBreakdownItem(delta=20, reason="ОКВЭД 43.22")
                    ],
                    source="demo",
                )
            ],
            groups=None,
            shown_count=1,
            total_count=1,
            has_more=False,
        )
    )
    app.dependency_overrides[search_router.get_search_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_filters_endpoint(client):
    response = client.get("/search/filters")
    assert response.status_code == 200
    body = response.json()
    assert len(body["checkbox_groups"]) == 3


def test_run_endpoint(client):
    response = client.post(
        "/search/run",
        json={
            "user_role": "rop",
            "filters": {"checkboxes": ["vent_mount"], "extra": {}},
        },
    )
    assert response.status_code == 200
    assert response.json()["leads"][0]["score"] == 82
