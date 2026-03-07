"""Service scaffold for the Memory Service module."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Dict, Iterator

from data_models import ContextPack


@dataclass
class MemoryServiceConfig:
    """Configuration for memory indexing and retrieval."""

    max_context_items: int = 10
    index_backend: str = "in_memory"
    db_path: str = ":memory:"


class MemoryService:
    """Stores and retrieves historical solutions and insights."""

    def __init__(self, config: MemoryServiceConfig) -> None:
        """Initialize memory service with retrieval limits."""

        self._config = config
        self._db_path = config.db_path
        self._db_uri = False
        self._memory_anchor: sqlite3.Connection | None = None

        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._db_path = f"file:memory_service_{id(self)}?mode=memory&cache=shared"
            self._db_uri = True
            self._memory_anchor = sqlite3.connect(self._db_path, uri=True)
            self._memory_anchor.row_factory = sqlite3.Row

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, uri=self._db_uri)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _managed_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._managed_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS failure_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def write_memory(self, item: str, metadata: Dict[str, str]) -> None:
        """Write a memory item into storage.

        Responsibility:
            Persist a summary item and its metadata for later retrieval.
        Input semantics:
            - item: Human-readable summary string
            - metadata: Key-value metadata for indexing
        Output semantics:
            None.
        Architecture mapping:
            Memory Service -> write_memory
        """

        payload = json.dumps(metadata, sort_keys=True)
        with self._managed_connection() as conn:
            conn.execute(
                "INSERT INTO failure_cases (item, metadata) VALUES (?, ?)",
                (item, payload),
            )

    def query_context(self, query: Dict[str, str]) -> ContextPack:
        """Retrieve a context pack for reasoning.

        Responsibility:
            Assemble relevant memory items into a context pack.
        Input semantics:
            - query: Selection criteria for memory retrieval
        Output semantics:
            ContextPack containing summaries and highlights.
        Architecture mapping:
            Memory Service -> query_context
        """

        sql = "SELECT item FROM failure_cases"
        clauses = []
        params = []

        for key, value in query.items():
            clauses.append("metadata LIKE ?")
            params.append(f'%"{key}": "{value}"%')

        if clauses:
            sql = f"{sql} WHERE {' AND '.join(clauses)}"

        sql = f"{sql} ORDER BY id DESC LIMIT ?"
        params.append(self._config.max_context_items)

        with self._managed_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        items = [str(row["item"]) for row in rows]
        highlights = list(query.keys()) if items else []
        return ContextPack(items=items, highlights=highlights)

    def get_memory_stats(self) -> Dict[str, int]:
        """Return basic memory statistics.

        Responsibility:
            Provide counts for memory indexing and storage.
        Input semantics:
            None.
        Output semantics:
            Dictionary with basic counts.
        Architecture mapping:
            Memory Service -> get_memory_stats
        """

        with self._managed_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM failure_cases").fetchone()
        return {"items": int(row["count"]) if row is not None else 0}
