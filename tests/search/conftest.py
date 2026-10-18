import pytest

from core.config.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings.model_construct(
        openai_api_key="test",
        rag_docs_path=tmp_path / "rag_docs",
        chroma_persist_path=tmp_path / "chroma",
        disk_cache_path=tmp_path / "diskcache",
        analytics_db_path=tmp_path / "analytics.db",
        database_url="sqlite+aiosqlite:///:memory:",
        search_use_live_sources=False,
        search_page_size=20,
        search_max_results=100,
    )
