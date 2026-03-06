"""SQLite metadata store for runs and events."""

from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from data_models import Event, RunSession
from observability import sanitize_payload


@dataclass
class SQLiteStoreConfig:
    """Configuration for sqlite metadata store."""

    sqlite_path: str = "/tmp/rd_agent.sqlite3"


class SQLiteMetadataStore:
    """SQLite-backed store for run sessions and trace events."""

    def __init__(self, config: SQLiteStoreConfig) -> None:
        self._config = config
        self._db_path = Path(config.sqlite_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._db_path))
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
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL DEFAULT 'main',
                    timestamp TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_branch_id ON events(branch_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(events)").fetchall()
            }
            if "branch_id" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN branch_id TEXT NOT NULL DEFAULT 'main'")

    def create_run(self, run_session: RunSession) -> None:
        payload = json.dumps(run_session.to_dict(), sort_keys=True)
        with self._managed_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, payload_json) VALUES (?, ?)",
                (run_session.run_id, payload),
            )

    def get_run(self, run_id: str) -> Optional[RunSession]:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT payload_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return RunSession.from_dict(json.loads(row["payload_json"]))

    def list_runs(self) -> List[RunSession]:
        runs: List[RunSession] = []
        with self._managed_connection() as conn:
            rows = conn.execute("SELECT payload_json FROM runs ORDER BY run_id").fetchall()
        for row in rows:
            runs.append(RunSession.from_dict(json.loads(row["payload_json"])))
        return runs

    def append_event(self, event: Event) -> None:
        event_dict = event.to_dict()
        event_dict["payload"] = sanitize_payload(event_dict.get("payload", {}))
        payload = json.dumps(event_dict, sort_keys=True)
        with self._managed_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO events (event_id, run_id, branch_id, timestamp, payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    str(event_dict["event_id"]),
                    str(event_dict["run_id"]),
                    str(event_dict["branch_id"]),
                    str(event_dict["timestamp"]),
                    payload,
                ),
            )

    def query_events(self, run_id: Optional[str] = None, branch_id: Optional[str] = None) -> List[Event]:
        with self._managed_connection() as conn:
            if run_id is None and branch_id is None:
                rows = conn.execute(
                    "SELECT payload_json FROM events ORDER BY timestamp, event_id"
                ).fetchall()
            elif run_id is not None and branch_id is None:
                rows = conn.execute(
                    "SELECT payload_json FROM events WHERE run_id = ? ORDER BY timestamp, event_id",
                    (run_id,),
                ).fetchall()
            elif run_id is None and branch_id is not None:
                rows = conn.execute(
                    "SELECT payload_json FROM events WHERE branch_id = ? ORDER BY timestamp, event_id",
                    (branch_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM events WHERE run_id = ? AND branch_id = ? ORDER BY timestamp, event_id",
                    (run_id, branch_id),
                ).fetchall()

        events: List[Event] = []
        for row in rows:
            events.append(Event.from_dict(json.loads(row["payload_json"])))
        return events
