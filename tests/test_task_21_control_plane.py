"""Task-21 tests for the control plane and RunSupervisor."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.control_plane import build_control_plane_app
from app.fastapi_compat import TestClient
from app.run_supervisor import RunSupervisor, RunSupervisorConfig
from app.runtime import build_runtime, build_run_service
from data_models import RunSession, RunStatus, StopConditions


class ControlPlaneTests(unittest.TestCase):
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

    def test_post_runs_returns_immediately_and_background_completes(self) -> None:
        response = self.client.post(
            "/runs",
            json={
                "scenario": "synthetic_research",
                "task_summary": "background synthetic run",
                "stop_conditions": {"max_loops": 2, "max_duration_sec": 60},
            },
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["run_id"]

        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))

        get_response = self.client.get(f"/runs/{run_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["status"], "COMPLETED")

    def test_pause_resume_and_stop_drive_background_lifecycle(self) -> None:
        create_response = self.client.post(
            "/runs",
            json={
                "scenario": "data_science",
                "task_summary": "controlled data science run",
                "entry_input": {"command": 'python3 -c "import time; time.sleep(0.2)"'},
                "stop_conditions": {"max_loops": 4, "max_duration_sec": 60},
            },
        )
        run_id = create_response.json()["run_id"]

        pause_response = self.client.post(f"/runs/{run_id}/pause")
        self.assertEqual(pause_response.status_code, 200)
        self.assertEqual(pause_response.json()["action"], "pause")
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))
        paused = self.client.get(f"/runs/{run_id}").json()
        self.assertEqual(paused["status"], "PAUSED")

        resume_response = self.client.post(f"/runs/{run_id}/resume", json={})
        self.assertEqual(resume_response.status_code, 200)
        self.assertEqual(resume_response.json()["action"], "resume")
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))
        resumed = self.client.get(f"/runs/{run_id}").json()
        self.assertEqual(resumed["status"], "COMPLETED")

        stop_create = self.client.post(
            "/runs",
            json={
                "scenario": "data_science",
                "task_summary": "stop run",
                "entry_input": {"command": 'python3 -c "import time; time.sleep(0.2)"'},
                "stop_conditions": {"max_loops": 5, "max_duration_sec": 60},
            },
        )
        stop_run_id = stop_create.json()["run_id"]
        stop_response = self.client.post(f"/runs/{stop_run_id}/stop")
        self.assertEqual(stop_response.status_code, 200)
        self.assertEqual(stop_response.json()["action"], "stop")
        self.assertTrue(self.supervisor.wait_for_idle(stop_run_id, timeout_sec=3.0))
        stopped = self.client.get(f"/runs/{stop_run_id}").json()
        self.assertEqual(stopped["status"], "STOPPED")

    def test_restart_marks_running_runs_paused_until_explicit_resume(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "synthetic_research")
        run = run_service.create_run(
            task_summary="restart recovery",
            scenario="synthetic_research",
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
            run_id="run-task-21-recovery",
        )
        run.update_status(RunStatus.RUNNING)
        runtime.sqlite_store.create_run(run)

        restarted_supervisor = RunSupervisor(RunSupervisorConfig(loop_poll_interval_sec=0.01))
        restarted_client = TestClient(build_control_plane_app(restarted_supervisor))

        recovered = restarted_client.get(f"/runs/{run.run_id}")
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(recovered.json()["status"], "PAUSED")

        resume_response = restarted_client.post(f"/runs/{run.run_id}/resume", json={})
        self.assertEqual(resume_response.status_code, 200)
        self.assertTrue(restarted_supervisor.wait_for_idle(run.run_id, timeout_sec=3.0))
        resumed = restarted_client.get(f"/runs/{run.run_id}")
        self.assertEqual(resumed.json()["status"], "COMPLETED")

    def test_events_artifacts_branches_scenarios_and_health_endpoints(self) -> None:
        create_response = self.client.post(
            "/runs",
            json={
                "scenario": "synthetic_research",
                "task_summary": "inspect endpoints",
                "entry_input": {"reference_topics": ["llm", "eval"]},
                "stop_conditions": {"max_loops": 1, "max_duration_sec": 60},
            },
        )
        run_id = create_response.json()["run_id"]
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))

        events_response = self.client.get(f"/runs/{run_id}/events", params={"limit": 2})
        self.assertEqual(events_response.status_code, 200)
        self.assertEqual(len(events_response.json()["items"]), 2)
        self.assertIsNotNone(events_response.json()["next_cursor"])

        artifacts_response = self.client.get(f"/runs/{run_id}/artifacts")
        self.assertEqual(artifacts_response.status_code, 200)
        artifact_paths = [item["path"] for item in artifacts_response.json()["items"]]
        self.assertTrue(any(path.endswith("research_summary.json") for path in artifact_paths))

        branches_response = self.client.get(f"/runs/{run_id}/branches")
        self.assertEqual(branches_response.status_code, 200)
        self.assertEqual(branches_response.json()["items"][0]["branch_id"], "main")

        scenarios_response = self.client.get("/scenarios")
        self.assertEqual(scenarios_response.status_code, 200)
        scenario_names = [item["scenario_name"] for item in scenarios_response.json()["items"]]
        self.assertIn("data_science", scenario_names)
        self.assertIn("synthetic_research", scenario_names)

        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertIn(health_response.json()["status"], {"ok", "degraded"})
        self.assertIn("sqlite", health_response.json()["checks"])
        self.assertIn("execution_backend", health_response.json()["checks"])

    def test_invalid_lifecycle_transitions_return_structured_invalid_state(self) -> None:
        runtime = build_runtime()
        for run_session in [
            RunSession(
                run_id="run-task-21-completed",
                scenario="synthetic_research",
                status=RunStatus.COMPLETED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                entry_input={"task_summary": "completed"},
            ),
            RunSession(
                run_id="run-task-21-paused",
                scenario="synthetic_research",
                status=RunStatus.PAUSED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                entry_input={"task_summary": "paused"},
            ),
            RunSession(
                run_id="run-task-21-stopped",
                scenario="synthetic_research",
                status=RunStatus.STOPPED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                entry_input={"task_summary": "stopped"},
            ),
        ]:
            runtime.sqlite_store.create_run(run_session)

        invalid_cases = [
            ("run-task-21-completed", "pause"),
            ("run-task-21-completed", "resume"),
            ("run-task-21-completed", "stop"),
            ("run-task-21-paused", "pause"),
            ("run-task-21-stopped", "pause"),
            ("run-task-21-stopped", "resume"),
            ("run-task-21-stopped", "stop"),
        ]
        for run_id, action in invalid_cases:
            with self.subTest(run_id=run_id, action=action):
                response = self.client.post(f"/runs/{run_id}/{action}", json={})
                self.assertEqual(response.status_code, 409)
                payload = response.json()
                self.assertEqual(payload["error"]["code"], "invalid_state")
                self.assertIn(run_id, payload["error"]["message"])

    def test_build_config_snapshot_serializes_stop_conditions_without_to_dict_method(self) -> None:
        """Verify _build_config_snapshot falls back to manual serialization when to_dict() is missing."""
        from app.control_plane import _build_config_snapshot
        from service_contracts import RunCreateRequest, StepOverrideConfig
        
        # Create a RunCreateRequest with StopConditions (which lacks to_dict method)
        request = RunCreateRequest(
            scenario="synthetic_research",
            task_summary="test-snapshot",
            stop_conditions=StopConditions(max_loops=5, max_steps=10, max_duration_sec=3600),
            step_overrides=StepOverrideConfig(),
        )
        
        runtime = build_runtime()
        manifest = runtime.plugin_registry.get_manifest("synthetic_research")
        snapshot = _build_config_snapshot(runtime, request, manifest)
        
        # Verify stop_conditions was serialized correctly via fallback
        self.assertEqual(snapshot["stop_conditions"]["max_loops"], 5)
        self.assertEqual(snapshot["stop_conditions"]["max_steps"], 10)
        self.assertEqual(snapshot["stop_conditions"]["max_duration_sec"], 3600)
        self.assertIn("scenario", snapshot)
        self.assertIn("step_overrides", snapshot)

    def test_invalid_event_pagination_returns_structured_invalid_request(self) -> None:
        create_response = self.client.post(
            "/runs",
            json={
                "scenario": "synthetic_research",
                "task_summary": "inspect bad pagination",
                "stop_conditions": {"max_loops": 1, "max_duration_sec": 60},
            },
        )
        run_id = create_response.json()["run_id"]
        self.assertTrue(self.supervisor.wait_for_idle(run_id, timeout_sec=3.0))

        for params, field_name in [
            ({"cursor": "bad", "limit": "bad"}, "cursor"),
            ({"cursor": "bad", "limit": 2}, "cursor"),
            ({"cursor": "0", "limit": "bad"}, "limit"),
        ]:
            with self.subTest(params=params):
                response = self.client.get(f"/runs/{run_id}/events", params=params)
                self.assertEqual(response.status_code, 400)
                payload = response.json()
                self.assertEqual(payload["error"]["code"], "invalid_request")
                self.assertEqual(payload["error"]["field"], field_name)


if __name__ == "__main__":
    unittest.main()
