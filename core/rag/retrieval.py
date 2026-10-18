import logging
from typing import Any

import tiktoken
from langchain_openai import ChatOpenAI
from openai import APITimeoutError, RateLimitError

from core.config.settings import Settings
from core.rag.cache import RetrievalCache
from core.rag.chroma_store import ChromaStore
from core.rag.embeddings import EmbeddingService
from core.rag.intent_classifier import IntentClassifier
from core.rag.models import (
    DocumentCategory,
    IntentType,
    RetrievedChunk,
    SearchRequest,
    SearchResponse,
    SourceItem,
    UserRole,
)

logger = logging.getLogger(__name__)

PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


class RetrievalPipeline:
    def __init__(
        self,
        settings: Settings,
        chroma: ChromaStore,
        embeddings: EmbeddingService,
        intent_classifier: IntentClassifier,
        cache: RetrievalCache,
    ) -> None:
        self._settings = settings
        self._chroma = chroma
        self._embeddings = embeddings
        self._intent_classifier = intent_classifier
        self._cache = cache
        self._encoding = tiktoken.get_encoding("cl100k_base")

    async def retrieve_for_chat(
        self,
        query: str,
        user_role: UserRole,
        categories: list[DocumentCategory],
        *,
        use_cache: bool = True,
    ) -> tuple[list[RetrievedChunk], bool, dict[str, Any]]:
        chroma_filter = ChromaStore.build_category_filter(categories)
        cache_key = RetrievalCache.make_key(
            query,
            chroma_filter,
            self._settings.retrieval_top_k,
        )
        cache_hit = False
        cached_chunks: list[RetrievedChunk] | None = None
        if use_cache:
            cached_chunks, cache_hit = self._cache.get(cache_key)

        if cached_chunks is None:
            query_embedding = await self._embeddings.embed_query(query)
            raw_results = self._chroma.similarity_search(
                query_embedding,
                where=chroma_filter,
                k=self._settings.retrieval_top_k * 3,
            )
            filtered = self._post_filter(raw_results, user_role)
            cached_chunks = filtered[: self._settings.retrieval_top_k]
            if use_cache:
                self._cache.set(
                    cache_key,
                    cached_chunks,
                    IntentType.SEARCH,
                    categories[0] if categories else None,
                )
            cache_hit = False

        metadata = {
            "filters": chroma_filter,
            "retrieved_doc_ids": [chunk.doc_id for chunk in cached_chunks],
            "cache_hit": cache_hit,
        }
        return cached_chunks, cache_hit, metadata

    async def search(self, request: SearchRequest) -> tuple[SearchResponse, dict[str, Any]]:
        intent_result = await self._intent_classifier.classify(
            request.query,
            request.user_role,
            request.category_override,
        )
        categories = self._resolve_categories(intent_result.category, intent_result.intent)
        chroma_filter = ChromaStore.build_category_filter(categories)
        cache_key = RetrievalCache.make_key(
            request.query,
            chroma_filter,
            self._settings.retrieval_top_k,
        )

        logger.info(
            "SEARCH query=%r category=%s threshold=%s top_k=%s",
            request.query,
            intent_result.category.value if intent_result.category else None,
            self._settings.similarity_score_threshold,
            self._settings.retrieval_top_k,
        )

        cached_chunks, cache_hit = self._cache.get(cache_key)
        if cached_chunks is None:
            query_embedding = await self._embeddings.embed_query(request.query)
            raw_results = self._chroma.similarity_search(
                query_embedding,
                where=chroma_filter,
                k=self._settings.retrieval_top_k * 3,
            )
            logger.info("Raw results from chroma: %s", len(raw_results))
            for chunk_id, text, meta, score in raw_results[:5]:
                logger.info("  doc=%s score=%.3f", meta.get("doc_id"), score)

            filtered = self._post_filter(raw_results, request.user_role)
            logger.info("After post_filter: %s chunks", len(filtered))
            
            # FALLBACK: если threshold отфильтровал всё, берём top-3 без порога
            if not filtered and raw_results:
                logger.warning("Threshold filtered all results, using fallback top-3")
                fallback_chunks = []
                for chunk_id, text, metadata, score in raw_results[:3]:
                    if ChromaStore.audience_matches(metadata, request.user_role.value):
                        priority = ChromaStore.priority_from_metadata(metadata)
                        fallback_chunks.append(
                            RetrievedChunk(
                                chunk_id=chunk_id,
                                doc_id=str(metadata.get("doc_id", "")),
                                section_title=str(metadata.get("section_title", "")),
                                text=text,
                                score=score,
                                priority=priority,
                                category=DocumentCategory(str(metadata.get("category", "sales"))),
                                is_table=bool(metadata.get("is_table", False)),
                            )
                        )
                filtered = fallback_chunks
                logger.info("Fallback returned %s chunks", len(filtered))
            
            cached_chunks = filtered[: self._settings.retrieval_top_k]
            self._cache.set(
                cache_key,
                cached_chunks,
                intent_result.intent,
                intent_result.category,
            )

        context = self._format_context(cached_chunks)
        answer = await self._generate_answer(request.query, context)

        sources = [
            SourceItem(
                doc_id=chunk.doc_id,
                section=chunk.section_title,
                score=chunk.score,
            )
            for chunk in cached_chunks
        ]
        metadata = {
            "query": request.query,
            "filters": chroma_filter,
            "retrieved_doc_ids": [chunk.doc_id for chunk in cached_chunks],
            "cache_hit": cache_hit,
            "intent": intent_result.model_dump(),
            "retrieval_metadata": {
                "chunk_ids": [chunk.chunk_id for chunk in cached_chunks],
                "categories": categories,
            },
        }
        return (
            SearchResponse(answer=answer, sources=sources, cache_hit=cache_hit),
            metadata,
        )

    def _resolve_categories(
        self,
        category: DocumentCategory | None,
        intent: IntentType,
    ) -> list[DocumentCategory]:
        if category is None:
            category = DocumentCategory.SALES
        categories = [category]
        if intent == IntentType.HELP and DocumentCategory.SYSTEM not in categories:
            categories.append(DocumentCategory.SYSTEM)
        return categories

    def _post_filter(
        self,
        raw_results: list[tuple[str, str, dict[str, Any], float]],
        user_role: UserRole,
    ) -> list[RetrievedChunk]:
        threshold = self._settings.similarity_score_threshold
        chunks: list[RetrievedChunk] = []
        for chunk_id, text, metadata, score in raw_results:
            if score < threshold:
                logger.debug("Filtered by threshold: doc=%s score=%.3f < %.3f", metadata.get("doc_id"), score, threshold)
                continue
            if not ChromaStore.audience_matches(metadata, user_role.value):
                logger.debug("Filtered by audience: doc=%s", metadata.get("doc_id"))
                continue
            priority = ChromaStore.priority_from_metadata(metadata)
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=str(metadata.get("doc_id", "")),
                    section_title=str(metadata.get("section_title", "")),
                    text=text,
                    score=score,
                    priority=priority,
                    category=DocumentCategory(str(metadata.get("category", "sales"))),
                    is_table=bool(metadata.get("is_table", False)),
                )
            )

        chunks.sort(
            key=lambda item: (-item.score, -PRIORITY_WEIGHT.get(item.priority.value, 1))
        )

        deduped: dict[str, RetrievedChunk] = {}
        for chunk in chunks:
            existing = deduped.get(chunk.doc_id)
            if existing is None or chunk.score > existing.score:
                deduped[chunk.doc_id] = chunk
        return list(deduped.values())

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        parts: list[str] = []
        token_count = 0
        for chunk in chunks:
            block = f"[DOC: {chunk.doc_id}] {chunk.section_title}\n{chunk.text}"
            block_tokens = len(self._encoding.encode(block))
            if token_count + block_tokens > self._settings.max_context_tokens:
                break
            parts.append(block)
            token_count += block_tokens
        return "\n\n---\n\n".join(parts)

    async def generate_answer(
        self,
        query: str,
        context: str,
        *,
        system_prompt: str | None = None,
        stream: bool = False,
    ):
        if not self._settings.openai_api_key:
            if not context.strip():
                text = "Контекст не найден. Укажите OPENAI_API_KEY для генерации ответа."
            else:
                text = f"Найден релевантный контекст:\n\n{context}"
            if stream:
                async def _single():
                    yield text
                return _single()
            return text

        prompt = system_prompt or (
            "Ты — ассистент базы знаний НЕВАТОМ. Тебе предоставлен контекст из внутренней базы. "
            "Используй ТОЛЬКО этот контекст. Запрещено использовать общие знания, Wikipedia, "
            "личный опыт модели.\n\n"
            "Если контекст не содержит ответа — напиши точно: "
            "'В предоставленных документах нет информации по этому вопросу.'\n\n"
            "Структура ответа:\n"
            "1. Краткое резюме (1-2 предложения).\n"
            "2. Развёрнутый ответ с деталями из контекста.\n"
            "3. Если применимо — готовая фраза/скрипт для менеджера.\n"
            "4. Блок «Источники» с doc_id.\n\n"
            "Формат: Markdown. Без приветствий и прощаний."
        )
        llm = ChatOpenAI(
            model=self._settings.openai_chat_model,
            api_key=self._settings.openai_api_key,
            base_url=self._settings.openai_base_url,
            temperature=0.2,
            max_retries=0,
        )
        messages = [
            ("system", prompt),
            ("user", f"Контекст:\n{context}\n\nВопрос: {query}"),
        ]

        if stream:
            async def _stream():
                async for chunk in llm.astream(messages):
                    if chunk.content:
                        yield str(chunk.content)
            return _stream()

        attempt = 0
        while True:
            try:
                response = await llm.ainvoke(messages)
                return str(response.content).strip()
            except (RateLimitError, APITimeoutError) as exc:
                attempt += 1
                if attempt > self._settings.openai_max_retries:
                    logger.error("Answer generation failed: %s", exc)
                    return (
                        "Сервис временно перегружен. Попробуйте повторить запрос позже."
                    )
                import asyncio

                await asyncio.sleep(
                    self._settings.openai_retry_base_delay_sec * (2 ** (attempt - 1))
                )

    async def _generate_answer(self, query: str, context: str) -> str:
        result = await self.generate_answer(query, context)
        return result if isinstance(result, str) else ""
