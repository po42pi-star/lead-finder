from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.analytics.schemas import (
    AnalyticsBlock,
    AnalyticsItem,
    AnalyticsReport,
    AnalyticsRunResponse,
    ConfidenceLevel,
    RecommendedQuestion,
)
from handlers import analytics_router
from main import app
from services.analytics_service import AnalyticsService


@pytest.fixture
def client(mocker):
    mock_service = mocker.Mock(spec=AnalyticsService)
    report_id = uuid4()
    lead_id = uuid4()
    mock_service.run = mocker.AsyncMock(
        return_value=AnalyticsRunResponse(
            reports=[
                AnalyticsReport(
                    report_id=report_id,
                    lead_id=lead_id,
                    company_name='ООО "ВентМонтаж"',
                    segment="installer",
                    score=82,
                    region="Самара",
                    mandatory={
                        "financial": AnalyticsBlock(
                            title="Финансовые признаки",
                            items=[AnalyticsItem(text="Активен", confidence=ConfidenceLevel.OK)],
                            summary="✅ Активен",
                        )
                    },
                    optional={},
                    questions=[
                        RecommendedQuestion(
                            question_id=uuid4(),
                            text="Какой бюджет?",
                            source="sales_questions_bank.md",
                        )
                    ],
                    created_at=datetime.now(timezone.utc),
                )
            ]
        )
    )
    app.dependency_overrides[analytics_router.get_analytics_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_analytics_run(client):
    response = client.post(
        "/analytics/run",
        json={"lead_ids": [str(uuid4())], "user_role": "rop"},
    )
    assert response.status_code == 200
    assert response.json()["reports"][0]["score"] == 82
