from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from core.rag.models import IngestResponse, SearchResponse, SourceItem
from handlers import rag_router
from main import app
from services.rag_service import RagService


@pytest.fixture
def client(mocker):
    mock_service = mocker.Mock(spec=RagService)
    mock_service.search = AsyncMock(
        return_value=SearchResponse(
            answer="ok",
            sources=[SourceItem(doc_id="system_faq_v1", section="FAQ", score=0.91)],
            cache_hit=False,
        )
    )
    mock_service.collections_stats.return_value = {
        "name": "nevatom_kb_v1",
        "chunk_count": 10,
        "categories": {"system": 3},
    }
    mock_service.ingest = AsyncMock(
        return_value=IngestResponse(status="completed", message="done", files_queued=1)
    )
    mock_service.count_files.return_value = 1

    app.dependency_overrides[rag_router.get_rag_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_endpoint(client):
    response = client.post(
        "/rag/search",
        json={
            "query": "Как экспортировать?",
            "user_role": "rop",
            "category_override": None,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "ok"
    assert body["sources"][0]["doc_id"] == "system_faq_v1"
    assert "source_file" not in body["sources"][0]


def test_collections_endpoint(client):
    response = client.get("/rag/collections")
    assert response.status_code == 200
    data = response.json()
    assert data["collections"][0]["chunk_count"] == 10


def test_ingest_accepts_background(client):
    response = client.post(
        "/rag/ingest",
        json={"path": "", "force_rebuild": False},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
