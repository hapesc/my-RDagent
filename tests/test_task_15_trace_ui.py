"""Task-15 tests for trace UI data helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event, EventType, RunSession, RunStatus, StopConditions
from ui.trace_ui import build_timeline_rows, list_artifacts, load_events, load_run_ids


class TraceUIHelperTests(unittest.TestCase):
    def test_load_runs_events_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sqlite_path = str(tmp_path / "meta.db")
            store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))

            run = RunSession(
                run_id="run-task-15",
                scenario="data_science",
                status=RunStatus.RUNNING,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                entry_input={"task_id": "task-15"},
            )
            store.create_run(run)
            store.append_event(
                Event(
                    event_id="event-1",
                    run_id="run-task-15",
                    branch_id="main",
                    loop_index=0,
                    step_name="trace",
                    event_type=EventType.TRACE_RECORDED,
                    payload={"status": "ok"},
                )
            )

            run_ids = load_run_ids(sqlite_path)
            events = load_events(sqlite_path, "run-task-15")
            rows = build_timeline_rows(events)

            self.assertEqual(run_ids, ["run-task-15"])
            self.assertEqual(len(events), 1)
            self.assertEqual(rows[0]["event_type"], "trace.recorded")

            workspace_root = tmp_path / "workspaces"
            artifact_root = tmp_path / "artifacts"
            (workspace_root / "run-task-15").mkdir(parents=True, exist_ok=True)
            (artifact_root / "run-task-15").mkdir(parents=True, exist_ok=True)
            (workspace_root / "run-task-15" / "a.txt").write_text("a", encoding="utf-8")
            (artifact_root / "run-task-15" / "metrics.json").write_text("{}", encoding="utf-8")

            artifacts = list_artifacts(str(workspace_root), str(artifact_root), "run-task-15")
            self.assertEqual(len(artifacts), 2)


if __name__ == "__main__":
    unittest.main()
