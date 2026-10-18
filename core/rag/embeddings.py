import asyncio
import logging
from typing import Sequence

from langchain_openai import OpenAIEmbeddings
from openai import APITimeoutError, RateLimitError

from core.config.settings import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            api_key=settings.openai_api_key or None,
            base_url=settings.openai_base_url,
            max_retries=0,
        )

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        batches = [
            list(texts[i : i + self._settings.chunk_batch_size])
            for i in range(0, len(texts), self._settings.chunk_batch_size)
        ]
        results = await asyncio.gather(*(self._embed_batch(batch) for batch in batches))
        return [vector for batch_vectors in results for vector in batch_vectors]

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        attempt = 0
        while True:
            try:
                return await self._client.aembed_documents(texts)
            except (RateLimitError, APITimeoutError) as exc:
                attempt += 1
                if attempt > self._settings.openai_max_retries:
                    logger.error("Embedding API failed after retries: %s", exc)
                    raise
                delay = self._settings.openai_retry_base_delay_sec * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding retry %s/%s after %ss: %s",
                    attempt,
                    self._settings.openai_max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
