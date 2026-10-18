import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

import diskcache

from core.config.settings import Settings
from core.rag.models import DocumentCategory, IntentType, RetrievedChunk

logger = logging.getLogger(__name__)


class RetrievalCache:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        settings.disk_cache_path.mkdir(parents=True, exist_ok=True)
        self._disk = diskcache.Cache(str(settings.disk_cache_path))
        self._memory: OrderedDict[str, list[RetrievedChunk]] = OrderedDict()

    @staticmethod
    def make_key(query: str, filter_dict: dict[str, Any], k: int) -> str:
        payload = json.dumps(
            {"query": query, "filter": filter_dict, "k": k},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> tuple[list[RetrievedChunk] | None, bool]:
        if key in self._memory:
            self._memory.move_to_end(key)
            return self._memory[key], True

        disk_hit = self._disk.get(key)
        if disk_hit is not None:
            chunks = [RetrievedChunk.model_validate(item) for item in disk_hit]
            self._set_memory(key, chunks)
            return chunks, True
        return None, False

    def set(
        self,
        key: str,
        chunks: list[RetrievedChunk],
        intent: IntentType,
        category: DocumentCategory | None,
    ) -> None:
        serialized = [chunk.model_dump() for chunk in chunks]
        ttl = self._resolve_ttl(intent, category)
        self._disk.set(key, serialized, expire=ttl)
        self._set_memory(key, chunks)

    def invalidate_all(self) -> None:
        self._disk.clear()
        self._memory.clear()
        logger.info("Retrieval cache fully invalidated")

    def invalidate_doc(self, doc_id: str) -> None:
        removed = 0
        for key in list(self._disk):
            value = self._disk.get(key)
            if not value:
                continue
            if any(item.get("doc_id") == doc_id for item in value):
                del self._disk[key]
                removed += 1
        if removed:
            self._memory.clear()
            logger.info("Invalidated cache entries for doc_id=%s (%s keys)", doc_id, removed)

    def _set_memory(self, key: str, chunks: list[RetrievedChunk]) -> None:
        self._memory[key] = chunks
        self._memory.move_to_end(key)
        while len(self._memory) > self._settings.lru_cache_maxsize:
            self._memory.popitem(last=False)

    def _resolve_ttl(
        self,
        intent: IntentType,
        category: DocumentCategory | None,
    ) -> int:
        if intent == IntentType.HELP or category == DocumentCategory.SYSTEM:
            return self._settings.disk_cache_ttl_faq_sec
        return self._settings.disk_cache_ttl_technical_sec
