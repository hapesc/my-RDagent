"""Task-20 tests for effective per-step config resolution and auditability."""

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
from planner.service import Planner
from tests._llm_test_utils import patch_runtime_llm_provider
from ui.trace_ui import load_run_summary


class Task20PerStepConfigTests(unittest.TestCase):
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
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "123",
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

    def test_default_step_config_falls_back_to_scenario_defaults_and_is_auditable(self) -> None:
        code_run, out_run, err_run = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                '{"task_summary":"task-20 defaults","max_loops":1}',
            ]
        )

        self.assertEqual(code_run, int(ExitCode.OK))
        self.assertEqual(err_run, "")
        run_payload = json.loads(out_run)
        run_id = run_payload["run_id"]
        step_config = run_payload["run"]["config_snapshot"]["step_overrides"]
        self.assertEqual(step_config["proposal"]["model"], "ds-proposal-default")
        self.assertEqual(step_config["coding"]["model"], "ds-coding-default")
        self.assertEqual(step_config["feedback"]["model"], "ds-feedback-default")
        # The config_snapshot reflects the effective running timeout after resolution.
        # With default planner, this will be the plan-allocated timeout (typically 75s from 300s/4 steps).
        self.assertIsInstance(step_config["running"]["timeout_sec"], int)
        self.assertGreater(step_config["running"]["timeout_sec"], 0)

        code_trace, out_trace, err_trace = self._run_cli(["trace", "--run-id", run_id, "--format", "json"])
        self.assertEqual(code_trace, int(ExitCode.OK))
        self.assertEqual(err_trace, "")
        trace_payload = json.loads(out_trace)
        trace_timeout = trace_payload["run"]["config_snapshot"]["step_overrides"]["running"]["timeout_sec"]
        self.assertEqual(trace_timeout, step_config["running"]["timeout_sec"])

        run_summary = load_run_summary(os.environ["AGENTRD_SQLITE_PATH"], run_id)
        self.assertIsNotNone(run_summary)
        assert run_summary is not None
        self.assertEqual(run_summary.config_snapshot["step_overrides"]["proposal"]["model"], "ds-proposal-default")

    def test_overrides_are_consumed_by_llm_steps_and_running_timeout(self) -> None:
        code_run, out_run, err_run = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                json.dumps(
                    {
                        "task_summary": "task-20 overrides",
                        "command": "python3 pipeline.py",
                        "max_loops": 1,
                        "step_overrides": {
                            "proposal": {"model": "proposal-override"},
                            "coding": {"model": "coding-override"},
                            "running": {"timeout_sec": 1},
                            "feedback": {"model": "feedback-override"},
                        },
                    }
                ),
            ]
        )

        self.assertEqual(code_run, int(ExitCode.OK))
        self.assertEqual(err_run, "")
        run_payload = json.loads(out_run)
        run_id = run_payload["run_id"]

        code_trace, out_trace, err_trace = self._run_cli(["trace", "--run-id", run_id, "--format", "json"])
        self.assertEqual(code_trace, int(ExitCode.OK))
        self.assertEqual(err_trace, "")
        trace_payload = json.loads(out_trace)

        proposal_event = next(item for item in trace_payload["events"] if item["step_name"] == "proposing")
        coding_event = next(item for item in trace_payload["events"] if item["step_name"] == "coding")
        running_event = next(item for item in trace_payload["events"] if item["step_name"] == "running")
        feedback_event = next(item for item in trace_payload["events"] if item["step_name"] == "feedback")

        self.assertIn("model:proposal-override", proposal_event["payload"]["constraints"])
        self.assertEqual(coding_event["payload"]["model_config"]["model"], "coding-override")
        self.assertEqual(running_event["payload"]["timeout_sec"], 1)
        self.assertIn("model=feedback-override", feedback_event["payload"]["reason"])
        self.assertEqual(trace_payload["run"]["config_snapshot"]["step_overrides"]["running"]["timeout_sec"], 1)
        self.assertEqual(
            trace_payload["run"]["config_snapshot"]["requested_step_overrides"]["proposal"]["model"],
            "proposal-override",
        )

    def test_invalid_step_override_values_fail_fast_as_invalid_request(self) -> None:
        invalid_requests = [
            (
                '{"task_summary":"bad retries","step_overrides":{"proposal":{"max_retries":-1}}}',
                "step_overrides.proposal.max_retries",
                "max_retries must be >= 0",
            ),
            (
                '{"task_summary":"bad timeout","step_overrides":{"running":{"timeout_sec":0}}}',
                "step_overrides.running.timeout_sec",
                "timeout_sec must be > 0",
            ),
        ]

        for raw_input, field_name, message in invalid_requests:
            with self.subTest(field=field_name):
                code, _out, err = self._run_cli(
                    [
                        "run",
                        "--scenario",
                        "data_science",
                        "--input",
                        raw_input,
                    ]
                )
                self.assertEqual(code, int(ExitCode.INVALID_ARGS))
                payload = json.loads(err)
                self.assertEqual(payload["error"]["code"], "invalid_request")
                self.assertEqual(payload["error"]["field"], field_name)
                self.assertIn(message, payload["error"]["message"])

    def test_plan_timeout_reflected_in_config_snapshot(self) -> None:
        """Regression test T6b: Verify config_snapshot reflects plan-applied running timeout.

        When no explicit step_overrides are provided, the planner generates a budget_allocation
        that includes a "running" timeout. This timeout should be reflected in config_snapshot
        after resolution (proving the plan-timeout path works).
        """
        code_run, out_run, err_run = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                '{"task_summary":"task-20 plan-timeout","max_loops":1}',
            ]
        )

        self.assertEqual(code_run, int(ExitCode.OK))
        self.assertEqual(err_run, "")
        run_payload = json.loads(out_run)
        run_id = run_payload["run_id"]
        step_config = run_payload["run"]["config_snapshot"]["step_overrides"]

        # The planner should generate a plan with budget_allocation.
        # Default budget is 600s / 4 steps = 150s per step, but adjusted for actual timing.
        # The key assertion is that the timeout exists and is a positive integer.
        self.assertIsNotNone(step_config["running"]["timeout_sec"])
        self.assertIsInstance(step_config["running"]["timeout_sec"], int)
        self.assertGreater(step_config["running"]["timeout_sec"], 0)

        # Verify via trace API that the snapshot is consistent
        code_trace, out_trace, err_trace = self._run_cli(["trace", "--run-id", run_id, "--format", "json"])
        self.assertEqual(code_trace, int(ExitCode.OK))
        self.assertEqual(err_trace, "")
        trace_payload = json.loads(out_trace)
        snapshot_timeout = trace_payload["run"]["config_snapshot"]["step_overrides"]["running"]["timeout_sec"]
        self.assertEqual(snapshot_timeout, step_config["running"]["timeout_sec"])

    def test_default_timeout_reflected_in_config_snapshot_when_no_plan_timeout(self) -> None:
        """Regression test T6b: Verify config_snapshot reflects default running timeout.

        When no explicit step_overrides are provided and the planner does not provide
        a "running" timeout in budget_allocation, _resolve_step_config() must fall back
        to the default timeout from the plugin's default_step_overrides.

        This test patches the planner to return budget_allocation WITHOUT "running" so the
        fallback path is exercised.
        """

        original_generate_plan = Planner.generate_plan

        def patched_generate_plan(self, *args, **kwargs):
            plan = original_generate_plan(self, *args, **kwargs)
            if plan.budget_allocation is not None and "running" in plan.budget_allocation:
                plan.budget_allocation = {k: v for k, v in plan.budget_allocation.items() if k != "running"}
            return plan

        with patch.object(Planner, "generate_plan", patched_generate_plan):
            code_run, out_run, err_run = self._run_cli(
                [
                    "run",
                    "--scenario",
                    "data_science",
                    "--input",
                    '{"task_summary":"task-20 default-timeout","max_loops":1}',
                ]
            )

        self.assertEqual(code_run, int(ExitCode.OK))
        self.assertEqual(err_run, "")
        run_payload = json.loads(out_run)
        run_id = run_payload["run_id"]
        step_config = run_payload["run"]["config_snapshot"]["step_overrides"]

        self.assertIsNotNone(step_config["running"]["timeout_sec"])
        self.assertIsInstance(step_config["running"]["timeout_sec"], int)
        self.assertGreater(step_config["running"]["timeout_sec"], 0)

        default_timeout = int(os.environ["AGENTRD_SANDBOX_TIMEOUT_SEC"])
        self.assertEqual(step_config["running"]["timeout_sec"], default_timeout)

        run_summary = load_run_summary(os.environ["AGENTRD_SQLITE_PATH"], run_id)
        self.assertIsNotNone(run_summary)
        assert run_summary is not None
        db_timeout = run_summary.config_snapshot["step_overrides"]["running"]["timeout_sec"]
        self.assertEqual(db_timeout, default_timeout)


if __name__ == "__main__":
    unittest.main()
