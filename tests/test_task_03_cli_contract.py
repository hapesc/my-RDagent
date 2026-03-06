"""Task-03 tests for CLI contract stability."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from agentrd_cli import ExitCode, build_parser, main


class CLIContractTests(unittest.TestCase):
    def _run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_root_help_lists_all_mvp_commands(self) -> None:
        help_text = build_parser().format_help()
        for command in ["run", "resume", "pause", "stop", "trace", "ui", "health-check"]:
            self.assertIn(command, help_text)

    def test_run_command_accepts_inline_json(self) -> None:
        code, out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--input",
                '{"task_summary":"cli test","max_loops":1}',
            ]
        )
        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload["command"], "run")
        self.assertEqual(payload["scenario"], "data_science")
        self.assertIn("run_id", payload)

    def test_invalid_input_returns_invalid_args_code(self) -> None:
        code, _out, err = self._run_cli(["run", "--scenario", "data_science", "--input", "not-json"])
        self.assertEqual(code, int(ExitCode.INVALID_ARGS))
        self.assertIn("--input", err)

    def test_resume_trace_health_check_commands(self) -> None:
        code_run, out_run, _ = self._run_cli(
            [
                "run",
                "--scenario",
                "data_science",
                "--loops-per-call",
                "1",
                "--max-loops",
                "2",
                "--input",
                '{"task_summary":"resume test","max_loops":2}',
            ]
        )
        run_id = json.loads(out_run)["run_id"]

        code_pause, out_pause, _ = self._run_cli(["pause", "--run-id", run_id])
        code_resume, out_resume, _ = self._run_cli(["resume", "--run-id", run_id, "--loops-per-call", "1"])
        code_trace, out_trace, _ = self._run_cli(["trace", "--run-id", run_id, "--format", "json"])
        code_health, out_health, _ = self._run_cli(["health-check", "--verbose"])

        self.assertEqual(code_run, int(ExitCode.OK))
        self.assertEqual(code_pause, int(ExitCode.OK))
        self.assertEqual(code_resume, int(ExitCode.OK))
        self.assertEqual(code_trace, int(ExitCode.OK))
        self.assertEqual(code_health, int(ExitCode.OK))

        self.assertEqual(json.loads(out_pause)["command"], "pause")
        self.assertEqual(json.loads(out_resume)["command"], "resume")
        self.assertEqual(json.loads(out_trace)["command"], "trace")
        self.assertIn(json.loads(out_health)["status"], {"ok", "degraded"})

    def test_help_exits_zero(self) -> None:
        code, _out, _err = self._run_cli(["--help"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
