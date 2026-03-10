"""Task-18 tests for shared V1 contracts and config snapshot persistence."""

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
from app.runtime import build_runtime
from core.storage import SQLiteMetadataStore, SQLiteStoreConfig
from data_models import RunSession, RunStatus, StopConditions
from service_contracts import RunCreateRequest, ServiceContractError
from tests._llm_test_utils import patch_runtime_llm_provider
from ui.trace_ui import load_scenario_manifests


class Task18V1ContractTests(unittest.TestCase):
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
        self._llm_patch = patch_runtime_llm_provider()
        self._llm_patch.start()

    def tearDown(self) -> None:
        self._llm_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_run_create_request_supports_all_step_override_sections(self) -> None:
        request = RunCreateRequest.from_dict(
            {
                "scenario": "data_science",
                "task_summary": "task-18 contract",
                "max_loops": 2,
                "step_overrides": {
                    "proposal": {"provider": "mock", "model": "p-model", "temperature": 0.2},
                    "coding": {"provider": "mock", "model": "c-model", "max_tokens": 256},
                    "running": {"timeout_sec": 45},
                    "feedback": {"provider": "mock", "model": "f-model", "max_retries": 2},
                },
            }
        )

        self.assertEqual(request.stop_conditions.max_loops, 2)
        self.assertEqual(request.step_overrides.proposal.model, "p-model")
        self.assertEqual(request.step_overrides.coding.max_tokens, 256)
        self.assertEqual(request.step_overrides.running.timeout_sec, 45)
        self.assertEqual(request.step_overrides.feedback.max_retries, 2)

    def test_unknown_step_override_key_returns_structured_contract_error(self) -> None:
        with self.assertRaises(ServiceContractError) as ctx:
            RunCreateRequest.from_dict(
                {
                    "scenario": "data_science",
                    "task_summary": "bad override",
                    "step_overrides": {"planner": {"model": "x"}},
                }
            )

        self.assertEqual(ctx.exception.field, "step_overrides")
        self.assertIn("unsupported step override keys", str(ctx.exception))

    def test_invalid_model_selector_semantics_are_rejected_in_dto_layer(self) -> None:
        invalid_payloads = [
            (
                {
                    "scenario": "data_science",
                    "task_summary": "bad retries",
                    "step_overrides": {"proposal": {"max_retries": -1}},
                },
                "step_overrides.proposal.max_retries",
                "max_retries must be >= 0",
            ),
            (
                {
                    "scenario": "data_science",
                    "task_summary": "bad retries",
                    "step_overrides": {"coding": {"max_retries": -1}},
                },
                "step_overrides.coding.max_retries",
                "max_retries must be >= 0",
            ),
            (
                {
                    "scenario": "data_science",
                    "task_summary": "bad retries",
                    "step_overrides": {"feedback": {"max_retries": -1}},
                },
                "step_overrides.feedback.max_retries",
                "max_retries must be >= 0",
            ),
            (
                {
                    "scenario": "data_science",
                    "task_summary": "bad tokens",
                    "step_overrides": {"coding": {"max_tokens": 0}},
                },
                "step_overrides.coding.max_tokens",
                "max_tokens must be > 0",
            ),
        ]

        for payload, field_name, message in invalid_payloads:
            with self.subTest(field=field_name):
                with self.assertRaises(ServiceContractError) as ctx:
                    RunCreateRequest.from_dict(payload)
                self.assertEqual(ctx.exception.field, field_name)
                self.assertIn(message, str(ctx.exception))

    def test_run_session_config_snapshot_persists_in_sqlite_store(self) -> None:
        sqlite_path = Path(os.environ["AGENTRD_SQLITE_PATH"])
        store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(sqlite_path)))
        run = RunSession(
            run_id="run-task-18-config",
            scenario="data_science",
            status=RunStatus.CREATED,
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
            config_snapshot={
                "runtime": {"sandbox_timeout_sec": 300},
                "step_overrides": {"running": {"timeout_sec": 10}},
            },
        )

        store.create_run(run)
        restored = store.get_run(run.run_id)

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.config_snapshot["runtime"]["sandbox_timeout_sec"], 300)
        self.assertEqual(restored.config_snapshot["step_overrides"]["running"]["timeout_sec"], 10)

    def test_cli_run_persists_config_snapshot_and_structured_manifest(self) -> None:
        code, out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                json.dumps(
                    {
                        "task_summary": "task-18 cli run",
                        "data_source": "/tmp/input.csv",
                        "step_overrides": {
                            "running": {"timeout_sec": 12},
                            "proposal": {"provider": "mock", "model": "proposal-v1"},
                        },
                    }
                ),
            ]
        )

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        run_id = payload["run_id"]
        runtime = build_runtime()
        restored = runtime.sqlite_store.get_run(run_id)

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.config_snapshot["step_overrides"]["running"]["timeout_sec"], 12)
        self.assertEqual(restored.config_snapshot["scenario_manifest"]["scenario_name"], "data_science")
        self.assertEqual(restored.entry_input["data_source"], "/tmp/input.csv")

    def test_cli_and_ui_share_same_scenario_manifests(self) -> None:
        runtime = build_runtime()
        registry_payload = [manifest.to_dict() for manifest in runtime.plugin_registry.list_manifests()]
        ui_payload = [manifest.to_dict() for manifest in load_scenario_manifests()]

        code, out, err = self._run_cli(["health-check", "--verbose"])

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        health_payload = json.loads(out)

        self.assertEqual(
            sorted(item["scenario_name"] for item in registry_payload),
            sorted(item["scenario_name"] for item in ui_payload),
        )
        self.assertEqual(
            sorted(item["scenario_name"] for item in registry_payload),
            sorted(item["scenario_name"] for item in health_payload["details"]["scenario_manifests"]),
        )

    def test_invalid_run_request_returns_structured_error_payload(self) -> None:
        code, _out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                '{"task_summary":"broken","entry_input":[]}',
            ]
        )

        self.assertEqual(code, int(ExitCode.INVALID_ARGS))
        payload = json.loads(err)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertEqual(payload["error"]["field"], "entry_input")
        self.assertIn("entry_input must be an object", payload["error"]["message"])

    def test_invalid_timeout_override_returns_structured_error_payload(self) -> None:
        code, _out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                '{"task_summary":"broken","step_overrides":{"running":{"timeout_sec":-1}}}',
            ]
        )

        self.assertEqual(code, int(ExitCode.INVALID_ARGS))
        payload = json.loads(err)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertEqual(payload["error"]["field"], "step_overrides.running.timeout_sec")
        self.assertIn("timeout_sec must be > 0", payload["error"]["message"])

    def test_unsupported_scenario_returns_stable_error_code(self) -> None:
        code, _out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "unknown_scenario",
                "--input",
                '{"task_summary":"broken"}',
            ]
        )

        self.assertEqual(code, int(ExitCode.INVALID_ARGS))
        payload = json.loads(err)
        self.assertEqual(payload["error"]["code"], "unsupported_scenario")
        self.assertEqual(payload["error"]["field"], "scenario")


if __name__ == "__main__":
    unittest.main()
