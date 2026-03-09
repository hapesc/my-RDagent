from __future__ import annotations

import importlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app import fastapi_compat
from app.fastapi_compat import FASTAPI_AVAILABLE, HTTPException, Query, TestClient as CompatTestClient
from app.query_services import load_artifact_page, load_branch_page, load_event_page, load_run_summary
from app.run_supervisor import RunSupervisor, RunSupervisorConfig
from app.runtime import build_runtime
from data_models import RunSession, RunStatus, StopConditions

from tests._llm_test_utils import patch_runtime_llm_provider


class AppSmokeTests(unittest.TestCase):
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
                "RD_AGENT_LLM_PROVIDER": "mock",
            },
            clear=False,
        )
        self._env_patch.start()
        self._llm_patch = patch_runtime_llm_provider()
        self._llm_patch.start()

    def tearDown(self) -> None:
        self._llm_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_api_main_import_exposes_live_control_plane_app(self) -> None:
        api_main = importlib.import_module("app.api_main")
        api_main = importlib.reload(api_main)

        client = CompatTestClient(api_main.app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"ok", "degraded"})
        self.assertEqual(payload["checks"]["artifact_root"], "ok")
        self.assertIn("data_science", payload["details"]["registered_scenarios"])
        self.assertIn("synthetic_research", payload["details"]["registered_scenarios"])

    def test_startup_main_prints_config_snapshot(self) -> None:
        startup = importlib.import_module("app.startup")
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = startup.main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["sqlite_path"], os.environ["AGENTRD_SQLITE_PATH"])
        self.assertEqual(payload["artifact_root"], os.environ["AGENTRD_ARTIFACT_ROOT"])
        self.assertEqual(payload["workspace_root"], os.environ["AGENTRD_WORKSPACE_ROOT"])

    def test_run_supervisor_recovers_running_runs_on_init(self) -> None:
        runtime = build_runtime()
        run_session = RunSession(
            run_id="run-app-smoke-recovery",
            scenario="synthetic_research",
            status=RunStatus.RUNNING,
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
            entry_input={"task_summary": "recover me"},
        )
        runtime.sqlite_store.create_run(run_session)

        RunSupervisor(RunSupervisorConfig(loop_poll_interval_sec=0.01))

        recovered = build_runtime().sqlite_store.get_run(run_session.run_id)
        self.assertIsNotNone(recovered)
        assert recovered is not None
        self.assertEqual(recovered.status, RunStatus.PAUSED)
        self.assertTrue(recovered.entry_input["recovery_required"])

    def test_query_services_survive_empty_state_and_missing_roots(self) -> None:
        sqlite_path = os.environ["AGENTRD_SQLITE_PATH"]
        workspace_root = os.environ["AGENTRD_WORKSPACE_ROOT"]
        artifact_root = os.environ["AGENTRD_ARTIFACT_ROOT"]

        self.assertIsNone(load_run_summary(sqlite_path, "missing-run"))

        event_page = load_event_page(sqlite_path, "missing-run", cursor=None, limit=5)
        branch_page = load_branch_page(sqlite_path, "missing-run")
        artifact_page = load_artifact_page(
            sqlite_path,
            workspace_root,
            artifact_root,
            "missing-run",
            branch_id="main",
        )

        self.assertEqual(event_page.run_id, "missing-run")
        self.assertEqual(event_page.items, [])
        self.assertIsNone(event_page.next_cursor)
        self.assertEqual(branch_page.items, [])
        self.assertEqual(artifact_page.items, [])

    def test_fastapi_compat_exports_work_in_current_environment(self) -> None:
        self.assertIs(fastapi_compat.FASTAPI_AVAILABLE, FASTAPI_AVAILABLE)

        if FASTAPI_AVAILABLE:
            self.assertTrue(callable(fastapi_compat.FastAPI))
            self.assertTrue(callable(HTTPException))
            self.assertTrue(callable(Query))
            return

        app = fastapi_compat.FastAPI(title="compat-smoke")

        @app.get("/items/{item_id}")
        def get_item(item_id: str, limit: int = Query(default=2)):
            return {"item_id": item_id, "limit": int(limit)}

        @app.post("/boom")
        def boom() -> None:
            raise HTTPException(status_code=409, detail={"error": "boom"})

        client = CompatTestClient(app)
        ok_response = client.get("/items/abc", params={"limit": "3"})
        error_response = client.post("/boom", json={})

        self.assertEqual(ok_response.status_code, 200)
        self.assertEqual(ok_response.json(), {"item_id": "abc", "limit": 3})
        self.assertEqual(error_response.status_code, 409)
        self.assertEqual(error_response.json(), {"error": "boom"})


if __name__ == "__main__":
    unittest.main()
