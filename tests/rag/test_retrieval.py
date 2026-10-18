from unittest.mock import AsyncMock, MagicMock

import pytest

from core.rag.cache import RetrievalCache
from core.rag.chroma_store import ChromaStore
from core.rag.intent_classifier import IntentClassifier
from core.rag.models import (
    DocumentCategory,
    IntentType,
    Priority,
    RetrievedChunk,
    SearchRequest,
    UserRole,
)
from core.rag.retrieval import RetrievalPipeline


@pytest.fixture
def pipeline(settings, mocker):
    chroma = MagicMock(spec=ChromaStore)
    chroma.similarity_search.return_value = [
        (
            "chunk_1",
            "FAQ answer text",
            {
                "doc_id": "system_faq_v1",
                "section_title": "FAQ",
                "category": "system",
                "audience": "rop,manager",
                "priority": "high",
            },
            0.9,
        )
    ]
    chroma.build_category_filter.return_value = {"category": "system"}

    embeddings = mocker.Mock()
    embeddings.embed_query = AsyncMock(return_value=[0.1] * 1536)

    cache = RetrievalCache(settings)
    intent = IntentClassifier(settings)

    return RetrievalPipeline(
        settings=settings,
        chroma=chroma,
        embeddings=embeddings,
        intent_classifier=intent,
        cache=cache,
    )


@pytest.mark.asyncio
async def test_retrieval_pipeline_returns_sources(pipeline, settings, mocker):
    mocker.patch.object(
        pipeline,
        "_generate_answer",
        AsyncMock(return_value="Test answer"),
    )
    request = SearchRequest(
        query="Как экспортировать список?",
        user_role=UserRole.ROP,
        category_override=DocumentCategory.SYSTEM,
    )
    response, metadata = await pipeline.search(request)
    assert response.answer == "Test answer"
    assert len(response.sources) == 1
    assert metadata["retrieved_doc_ids"] == ["system_faq_v1"]


@pytest.mark.asyncio
async def test_cache_hit_on_second_query(pipeline, mocker):
    mocker.patch.object(
        pipeline,
        "_generate_answer",
        AsyncMock(return_value="Cached answer"),
    )
    request = SearchRequest(
        query="Что такое скоринг?",
        user_role=UserRole.MANAGER,
        category_override=DocumentCategory.SYSTEM,
    )
    first, meta_first = await pipeline.search(request)
    second, meta_second = await pipeline.search(request)
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert meta_first["cache_hit"] is False
    assert meta_second["cache_hit"] is True


def test_intent_classifier_help_for_system_keywords(settings):
    classifier = IntentClassifier(settings)
    import asyncio

    result = asyncio.run(
        classifier.classify("Как настроить фильтры поиска?", UserRole.ROP)
    )
    assert result.category == DocumentCategory.SYSTEM
    assert result.intent in {IntentType.HELP, IntentType.SEARCH}


def test_cache_invalidation(settings):
    cache = RetrievalCache(settings)
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            doc_id="doc_a",
            section_title="S",
            text="t",
            score=0.9,
            priority=Priority.HIGH,
            category=DocumentCategory.SYSTEM,
        )
    ]
    key = RetrievalCache.make_key("q", {"category": "system"}, 4)
    cache.set(key, chunks, IntentType.HELP, DocumentCategory.SYSTEM)
    loaded, hit = cache.get(key)
    assert hit is True
    assert loaded[0].doc_id == "doc_a"
    cache.invalidate_doc("doc_a")
    loaded_after, hit_after = cache.get(key)
    assert hit_after is False or loaded_after is None
