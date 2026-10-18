import json
import logging
from pathlib import Path

import aiosqlite

from core.config.settings import Settings

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS retrieval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    filters TEXT,
    retrieved_doc_ids TEXT,
    cache_hit INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    retrieval_metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


class RetrievalLogger:
    def __init__(self, settings: Settings) -> None:
        self._db_path: Path = settings.analytics_db_path

    async def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(CREATE_TABLE_SQL)
            await db.commit()

    async def log(
        self,
        *,
        query: str,
        filters: dict,
        retrieved_doc_ids: list[str],
        cache_hit: bool,
        latency_ms: int,
        retrieval_metadata: dict,
    ) -> None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    INSERT INTO retrieval_log
                    (query, filters, retrieved_doc_ids, cache_hit, latency_ms, retrieval_metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query,
                        json.dumps(filters, ensure_ascii=False),
                        json.dumps(retrieved_doc_ids, ensure_ascii=False),
                        int(cache_hit),
                        latency_ms,
                        json.dumps(retrieval_metadata, ensure_ascii=False),
                    ),
                )
                await db.commit()
        except Exception as exc:
            logger.warning("Failed to write retrieval log: %s", exc)
