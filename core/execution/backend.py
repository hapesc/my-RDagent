"""Execution backend abstraction with Docker-first implementation."""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from data_models import (
    ArtifactVerificationStatus,
    Event,
    EventType,
    ExecutionOutcomeContract,
    ProcessExecutionStatus,
    UsefulnessEligibilityStatus,
)
from trace_store import TraceStore, TraceStoreConfig


class ExecutionStatus(str, Enum):
    """Normalized execution failure semantics."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class BackendResult:
    """Result produced by execution backend."""

    engine: str
    status: ExecutionStatus
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool
    artifact_paths: List[str] = field(default_factory=list)
    artifact_manifest: Dict[str, Any] = field(default_factory=dict)
    malformed_artifact_paths: List[str] = field(default_factory=list)
    outcome: Optional[ExecutionOutcomeContract] = None


@dataclass
class DockerExecutionBackendConfig:
    """Configuration for docker-first execution backend."""

    docker_image: str = "python:3.11-slim"
    prefer_docker: bool = True
    allow_local_execution: bool = False
    command_shell: str = "/bin/sh"
    default_timeout_sec: int = 300
    trace_storage_path: str = "/tmp/rd_agent_trace/events.jsonl"
    artifact_globs: List[str] = field(
        default_factory=lambda: [
            "*.txt",
            "*.log",
            "*.json",
            "*.csv",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.pkl",
            "*.parquet",
        ]
    )


class ExecutionBackend(Protocol):
    """Execution backend protocol."""

    def execute(
        self,
        run_id: str,
        branch_id: str,
        loop_index: int,
        workspace_path: str,
        command: str,
        timeout_sec: Optional[int] = None,
    ) -> BackendResult:
        ...


class DockerExecutionBackend:
    """Runs commands in Docker when available, with explicit local opt-in."""

    def __init__(self, config: DockerExecutionBackendConfig) -> None:
        self._config = config

    def execute(
        self,
        run_id: str,
        branch_id: str,
        loop_index: int,
        workspace_path: str,
        command: str,
        timeout_sec: Optional[int] = None,
    ) -> BackendResult:
        timeout = timeout_sec if timeout_sec is not None else self._config.default_timeout_sec
        workspace = Path(workspace_path).resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        docker_available = shutil.which("docker") is not None
        use_docker = self._config.prefer_docker and docker_available
        use_local = not use_docker and self._config.allow_local_execution

        if not use_docker and not use_local:
            message = self._blocked_execution_message(docker_available)
            result = BackendResult(
                engine="blocked",
                status=ExecutionStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=message,
                duration_sec=0.0,
                timed_out=False,
                artifact_paths=[],
                artifact_manifest={"paths": []},
                malformed_artifact_paths=[],
                outcome=ExecutionOutcomeContract(
                    process_status=ProcessExecutionStatus.ERROR,
                    artifact_status=ArtifactVerificationStatus.MISSING_REQUIRED,
                    usefulness_status=UsefulnessEligibilityStatus.INELIGIBLE,
                ),
            )
            self._record_execution_event(
                run_id=run_id,
                branch_id=branch_id,
                loop_index=loop_index,
                result=result,
                docker_available=docker_available,
                timeout_sec=timeout,
            )
            raise RuntimeError(message)

        engine = "docker" if use_docker else "local"
        cmd = self._build_docker_command(workspace, command) if use_docker else self._build_local_command(command)

        started = time.monotonic()
        status, exit_code, stdout, stderr, timed_out = self._run_command(
            cmd,
            cwd=None if use_docker else str(workspace),
            timeout=timeout,
        )

        if self._should_fallback_to_local(
            used_docker=use_docker,
            status=status,
            exit_code=exit_code,
            stderr=stderr,
        ):
            engine = "local"
            status, exit_code, stdout, stderr, timed_out = self._run_command(
                self._build_local_command(command),
                cwd=str(workspace),
                timeout=timeout,
            )

        duration = time.monotonic() - started
        artifact_paths = self._collect_artifacts(workspace)
        malformed_artifact_paths = self._collect_malformed_artifact_paths(artifact_paths)
        process_status = self._to_process_status(status)
        if len(malformed_artifact_paths) > 0:
            artifact_status = ArtifactVerificationStatus.MALFORMED_REQUIRED
        elif len(artifact_paths) > 0:
            artifact_status = ArtifactVerificationStatus.VERIFIED
        else:
            artifact_status = ArtifactVerificationStatus.MISSING_REQUIRED
        usefulness_status = (
            UsefulnessEligibilityStatus.ELIGIBLE
            if process_status == ProcessExecutionStatus.SUCCESS
            and artifact_status == ArtifactVerificationStatus.VERIFIED
            else UsefulnessEligibilityStatus.INELIGIBLE
        )
        artifact_manifest = {
            "paths": artifact_paths,
            "required_globs": list(self._config.artifact_globs),
            "malformed_paths": malformed_artifact_paths,
        }
        result = BackendResult(
            engine=engine,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_sec=duration,
            timed_out=timed_out,
            artifact_paths=artifact_paths,
            artifact_manifest=artifact_manifest,
            malformed_artifact_paths=malformed_artifact_paths,
            outcome=ExecutionOutcomeContract(
                process_status=process_status,
                artifact_status=artifact_status,
                usefulness_status=usefulness_status,
            ),
        )
        self._record_execution_event(
            run_id=run_id,
            branch_id=branch_id,
            loop_index=loop_index,
            result=result,
            docker_available=docker_available,
            timeout_sec=timeout,
        )
        return result

    def _blocked_execution_message(self, docker_available: bool) -> str:
        if self._config.prefer_docker and not docker_available:
            return "docker is unavailable and local execution is disabled; set allow_local_execution=true to opt in"
        return "no permitted execution backend available; enable docker execution or set allow_local_execution=true"

    def _build_docker_command(self, workspace: Path, command: str) -> List[str]:
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "-w",
            "/workspace",
            self._config.docker_image,
            self._config.command_shell,
            "-lc",
            command,
        ]

    def _build_local_command(self, command: str) -> List[str]:
        return [self._config.command_shell, "-lc", command]

    def _run_command(
        self,
        cmd: List[str],
        *,
        cwd: Optional[str],
        timeout: int,
    ) -> tuple[ExecutionStatus, int, str, str, bool]:
        timed_out = False
        status = ExecutionStatus.ERROR
        exit_code = -1
        stdout = ""
        stderr = ""
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = int(process.returncode)
                status = ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                status = ExecutionStatus.TIMEOUT
        except Exception as exc:
            stderr = str(exc)
            status = ExecutionStatus.ERROR
            exit_code = -1
        return status, exit_code, stdout, stderr, timed_out

    def _should_fallback_to_local(
        self,
        *,
        used_docker: bool,
        status: ExecutionStatus,
        exit_code: int,
        stderr: str,
    ) -> bool:
        if not used_docker or not self._config.allow_local_execution:
            return False
        if status not in {ExecutionStatus.FAILED, ExecutionStatus.ERROR}:
            return False

        stderr_lower = (stderr or "").lower()
        daemon_unavailable = any(
            marker in stderr_lower
            for marker in (
                "cannot connect to the docker daemon",
                "is the docker daemon running",
                "error during connect",
                "docker daemon",
            )
        )
        return daemon_unavailable or exit_code in {-1, 125}

    def _collect_artifacts(self, workspace: Path) -> List[str]:
        paths = set()
        for pattern in self._config.artifact_globs:
            for path in workspace.rglob(pattern):
                if path.is_file():
                    paths.add(str(path))
        return sorted(paths)

    def _collect_malformed_artifact_paths(self, artifact_paths: List[str]) -> List[str]:
        malformed_paths: List[str] = []
        for path_str in artifact_paths:
            normalized = path_str.strip()
            if not normalized:
                malformed_paths.append(path_str)
                continue
            try:
                path_obj = Path(normalized)
            except Exception:
                malformed_paths.append(path_str)
                continue
            if not path_obj.exists() or not path_obj.is_file():
                malformed_paths.append(path_str)
        return malformed_paths

    def _record_execution_event(
        self,
        run_id: str,
        branch_id: str,
        loop_index: int,
        result: BackendResult,
        docker_available: bool,
        timeout_sec: int,
    ) -> None:
        trace_store = TraceStore(TraceStoreConfig(storage_path=self._config.trace_storage_path))
        trace_store.append_event(
            Event(
                event_id=f"event-{uuid.uuid4().hex}",
                run_id=run_id,
                branch_id=branch_id,
                loop_index=loop_index,
                step_name="execution",
                event_type=EventType.EXECUTION_FINISHED,
                payload={
                    "engine": result.engine,
                    "status": result.status.value,
                    "exit_code": result.exit_code,
                    "timed_out": result.timed_out,
                    "timeout_sec": timeout_sec,
                    "artifact_count": len(result.artifact_paths),
                    "artifact_manifest": result.artifact_manifest,
                    "malformed_artifact_paths": list(result.malformed_artifact_paths),
                    "docker_available": docker_available,
                    "allow_local_execution": self._config.allow_local_execution,
                    "stderr": result.stderr,
                    "process_status": result.outcome.process_status.value if result.outcome else None,
                    "artifact_status": result.outcome.artifact_status.value if result.outcome else None,
                    "usefulness_status": result.outcome.usefulness_status.value if result.outcome else None,
                },
            )
        )

    def _to_process_status(self, status: ExecutionStatus) -> ProcessExecutionStatus:
        if status == ExecutionStatus.SUCCESS:
            return ProcessExecutionStatus.SUCCESS
        if status == ExecutionStatus.FAILED:
            return ProcessExecutionStatus.FAILED
        if status == ExecutionStatus.TIMEOUT:
            return ProcessExecutionStatus.TIMEOUT
        return ProcessExecutionStatus.ERROR
