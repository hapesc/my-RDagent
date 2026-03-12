"""Task-14 tests for CLI wiring to run service and trace/artifacts query."""

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
from tests._llm_test_utils import patch_runtime_llm_provider


class CLIIntegrationTests(unittest.TestCase):
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
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "120",
                "RD_AGENT_LLM_PROVIDER": "mock",
                "RD_AGENT_LAYER0_N_CANDIDATES": "1",
                "RD_AGENT_LAYER0_K_FORWARD": "1",
                "RD_AGENT_COSTEER_MAX_ROUNDS": "1",
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

    def test_run_trace_pause_resume_stop_health_check_flow(self) -> None:
        code_run, out_run, _ = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--loops-per-call",
                "1",
                "--max-loops",
                "3",
                "--input",
                '{"task_summary":"task-14 flow","max_loops":3}',
            ]
        )
        self.assertEqual(code_run, int(ExitCode.OK))
        run_payload = json.loads(out_run)
        run_id = run_payload["run_id"]
        self.assertEqual(run_payload["command"], "run")

        code_trace, out_trace, _ = self._run_cli(["trace", "--run-id", run_id, "--format", "json"])
        self.assertEqual(code_trace, int(ExitCode.OK))
        trace_payload = json.loads(out_trace)
        self.assertEqual(trace_payload["command"], "trace")
        self.assertIn("events", trace_payload)
        self.assertIn("artifacts", trace_payload)

        code_pause, out_pause, _ = self._run_cli(["pause", "--run-id", run_id])
        self.assertEqual(code_pause, int(ExitCode.OK))
        self.assertEqual(json.loads(out_pause)["status"], "PAUSED")

        code_resume, out_resume, _ = self._run_cli(["resume", "--run-id", run_id, "--loops-per-call", "1"])
        self.assertEqual(code_resume, int(ExitCode.OK))
        self.assertEqual(json.loads(out_resume)["command"], "resume")

        code_stop, out_stop, _ = self._run_cli(["stop", "--run-id", run_id])
        self.assertEqual(code_stop, int(ExitCode.OK))
        self.assertEqual(json.loads(out_stop)["status"], "STOPPED")

        code_health, out_health, _ = self._run_cli(["health-check", "--verbose"])
        self.assertEqual(code_health, int(ExitCode.OK))
        self.assertIn(json.loads(out_health)["status"], {"ok", "degraded"})

    def test_run_fails_closed_without_local_opt_in_when_docker_missing(self) -> None:
        with (
            patch.dict(os.environ, {"AGENTRD_ALLOW_LOCAL_EXECUTION": "0"}, clear=False),
            patch("core.execution.backend.shutil.which", return_value=None),
        ):
            code, _out, err = self._run_cli(
                [
                    "run",
                    "--scenario",
                    "data_science",
                    "--loops-per-call",
                    "1",
                    "--max-loops",
                    "1",
                    "--input",
                    '{"task_summary":"blocked run","max_loops":1}',
                ]
            )

        self.assertEqual(code, int(ExitCode.INVALID_STATE))
        self.assertIn("allow_local_execution=true", err)

    def test_resume_with_fork_branch_creates_branch_nodes(self) -> None:
        code_run, out_run, _ = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--loops-per-call",
                "1",
                "--max-loops",
                "1",
                "--input",
                '{"task_summary":"fork flow","max_loops":1}',
            ]
        )
        self.assertEqual(code_run, int(ExitCode.OK))
        run_id = json.loads(out_run)["run_id"]

        runtime = build_runtime()
        main_head = runtime.branch_store.get_branch_heads(run_id)["main"]

        code_resume, out_resume, _ = self._run_cli(
            [
                "resume",
                "--run-id",
                run_id,
                "--fork-branch",
                "--parent-node-id",
                main_head,
                "--loops-per-call",
                "1",
            ]
        )
        self.assertEqual(code_resume, int(ExitCode.OK))
        resume_payload = json.loads(out_resume)
        fork_branch_id = resume_payload["branch_id"]
        self.assertNotEqual(fork_branch_id, "main")

        code_trace, out_trace, _ = self._run_cli(
            ["trace", "--run-id", run_id, "--branch-id", fork_branch_id, "--format", "json"]
        )
        self.assertEqual(code_trace, int(ExitCode.OK))
        trace_payload = json.loads(out_trace)
        self.assertIn(fork_branch_id, trace_payload["branch_heads"])
        self.assertEqual(len(trace_payload["nodes"]), 1)
        self.assertEqual(trace_payload["nodes"][0]["parent_node_id"], main_head)

    def test_quant_run_accepts_local_ohlcv_file_via_data_source(self) -> None:
        csv_path = Path(self._tmpdir.name) / "ohlcv.csv"
        lines = ["date,stock_id,open,high,low,close,volume"]
        base_dates = [f"2021-06-{day:02d}" for day in range(21, 31)] + [f"2021-07-{day:02d}" for day in range(1, 16)]
        for date_index, trade_date in enumerate(base_dates):
            for stock_index in range(12):
                stock_id = f"STOCK_{stock_index:03d}"
                base_price = 100 + stock_index * 3 + date_index * 0.8
                open_price = base_price
                high_price = base_price + 1.5
                low_price = base_price - 1.5
                close_price = base_price + ((stock_index % 3) - 1) * 0.4
                volume = 1000000 + stock_index * 10000 + date_index * 1000
                lines.append(
                    f"{trade_date},{stock_id},{open_price:.2f},{high_price:.2f},{low_price:.2f},{close_price:.2f},{volume}"
                )
        csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        code, out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "quant",
                "--task-summary",
                "mine a momentum factor from local OHLCV data",
                "--data-source",
                str(csv_path),
            ]
        )

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload["scenario"], "quant")
        self.assertEqual(payload["run"]["scenario"], "quant")


if __name__ == "__main__":
    unittest.main()
