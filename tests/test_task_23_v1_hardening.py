"""Task-23 tests for V1 API contracts, smoke baselines, and service hardening."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.control_plane import build_control_plane_app
from app.control_plane_client import ControlPlaneClient
from app.fastapi_compat import TestClient
from app.run_supervisor import RunSupervisor, RunSupervisorConfig
from service_contracts import ErrorCode, RunCreateRequest, ServiceContractError
from ui.trace_ui import (
    build_timeline_rows,
    load_artifact_manifest,
    load_branches,
    load_events,
    load_run_ids,
    load_run_summary,
)

from tests._llm_test_utils import patch_runtime_llm_provider


class Task23V1HardeningTests(unittest.TestCase):
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
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "45",
            },
            clear=False,
        )
        self._env_patch.start()
        self._llm_patch = patch_runtime_llm_provider()
        self._llm_patch.start()
        self.supervisor = RunSupervisor(RunSupervisorConfig(loop_poll_interval_sec=0.01))
        self.client = ControlPlaneClient(TestClient(build_control_plane_app(self.supervisor)))

    def tearDown(self) -> None:
        self._llm_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_remote_client_can_create_control_and_monitor_runs(self) -> None:
        running = self.client.create_run(
            {
                "scenario": "data_science",
                "task_summary": "task-23 remote control",
                "entry_input": {
                    "command": "python3 pipeline.py && python3 -c \"import time; time.sleep(0.2)\""
                },
                "stop_conditions": {"max_loops": 4, "max_duration_sec": 60},
            }
        )
        self.assertEqual(running.scenario, "data_science")

        pause_response = self.client.pause_run(running.run_id)
        self.assertEqual(pause_response.action, "pause")
        self.assertTrue(self.supervisor.wait_for_idle(running.run_id, timeout_sec=3.0))
        self.assertEqual(self.client.get_run(running.run_id).status, "PAUSED")

        resume_response = self.client.resume_run(running.run_id)
        self.assertEqual(resume_response.action, "resume")
        self.assertTrue(self.supervisor.wait_for_idle(running.run_id, timeout_sec=3.0))

        completed = self.client.get_run(running.run_id)
        self.assertEqual(completed.status, "COMPLETED")

        events_page = self.client.list_events(running.run_id, limit=2)
        self.assertLessEqual(len(events_page.items), 2)
        self.assertEqual(events_page.limit, 2)

        artifacts = self.client.list_artifacts(running.run_id)
        branches = self.client.list_branches(running.run_id)
        scenarios = self.client.list_scenarios()
        health = self.client.health()
        manifests = {manifest.scenario_name: manifest for manifest in scenarios}

        self.assertTrue(
            any(item.path.endswith(name) for item in artifacts.items for name in ("pipeline.py", "metrics.json"))
        )
        self.assertEqual(branches.items[0].branch_id, "main")
        self.assertIn("synthetic_research", manifests)
        self.assertEqual(manifests["data_science"].default_step_overrides.proposal.model, "ds-proposal-default")
        self.assertEqual(manifests["data_science"].default_step_overrides.running.timeout_sec, 45)
        self.assertEqual(
            manifests["synthetic_research"].default_step_overrides.feedback.model,
            "synthetic-feedback-default",
        )
        self.assertIn(health["status"], {"ok", "degraded"})

    def test_invalid_requests_and_missing_resources_stay_structured(self) -> None:
        with self.assertRaises(ServiceContractError) as invalid_request:
            self.client.create_run(
                RunCreateRequest(
                    scenario="data_science",
                    task_summary="bad request",
                    step_overrides={"running": {"timeout_sec": 0}},  # type: ignore[arg-type]
                )
            )
        self.assertEqual(invalid_request.exception.code, ErrorCode.INVALID_REQUEST)

        with self.assertRaises(ServiceContractError) as missing_run:
            self.client.get_run("missing-run")
        self.assertEqual(missing_run.exception.code, ErrorCode.NOT_FOUND)

    def test_smoke_metadata_and_ui_first_screen_baselines(self) -> None:
        run = self.client.create_run(
            {
                "scenario": "synthetic_research",
                "task_summary": "task-23 smoke",
                "entry_input": {"reference_topics": ["llm", "evaluation"]},
                "stop_conditions": {"max_loops": 1, "max_duration_sec": 60},
            }
        )
        self.assertTrue(self.supervisor.wait_for_idle(run.run_id, timeout_sec=3.0))

        metadata_start = time.monotonic()
        summary = self.client.get_run(run.run_id)
        branches = self.client.list_branches(run.run_id)
        metadata_elapsed = time.monotonic() - metadata_start

        ui_start = time.monotonic()
        run_ids = load_run_ids(os.environ["AGENTRD_SQLITE_PATH"])
        ui_summary = load_run_summary(os.environ["AGENTRD_SQLITE_PATH"], run.run_id)
        ui_branches = load_branches(os.environ["AGENTRD_SQLITE_PATH"], run.run_id)
        ui_events = load_events(os.environ["AGENTRD_SQLITE_PATH"], run.run_id, page_limit=2)
        timeline_rows = build_timeline_rows(ui_events)
        artifacts = load_artifact_manifest(
            sqlite_path=os.environ["AGENTRD_SQLITE_PATH"],
            workspace_root=os.environ["AGENTRD_WORKSPACE_ROOT"],
            artifact_root=os.environ["AGENTRD_ARTIFACT_ROOT"],
            run_id=run.run_id,
        )
        ui_elapsed = time.monotonic() - ui_start

        self.assertLess(metadata_elapsed, 2.0)
        self.assertLess(ui_elapsed, 5.0)
        self.assertIn(run.run_id, run_ids)
        self.assertEqual(summary.status, "COMPLETED")
        self.assertIsNotNone(ui_summary)
        assert ui_summary is not None
        self.assertEqual(ui_summary.status, "COMPLETED")
        self.assertEqual(branches.items[0].branch_id, "main")
        self.assertEqual(ui_branches.items[0].branch_id, "main")
        self.assertGreaterEqual(len(timeline_rows), 1)
        self.assertTrue(any(item.path.endswith("research_summary.json") for item in artifacts.items))


if __name__ == "__main__":
    unittest.main()
