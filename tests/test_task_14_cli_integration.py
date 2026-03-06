"""Task-14 tests for CLI wiring to run service and trace/artifacts query."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from agentrd_cli import ExitCode, main


class CLIIntegrationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
