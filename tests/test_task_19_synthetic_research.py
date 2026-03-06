"""Task-19 tests for the formal synthetic_research scenario."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agentrd_cli import ExitCode, main
from app.runtime import build_run_service, build_runtime
from data_models import StopConditions
from plugins import build_default_registry


class SyntheticResearchScenarioTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_default_registry_exposes_formal_synthetic_research_scenario(self) -> None:
        registry = build_default_registry()

        self.assertIn("data_science", registry.list_scenarios())
        self.assertIn("synthetic_research", registry.list_scenarios())
        self.assertNotIn("data_science_minimal", registry.list_scenarios())

        bundle = registry.create_bundle("synthetic_research")
        manifest = registry.get_manifest("synthetic_research")

        self.assertEqual(bundle.scenario_name, "synthetic_research")
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.scenario_name, "synthetic_research")

    def test_synthetic_research_runs_through_shared_loop_engine(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "synthetic_research")
        run = run_service.create_run(
            task_summary="synth scenario",
            scenario="synthetic_research",
            run_id="run-task-19-runtime",
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
        )

        context = run_service.start_run(
            run_id=run.run_id,
            task_summary="synth scenario",
            loops_per_call=1,
        )

        self.assertEqual(context.run_session.scenario, "synthetic_research")
        self.assertEqual(context.run_session.status.value, "COMPLETED")
        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        self.assertGreaterEqual(len(events), 6)
        summary_path = (
            Path(os.environ["AGENTRD_WORKSPACE_ROOT"])
            / run.run_id
            / "loop-0000"
            / "research_summary.json"
        )
        self.assertTrue(summary_path.exists())

    def test_cli_run_supports_synthetic_research(self) -> None:
        code, out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "synthetic_research",
                "--input",
                '{"task_summary":"synthetic cli","reference_topics":["llm","benchmark"],"max_loops":1}',
            ]
        )

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload["scenario"], "synthetic_research")
        self.assertEqual(payload["run"]["scenario"], "synthetic_research")
        self.assertEqual(payload["run"]["config_snapshot"]["scenario_manifest"]["scenario_name"], "synthetic_research")
        artifact_paths = [item["path"] for item in payload["artifacts_page"]["items"]]
        self.assertTrue(any(path.endswith("research_summary.json") for path in artifact_paths))

    def test_health_check_lists_synthetic_research_manifest(self) -> None:
        code, out, err = self._run_cli(["health-check", "--verbose"])

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        manifests = payload["details"]["scenario_manifests"]

        self.assertIn("synthetic_research", payload["details"]["registered_scenarios"])
        self.assertTrue(any(item["scenario_name"] == "synthetic_research" for item in manifests))
        self.assertFalse(any(item["scenario_name"] == "data_science_minimal" for item in manifests))


if __name__ == "__main__":
    unittest.main()
