"""Service scaffold for the Execution Service module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from data_models import CodeArtifact, ExecutionResult


@dataclass
class ExecutionServiceConfig:
    """Configuration for sandbox execution limits."""

    sandbox_profile: str = "default"
    max_runtime_seconds: int = 0


class ExecutionService:
    """Runs artifacts in a controlled sandbox and collects runtime outputs."""

    def __init__(self, config: ExecutionServiceConfig) -> None:
        """Initialize execution service with sandbox settings."""

        self._config = config

    def execute_artifact(self, artifact: CodeArtifact) -> ExecutionResult:
        """Execute a runnable artifact in a sandbox.

        Responsibility:
            Produce execution result placeholders without running code.
        Input semantics:
            - artifact: CodeArtifact reference
        Output semantics:
            ExecutionResult with placeholder exit code and references.
        Architecture mapping:
            Execution Service -> execute_artifact
        """

        _ = artifact
        return ExecutionResult(
            run_id="run-placeholder",
            exit_code=0,
            logs_ref="logs-placeholder",
            artifacts_ref="outputs-placeholder",
        )

    def stream_logs(self, run_id: str) -> List[str]:
        """Stream logs for a running execution.

        Responsibility:
            Provide log lines for a given run ID.
        Input semantics:
            - run_id: Execution run identifier
        Output semantics:
            List of log lines.
        Architecture mapping:
            Execution Service -> stream_logs
        """

        _ = run_id
        return []

    def terminate_run(self, run_id: str) -> bool:
        """Terminate a running execution.

        Responsibility:
            Acknowledge termination of a sandbox run.
        Input semantics:
            - run_id: Execution run identifier
        Output semantics:
            Boolean indicating termination acknowledgment.
        Architecture mapping:
            Execution Service -> terminate_run
        """

        _ = run_id
        return True
