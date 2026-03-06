"""Task-08 tests for docker-first execution backend semantics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.execution import DockerExecutionBackend, DockerExecutionBackendConfig, ExecutionStatus
from trace_store import TraceStore, TraceStoreConfig


class ExecutionBackendTests(unittest.TestCase):
    def _backend(self, trace_path: str) -> DockerExecutionBackend:
        return DockerExecutionBackend(
            DockerExecutionBackendConfig(
                prefer_docker=False,
                default_timeout_sec=5,
                trace_storage_path=trace_path,
            )
        )

    def test_success_collects_artifacts_and_writes_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(trace_path)
            result = backend.execute(
                run_id="run-1",
                branch_id="main",
                loop_index=0,
                workspace_path=str(workspace),
                command="python3 -c \"from pathlib import Path; print('ok'); Path('out.txt').write_text('artifact', encoding='utf-8')\"",
            )

            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any(path.endswith("out.txt") for path in result.artifact_paths))

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["status"], "SUCCESS")

    def test_failure_writes_failure_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(trace_path)
            result = backend.execute(
                run_id="run-2",
                branch_id="main",
                loop_index=0,
                workspace_path=str(workspace),
                command="python3 -c \"import sys; print('bad'); sys.exit(7)\"",
            )

            self.assertEqual(result.status, ExecutionStatus.FAILED)
            self.assertEqual(result.exit_code, 7)

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-2")
            self.assertEqual(events[0].payload["status"], "FAILED")

    def test_timeout_is_terminated_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(trace_path)
            result = backend.execute(
                run_id="run-3",
                branch_id="main",
                loop_index=0,
                workspace_path=str(workspace),
                command="python3 -c \"import time; time.sleep(2)\"",
                timeout_sec=1,
            )

            self.assertEqual(result.status, ExecutionStatus.TIMEOUT)
            self.assertTrue(result.timed_out)

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-3")
            self.assertEqual(events[0].payload["status"], "TIMEOUT")
            self.assertTrue(events[0].payload["timed_out"])


if __name__ == "__main__":
    unittest.main()
