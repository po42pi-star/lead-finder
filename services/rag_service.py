import logging
import time
from pathlib import Path

from core.config.settings import Settings
from core.rag.cache import RetrievalCache
from core.rag.chunker import MarkdownChunker
from core.rag.chroma_store import ChromaStore
from core.rag.document_loader import DocumentLoader
from core.rag.embeddings import EmbeddingService
from core.rag.models import IngestResponse, SearchRequest, SearchResponse
from core.rag.retrieval import RetrievalPipeline

logger = logging.getLogger(__name__)


class MockRetrievalLogger:
    async def log(self, *, query, filters, retrieved_doc_ids, cache_hit, latency_ms, retrieval_metadata):
        pass


class RagService:
    def __init__(
        self,
        settings: Settings,
        loader: DocumentLoader,
        chunker: MarkdownChunker,
        embeddings: EmbeddingService,
        chroma: ChromaStore,
        cache: RetrievalCache,
        pipeline: RetrievalPipeline,
        retrieval_logger: MockRetrievalLogger = None,
    ) -> None:
        self._settings = settings
        self._loader = loader
        self._chunker = chunker
        self._embeddings = embeddings
        self._chroma = chroma
        self._cache = cache
        self._pipeline = pipeline
        self._retrieval_logger = retrieval_logger or MockRetrievalLogger()

    def count_files(self, path: str | None = None) -> int:
        return len(self._loader.discover_files(path or None))

    async def ingest(self, path: str, force_rebuild: bool = False) -> IngestResponse:
        files = self._loader.discover_files(path or None)
        if not files:
            return IngestResponse(
                status="empty",
                message=f"No markdown files found under {path}",
                files_queued=0,
            )

        total_chunks = 0
        for index, file_path in enumerate(files, start=1):
            logger.info("Ingesting file %s/%s: %s", index, len(files), file_path)
            metadata, body = self._loader.load(file_path)
            source_file = metadata.extra.get("source_file", str(file_path.name))

            if force_rebuild:
                self._chroma.delete_by_doc_id(metadata.doc_id)
                self._cache.invalidate_doc(metadata.doc_id)

            chunks = self._chunker.chunk_document(metadata, body, source_file)
            if not chunks:
                logger.warning("No chunks produced for %s", file_path)
                continue

            vectors = await self._embeddings.embed_texts([chunk.text for chunk in chunks])
            upserted = self._chroma.upsert_chunks(chunks, vectors)
            total_chunks += upserted
            logger.info("Upserted %s chunks for doc_id=%s", upserted, metadata.doc_id)

        self._cache.invalidate_all()
        return IngestResponse(
            status="completed",
            message=f"Ingested {len(files)} files, {total_chunks} chunks",
            files_queued=len(files),
        )

    async def search(self, request: SearchRequest) -> SearchResponse:
        started = time.perf_counter()
        response, metadata = await self._pipeline.search(request)
        latency_ms = int((time.perf_counter() - started) * 1000)

        await self._retrieval_logger.log(
            query=request.query,
            filters=metadata["filters"],
            retrieved_doc_ids=metadata["retrieved_doc_ids"],
            cache_hit=metadata["cache_hit"],
            latency_ms=latency_ms,
            retrieval_metadata=metadata["retrieval_metadata"],
        )
        logger.info(
            "retrieval_metadata query=%r cache_hit=%s latency_ms=%s docs=%s",
            request.query,
            metadata["cache_hit"],
            latency_ms,
            metadata["retrieved_doc_ids"],
        )
        return response

    def collections_stats(self) -> dict:
        return self._chroma.get_stats()
