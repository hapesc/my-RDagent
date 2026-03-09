"""Task-22 tests for branch/artifact services and branch-aware UI helpers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.control_plane import build_control_plane_app
from app.fastapi_compat import TestClient
from app.run_supervisor import RunSupervisor, RunSupervisorConfig
from app.runtime import build_runtime
from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import Event, EventType, ExperimentNode, RunSession, RunStatus, StepState, StopConditions
from ui.trace_ui import (
    build_branch_compare_summary,
    load_artifact_manifest,
    load_branches,
    load_event_page,
    load_events,
    perform_control_action,
)


class Task22BranchAwareUITests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmpdir.name)
        self._env_patch = patch.dict(
            os.environ,
            {
                "AGENTRD_SQLITE_PATH": str(tmp_path / "meta.db"),
                "AGENTRD_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
                "AGENTRD_WORKSPACE_ROOT": str(tmp_path / "workspaces"),
                "AGENTRD_TRACE_STORAGE_PATH": str(tmp_path / "trace.jsonl"),
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "1",
            },
            clear=False,
        )
        self._env_patch.start()
        self.supervisor = RunSupervisor(RunSupervisorConfig(loop_poll_interval_sec=0.01))
        self.client = TestClient(build_control_plane_app(self.supervisor))

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _seed_branch_dataset(self, run_id: str = "run-task-22") -> str:
        runtime = build_runtime()
        sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=runtime.config.sqlite_path))
        run_session = RunSession(
            run_id=run_id,
            scenario="synthetic_research",
            status=RunStatus.COMPLETED,
            stop_conditions=StopConditions(max_loops=2, max_duration_sec=60),
            entry_input={"task_summary": "task-22 dataset"},
            active_branch_ids=["main", "main-fork-001"],
        )
        sqlite_store.create_run(run_session)

        workspace_root = Path(runtime.config.workspace_root) / run_id
        artifact_root = Path(runtime.config.artifact_root) / run_id
        main_workspace = workspace_root / "main-loop"
        fork_workspace = workspace_root / "fork-loop"
        main_workspace.mkdir(parents=True, exist_ok=True)
        fork_workspace.mkdir(parents=True, exist_ok=True)
        artifact_root.mkdir(parents=True, exist_ok=True)

        (main_workspace / "main.txt").write_text("main", encoding="utf-8")
        (fork_workspace / "fork.txt").write_text("fork", encoding="utf-8")
        main_artifact = artifact_root / "main-summary.json"
        fork_artifact = artifact_root / "fork-summary.json"
        main_artifact.write_text('{"branch":"main"}', encoding="utf-8")
        fork_artifact.write_text('{"branch":"fork"}', encoding="utf-8")

        runtime.branch_store.record_node(
            ExperimentNode(
                node_id="node-main-0",
                run_id=run_id,
                branch_id="main",
                loop_index=0,
                step_state=StepState.RECORDED,
                workspace_ref=str(main_workspace),
                result_ref=json.dumps([str(main_artifact)]),
            )
        )
        runtime.branch_store.record_node(
            ExperimentNode(
                node_id="node-main-fork-001-0",
                run_id=run_id,
                branch_id="main-fork-001",
                parent_node_id="node-main-0",
                loop_index=0,
                step_state=StepState.RECORDED,
                workspace_ref=str(fork_workspace),
                result_ref=json.dumps([str(fork_artifact)]),
            )
        )

        sqlite_store.append_event(
            Event(
                event_id="event-main-1",
                run_id=run_id,
                branch_id="main",
                loop_index=0,
                step_name="proposing",
                event_type=EventType.HYPOTHESIS_GENERATED,
                payload={"branch": "main"},
            )
        )
        sqlite_store.append_event(
            Event(
                event_id="event-main-2",
                run_id=run_id,
                branch_id="main",
                loop_index=0,
                step_name="recording",
                event_type=EventType.TRACE_RECORDED,
                payload={"branch": "main"},
            )
        )
        sqlite_store.append_event(
            Event(
                event_id="event-fork-1",
                run_id=run_id,
                branch_id="main-fork-001",
                loop_index=0,
                step_name="recording",
                event_type=EventType.TRACE_RECORDED,
                payload={"branch": "fork"},
            )
        )
        return run_id

    def test_branch_services_feed_ui_helpers_with_shared_dtos(self) -> None:
        run_id = self._seed_branch_dataset()
        sqlite_path = os.environ["AGENTRD_SQLITE_PATH"]
        workspace_root = os.environ["AGENTRD_WORKSPACE_ROOT"]
        artifact_root = os.environ["AGENTRD_ARTIFACT_ROOT"]

        branches = load_branches(sqlite_path, run_id)
        self.assertEqual([item.branch_id for item in branches.items], ["main", "main-fork-001"])

        with patch("ui.trace_ui.load_event_page", wraps=load_event_page) as wrapped_loader:
            main_events = load_events(sqlite_path, run_id, branch_id="main", page_limit=1)
        self.assertEqual(len(main_events), 2)
        self.assertEqual([call.kwargs["cursor"] for call in wrapped_loader.call_args_list], [None, "1"])

        fork_artifacts = load_artifact_manifest(
            sqlite_path=sqlite_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            run_id=run_id,
            branch_id="main-fork-001",
        )
        fork_paths = [item.path for item in fork_artifacts.items]
        self.assertTrue(any(path.endswith("fork.txt") for path in fork_paths))
        self.assertTrue(any(path.endswith("fork-summary.json") for path in fork_paths))
        self.assertFalse(any(path.endswith("main.txt") for path in fork_paths))

        compare_summary = build_branch_compare_summary(
            sqlite_path=sqlite_path,
            workspace_root=workspace_root,
            artifact_root=artifact_root,
            run_id=run_id,
            selected_branch_id="main-fork-001",
        )
        self.assertEqual(compare_summary["baseline_head_node_id"], "node-main-0")
        self.assertEqual(compare_summary["selected_head_node_id"], "node-main-fork-001-0")
        self.assertEqual(compare_summary["baseline_event_count"], 2)
        self.assertEqual(compare_summary["selected_event_count"], 1)

    def test_control_plane_branch_endpoints_support_branch_filters(self) -> None:
        run_id = self._seed_branch_dataset()

        events_response = self.client.get(f"/runs/{run_id}/events", params={"branch_id": "main", "limit": 1})
        self.assertEqual(events_response.status_code, 200)
        self.assertEqual(len(events_response.json()["items"]), 1)
        self.assertEqual(events_response.json()["next_cursor"], "1")

        branches_response = self.client.get(f"/runs/{run_id}/branches")
        self.assertEqual(branches_response.status_code, 200)
        self.assertEqual(
            [item["branch_id"] for item in branches_response.json()["items"]],
            ["main", "main-fork-001"],
        )

        artifacts_response = self.client.get(
            f"/runs/{run_id}/artifacts",
            params={"branch_id": "main-fork-001"},
        )
        self.assertEqual(artifacts_response.status_code, 200)
        artifact_paths = [item["path"] for item in artifacts_response.json()["items"]]
        self.assertTrue(any(path.endswith("fork.txt") for path in artifact_paths))
        self.assertFalse(any(path.endswith("main.txt") for path in artifact_paths))

    def test_ui_control_action_helper_round_trips_run_control_dto(self) -> None:
        create_response = self.client.post(
            "/runs",
            json={
                "scenario": "data_science",
                "task_summary": "task-22 ui control",
                "entry_input": {
                    "command": "python3 pipeline.py && python3 -c \"import time; time.sleep(0.2)\""
                },
                "stop_conditions": {"max_loops": 4, "max_duration_sec": 60},
            },
        )
        self.assertEqual(create_response.status_code, 200)
        run_id = create_response.json()["run_id"]

        pause_result = perform_control_action(self.client, run_id, "pause")
        self.assertEqual(pause_result.action, "pause")
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))
        self.assertEqual(self.client.get(f"/runs/{run_id}").json()["status"], "PAUSED")

        resume_result = perform_control_action(self.client, run_id, "resume")
        self.assertEqual(resume_result.action, "resume")
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))
        self.assertEqual(self.client.get(f"/runs/{run_id}").json()["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
