from pathlib import Path

import pytest

from core.config.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    docs = Path("rag_docs")
    return Settings.model_construct(
        openai_api_key="test-key",
        rag_docs_path=docs,
        chroma_persist_path=tmp_path / "chroma",
        disk_cache_path=tmp_path / "diskcache",
        analytics_db_path=tmp_path / "analytics.db",
        intent_use_llm=False,
        chunk_max_tokens=200,
        chunk_overlap_tokens=20,
        retrieval_top_k=3,
        similarity_score_threshold=0.5,
    )
