import logging
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from core.config.settings import Settings
from core.rag.models import ChunkMetadata, DocumentCategory, Priority

logger = logging.getLogger(__name__)


def _serialize_list(values: list[str]) -> str:
    return ",".join(sorted(set(values)))


def _chunk_to_chroma_metadata(chunk: ChunkMetadata) -> dict[str, Any]:
    return {
        "doc_id": chunk.doc_id,
        "category": chunk.category.value,
        "audience": _serialize_list([a.value for a in chunk.audience]),
        "tags": _serialize_list(chunk.tags),
        "section_title": chunk.section_title,
        "is_table": chunk.is_table,
        "priority": chunk.priority.value,
        "chunk_id": chunk.chunk_id,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "source_file": chunk.source_file,
    }


class ChromaStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        settings.chroma_persist_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> Collection:
        return self._client.get_or_create_collection(
            name=self._settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Collection:
        return self._collection

    def upsert_chunks(
        self,
        chunks: list[ChunkMetadata],
        embeddings: list[list[float]],
    ) -> int:
        if not chunks:
            return 0
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [_chunk_to_chroma_metadata(chunk) for chunk in chunks]
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def delete_by_doc_id(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def similarity_search(
        self,
        query_embedding: list[float],
        *,
        where: dict[str, Any] | None,
        k: int,
    ) -> list[tuple[str, str, dict[str, Any], float]]:
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        if not result["ids"] or not result["ids"][0]:
            return []

        rows: list[tuple[str, str, dict[str, Any], float]] = []
        for idx, chunk_id in enumerate(result["ids"][0]):
            document = result["documents"][0][idx] if result["documents"] else ""
            metadata = result["metadatas"][0][idx] if result["metadatas"] else {}
            distance = result["distances"][0][idx] if result["distances"] else 1.0
            similarity = max(0.0, 1.0 - float(distance))
            rows.append((chunk_id, document or "", metadata or {}, similarity))
        return rows

    def get_stats(self) -> dict[str, Any]:
        total = self._collection.count()
        sample = self._collection.get(limit=min(total, 5000), include=["metadatas"])
        categories: dict[str, int] = {}
        for meta in sample.get("metadatas") or []:
            if not meta:
                continue
            category = str(meta.get("category", "unknown"))
            categories[category] = categories.get(category, 0) + 1
        return {
            "name": self._settings.chroma_collection_name,
            "chunk_count": total,
            "categories": categories,
        }

    @staticmethod
    def build_category_filter(categories: list[DocumentCategory]) -> dict[str, Any]:
        values = [category.value for category in categories]
        if len(values) == 1:
            return {"category": values[0]}
        return {"category": {"$in": values}}

    @staticmethod
    def audience_matches(metadata: dict[str, Any], user_role: str) -> bool:
        audience_raw = str(metadata.get("audience", ""))
        if not audience_raw:
            return True
        roles = {item.strip().lower() for item in audience_raw.split(",") if item.strip()}
        return user_role.lower() in roles or "admin" in roles

    @staticmethod
    def priority_from_metadata(metadata: dict[str, Any]) -> Priority:
        try:
            return Priority(str(metadata.get("priority", Priority.MEDIUM.value)).lower())
        except ValueError:
            return Priority.MEDIUM
