"""Task-15 tests for trace UI data helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event, EventType, RunSession, RunStatus, StopConditions
from service_contracts import RunControlResponse
from ui.trace_ui import build_timeline_rows, list_artifacts, load_events, load_run_ids, load_run_summary, perform_control_action


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
            run_summary = load_run_summary(sqlite_path, "run-task-15")

            self.assertEqual(run_ids, ["run-task-15"])
            self.assertEqual(len(events), 1)
            self.assertEqual(rows[0]["event_type"], "trace.recorded")
            assert run_summary is not None
            self.assertEqual(run_summary.run_id, "run-task-15")

            workspace_root = tmp_path / "workspaces"
            artifact_root = tmp_path / "artifacts"
            (workspace_root / "run-task-15").mkdir(parents=True, exist_ok=True)
            (artifact_root / "run-task-15").mkdir(parents=True, exist_ok=True)
            (workspace_root / "run-task-15" / "a.txt").write_text("a", encoding="utf-8")
            (artifact_root / "run-task-15" / "metrics.json").write_text("{}", encoding="utf-8")

            artifacts = list_artifacts(
                sqlite_path,
                str(workspace_root),
                str(artifact_root),
                "run-task-15",
            )
            self.assertEqual(len(artifacts), 2)

    def test_perform_control_action_uses_client_method_when_available(self) -> None:
        """Verify perform_control_action calls the direct method when it exists."""
        mock_client = MagicMock()
        mock_client.pause_run.return_value = RunControlResponse(
            run_id="run-123",
            action="pause",
            status="PAUSED",
            message="paused",
        )
        
        result = perform_control_action(mock_client, "run-123", "pause")
        
        mock_client.pause_run.assert_called_once_with("run-123")
        mock_client.post.assert_not_called()
        self.assertEqual(result.run_id, "run-123")
        self.assertEqual(result.action, "pause")

    def test_perform_control_action_uses_http_post_when_method_missing(self) -> None:
        """Verify perform_control_action falls back to HTTP POST when method doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run-456",
            "action": "resume",
            "status": "RUNNING",
            "message": "resumed",
        }
        
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        # Simulate missing pause_run method
        delattr(mock_client, "pause_run")
        
        result = perform_control_action(mock_client, "run-456", "pause")
        
        mock_client.post.assert_called_once_with("/runs/run-456/pause", json={})
        self.assertEqual(result.run_id, "run-456")
        self.assertEqual(result.action, "resume")

    def test_perform_control_action_with_non_callable_method_falls_back_to_post(self) -> None:
        """Verify perform_control_action falls back to POST when attribute is not callable."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "run_id": "run-789",
            "action": "stop",
            "status": "STOPPED",
            "message": "stopped",
        }
        
        mock_client = MagicMock()
        mock_client.stop_run = "not-callable"
        mock_client.post.return_value = mock_response
        
        result = perform_control_action(mock_client, "run-789", "stop")
        
        mock_client.post.assert_called_once_with("/runs/run-789/stop", json={})
        self.assertEqual(result.run_id, "run-789")


if __name__ == "__main__":
    unittest.main()
