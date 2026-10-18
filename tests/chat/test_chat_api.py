from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.chat.schemas import ChatMessageResponse, ChatMode, ChatSource
from handlers import chat_router
from main import app
from services.chat_service import ChatService


@pytest.fixture
def client(mocker):
    mock_service = mocker.Mock(spec=ChatService)
    mock_service.get_suggestions.return_value = type(
        "R", (), {"suggestions": ["Что такое скоринг?"]}
    )()
    mock_service.send_message = mocker.AsyncMock(
        return_value=ChatMessageResponse(
            session_id=uuid4(),
            interaction_id=uuid4(),
            answer="Скоринг 65 = тёплый лид.",
            sources=[ChatSource(doc_id="system_search_guide_v1", section="Скоринг", score=0.9)],
            cache_hit=False,
            fallback_used=False,
            suggested_followups=["Как запустить аналитику?"],
            quick_actions=[],
            escalation_used=False,
        )
    )
    app.dependency_overrides[chat_router.get_chat_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_chat_message(client):
    response = client.post(
        "/chat/message",
        json={
            "query": "Что означает скоринг 65?",
            "mode": "search",
            "user_role": "rop",
            "context": {},
        },
    )
    assert response.status_code == 200
    assert "тёплый" in response.json()["answer"]


def test_chat_suggestions(client):
    response = client.get("/chat/suggestions?mode=help&user_role=rop")
    assert response.status_code == 200
    assert response.json()["suggestions"]
