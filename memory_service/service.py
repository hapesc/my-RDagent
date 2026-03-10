"""Service scaffold for the Memory Service module."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from data_models import ContextPack
from memory_service.hypothesis_selector import rank_by_kernel
from memory_service.interaction_kernel import HypothesisRecord

logger = logging.getLogger(__name__)
_CONTEXT_QUERY_CONTROL_KEYS = {"branch_id"}


@dataclass
class MemoryServiceConfig:
    """Configuration for memory indexing and retrieval."""

    max_context_items: int = 10
    index_backend: str = "in_memory"
    db_path: str = ":memory:"
    enable_hypothesis_storage: bool = False


class MemoryService:
    """Stores and retrieves historical solutions and insights."""

    def __init__(self, config: MemoryServiceConfig, hypothesis_selector=None, interaction_kernel=None) -> None:
        """Initialize memory service with retrieval limits."""

        self._config = config
        self._db_path = config.db_path
        self._db_uri = False
        self._memory_anchor: sqlite3.Connection | None = None
        self._hypothesis_selector = hypothesis_selector
        self._interaction_kernel = interaction_kernel

        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._db_path = f"file:memory_service_{uuid.uuid4().hex}?mode=memory&cache=shared"
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
            logger.exception(
                f"Database operation failed in MemoryService._managed_connection(db_path={self._db_path}); rolling back"
            )
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
            if self._config.enable_hypothesis_storage:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hypotheses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        score REAL DEFAULT 0.0,
                        branch_id TEXT DEFAULT '',
                        timestamp REAL DEFAULT 0.0,
                        metadata TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

    def write_memory(self, item: str, metadata: dict[str, str]) -> None:
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

    @staticmethod
    def _parse_int(value: object, default: int) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _summarize_text(text: str, max_chars: int = 160) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max_chars - 3]}..."

    def _build_context_items(self, query: dict[str, str], items: list[str]) -> list[str]:
        if items:
            return items

        context_items = []
        for key, value in query.items():
            if key in _CONTEXT_QUERY_CONTROL_KEYS:
                continue
            context_items.append(f"{key}: {value}")
        return context_items

    def _select_reference_hypothesis(
        self,
        query: dict[str, str],
        items: list[str],
        candidates: list[HypothesisRecord],
    ) -> HypothesisRecord:
        if not candidates:
            raise ValueError("candidates list must not be empty")

        if self._hypothesis_selector is None:
            return max(candidates, key=lambda hypothesis: hypothesis.score)

        context_items = self._build_context_items(query, items)
        iteration = self._parse_int(query.get("iteration"), default=1)
        max_iterations = self._parse_int(query.get("max_iterations"), default=max(1, iteration))
        task_summary = str(query.get("task_summary", ""))
        scenario_name = str(query.get("scenario_name", query.get("scenario", "memory")))

        adaptive_select = getattr(self._hypothesis_selector, "adaptive_select", None)
        if callable(adaptive_select):
            selected = adaptive_select(
                candidates,
                iteration,
                max_iterations,
                context_items,
                task_summary,
                scenario_name,
            )
            selected_text = str(getattr(selected, "modified_hypothesis", "") or "")
            if selected_text:
                matched = next((candidate for candidate in candidates if candidate.text == selected_text), None)
                if matched is not None:
                    return matched
                return HypothesisRecord(
                    text=selected_text,
                    score=max(candidate.score for candidate in candidates),
                    timestamp=time.time(),
                    branch_id=str(query.get("branch_id", "") or candidates[0].branch_id),
                )

        select_hypothesis = getattr(self._hypothesis_selector, "select_hypothesis", None)
        if callable(select_hypothesis):
            selected_hypothesis = select_hypothesis(candidates, "\n".join(context_items))
            if isinstance(selected_hypothesis, HypothesisRecord):
                return selected_hypothesis

        return max(candidates, key=lambda hypothesis: hypothesis.score)

    def _rank_hypothesis_candidates(
        self,
        query: dict[str, str],
        items: list[str],
        candidates: list[HypothesisRecord],
    ) -> list[tuple[str, float]]:
        if not candidates:
            return []

        if self._interaction_kernel is None:
            return [(candidate.text, candidate.score) for candidate in candidates]

        reference = self._select_reference_hypothesis(query, items, candidates)
        ranked = rank_by_kernel(reference, candidates, self._interaction_kernel)
        return [(candidate.text, score) for candidate, score in ranked]

    def _build_highlights(self, scored_items: list[tuple[str, float]]) -> list[str]:
        top_k = min(3, self._config.max_context_items, len(scored_items))
        return [self._summarize_text(text) for text, _ in scored_items[:top_k]]

    def query_context(self, query: dict[str, str]) -> ContextPack:
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

        metadata_query = {key: value for key, value in query.items() if key not in _CONTEXT_QUERY_CONTROL_KEYS}

        for key, value in metadata_query.items():
            clauses.append(f"json_extract(metadata, ?) = ?")
            params.append(f"$.{key}")
            params.append(value)

        if clauses:
            sql = f"{sql} WHERE {' AND '.join(clauses)}"

        sql = f"{sql} ORDER BY id DESC LIMIT ?"
        params.append(self._config.max_context_items)

        with self._managed_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        items = [str(row["item"]) for row in rows]
        highlights = list(metadata_query.keys()) if items else []

        scored_items: list[tuple[str, float]] = []
        branch_id = query.get("branch_id")
        source_type: str | None = None
        timestamp: float | None = None
        if self._config.enable_hypothesis_storage:
            same_branch_hypotheses: list[HypothesisRecord] = []
            cross_branch_hypotheses: list[HypothesisRecord] = []
            if branch_id:
                same_branch_hypotheses = self.query_hypotheses(
                    branch_id=str(branch_id),
                    limit=self._config.max_context_items,
                )
                cross_branch_hypotheses = self.get_cross_branch_hypotheses(
                    str(branch_id),
                    limit=self._config.max_context_items,
                )
            else:
                same_branch_hypotheses = self.query_hypotheses(limit=self._config.max_context_items)

            candidates = same_branch_hypotheses + cross_branch_hypotheses
            if candidates:
                source_type = "cross_branch" if cross_branch_hypotheses else "memory"
                timestamp = max(candidate.timestamp for candidate in candidates)
                try:
                    scored_items = self._rank_hypothesis_candidates(query, items, candidates)
                except Exception:
                    logger.warning(
                        "query_context hypothesis ranking failed; using stored hypothesis ordering",
                        exc_info=True,
                    )
                    scored_items = [(candidate.text, candidate.score) for candidate in candidates]
                highlights = self._build_highlights(scored_items) or highlights

        return ContextPack(
            items=items,
            highlights=highlights,
            scored_items=scored_items,
            branch_id=str(branch_id) if branch_id is not None else None,
            source_type=source_type,
            timestamp=timestamp,
        )

    def get_memory_stats(self) -> dict[str, int]:
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
        stats = {"items": int(row["count"]) if row is not None else 0}
        if self._config.enable_hypothesis_storage:
            with self._managed_connection() as conn:
                h_row = conn.execute("SELECT COUNT(*) AS count FROM hypotheses").fetchone()
            stats["hypothesis_count"] = int(h_row["count"]) if h_row is not None else 0
        return stats

    def write_hypothesis(
        self,
        text: str,
        score: float,
        branch_id: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        ts = time.time()
        meta_json = json.dumps(metadata or {}, sort_keys=True)
        with self._managed_connection() as conn:
            conn.execute(
                "INSERT INTO hypotheses (text, score, branch_id, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (text, score, branch_id, ts, meta_json),
            )

    def query_hypotheses(self, branch_id: str | None = None, limit: int = 10) -> list[HypothesisRecord]:
        if branch_id is not None:
            sql = (
                "SELECT text, score, timestamp, branch_id FROM hypotheses WHERE branch_id = ? ORDER BY id DESC LIMIT ?"
            )
            params = (branch_id, limit)  # type: tuple
        else:
            sql = "SELECT text, score, timestamp, branch_id FROM hypotheses ORDER BY id DESC LIMIT ?"
            params = (limit,)
        with self._managed_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            HypothesisRecord(
                text=str(row["text"]),
                score=float(row["score"]),
                timestamp=float(row["timestamp"]),
                branch_id=str(row["branch_id"]),
            )
            for row in rows
        ]

    def get_cross_branch_hypotheses(self, exclude_branch: str, limit: int = 10) -> list[HypothesisRecord]:
        sql = (
            "SELECT text, score, timestamp, branch_id FROM hypotheses WHERE branch_id != ? ORDER BY score DESC LIMIT ?"
        )
        with self._managed_connection() as conn:
            rows = conn.execute(sql, (exclude_branch, limit)).fetchall()
        return [
            HypothesisRecord(
                text=str(row["text"]),
                score=float(row["score"]),
                timestamp=float(row["timestamp"]),
                branch_id=str(row["branch_id"]),
            )
            for row in rows
        ]
