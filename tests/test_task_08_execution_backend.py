"""Task-08 tests for docker-first execution backend semantics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.execution import DockerExecutionBackend, DockerExecutionBackendConfig, ExecutionStatus
from data_models import ArtifactVerificationStatus, ProcessExecutionStatus, UsefulnessEligibilityStatus
from trace_store import TraceStore, TraceStoreConfig


class ExecutionBackendTests(unittest.TestCase):
    def _backend(
        self,
        trace_path: str,
        *,
        prefer_docker: bool = False,
        allow_local_execution: bool = True,
    ) -> DockerExecutionBackend:
        return DockerExecutionBackend(
            DockerExecutionBackendConfig(
                prefer_docker=prefer_docker,
                allow_local_execution=allow_local_execution,
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
                command=(
                    "python3 -c \"from pathlib import Path; print('ok'); "
                    "Path('out.txt').write_text('artifact', encoding='utf-8')\""
                ),
            )

            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(any(path.endswith("out.txt") for path in result.artifact_paths))
            if result.outcome is None:
                self.fail("expected canonical outcome contract")
            self.assertEqual(result.outcome.process_status, ProcessExecutionStatus.SUCCESS)
            self.assertEqual(result.outcome.artifact_status, ArtifactVerificationStatus.VERIFIED)
            self.assertEqual(result.outcome.usefulness_status, UsefulnessEligibilityStatus.ELIGIBLE)
            self.assertIn("paths", result.artifact_manifest)
            self.assertTrue(any(path.endswith("out.txt") for path in result.artifact_manifest["paths"]))

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-1")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["status"], "SUCCESS")
            self.assertEqual(events[0].payload["usefulness_status"], "ELIGIBLE")
            self.assertIn("artifact_manifest", events[0].payload)

    def test_exit_zero_without_artifacts_is_semantically_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(trace_path)
            result = backend.execute(
                run_id="run-1b",
                branch_id="main",
                loop_index=0,
                workspace_path=str(workspace),
                command="python3 -c \"print('ok-no-artifacts')\"",
            )

            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertEqual(result.exit_code, 0)
            if result.outcome is None:
                self.fail("expected canonical outcome contract")
            self.assertEqual(result.outcome.process_status, ProcessExecutionStatus.SUCCESS)
            self.assertEqual(result.outcome.artifact_status, ArtifactVerificationStatus.MISSING_REQUIRED)
            self.assertEqual(result.outcome.usefulness_status, UsefulnessEligibilityStatus.INELIGIBLE)

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-1b")
            self.assertEqual(events[0].payload["status"], "SUCCESS")
            self.assertEqual(events[0].payload["usefulness_status"], "INELIGIBLE")

    def test_malformed_artifact_paths_fail_semantic_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(trace_path)
            with patch.object(
                backend,
                "_collect_artifacts",
                return_value=[""],
            ):
                result = backend.execute(
                    run_id="run-1c",
                    branch_id="main",
                    loop_index=0,
                    workspace_path=str(workspace),
                    command="python3 -c \"print('ok')\"",
                )

            if result.outcome is None:
                self.fail("expected canonical outcome contract")
            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertEqual(result.outcome.process_status, ProcessExecutionStatus.SUCCESS)
            self.assertEqual(result.outcome.artifact_status, ArtifactVerificationStatus.MALFORMED_REQUIRED)
            self.assertEqual(result.outcome.usefulness_status, UsefulnessEligibilityStatus.INELIGIBLE)
            self.assertEqual(result.malformed_artifact_paths, [""])

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-1c")
            self.assertEqual(events[0].payload["artifact_status"], "MALFORMED_REQUIRED")
            self.assertEqual(events[0].payload["usefulness_status"], "INELIGIBLE")

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
                command='python3 -c "import time; time.sleep(2)"',
                timeout_sec=1,
            )

            self.assertEqual(result.status, ExecutionStatus.TIMEOUT)
            self.assertTrue(result.timed_out)

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-3")
            self.assertEqual(events[0].payload["status"], "TIMEOUT")
            self.assertTrue(events[0].payload["timed_out"])

    def test_no_docker_without_local_opt_in_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(
                trace_path,
                prefer_docker=True,
                allow_local_execution=False,
            )
            with (
                patch("core.execution.backend.shutil.which", return_value=None),
                self.assertRaisesRegex(RuntimeError, "allow_local_execution=true"),
            ):
                backend.execute(
                    run_id="run-4",
                    branch_id="main",
                    loop_index=0,
                    workspace_path=str(workspace),
                    command="python3 -c \"print('blocked')\"",
                )

            events = TraceStore(TraceStoreConfig(storage_path=trace_path)).query_events(run_id="run-4")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["status"], "ERROR")
            self.assertFalse(events[0].payload["allow_local_execution"])

    def test_no_docker_with_local_opt_in_runs_locally(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            trace_path = str(Path(tmpdir) / "events.jsonl")

            backend = self._backend(
                trace_path,
                prefer_docker=True,
                allow_local_execution=True,
            )
            with patch("core.execution.backend.shutil.which", return_value=None):
                result = backend.execute(
                    run_id="run-5",
                    branch_id="main",
                    loop_index=0,
                    workspace_path=str(workspace),
                    command=(
                        "python3 -c \"from pathlib import Path; Path('local.txt').write_text('ok', encoding='utf-8')\""
                    ),
                )

            self.assertEqual(result.engine, "local")
            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
            self.assertTrue((workspace / "local.txt").exists())


if __name__ == "__main__":
    unittest.main()
