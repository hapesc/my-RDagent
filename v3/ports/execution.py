"""Execution handoff boundary for V3-owned run starts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from v3.contracts.artifact import ArtifactSnapshot
from v3.contracts.branch import BranchSnapshot
from v3.contracts.stage import StageSnapshot
from v3.contracts.tool_io import RunStartRequest


@dataclass(frozen=True)
class ExecutionStartResult:
    """Minimal execution result needed to publish initial V3 truth."""

    branch: BranchSnapshot
    stage: StageSnapshot
    artifacts: list[ArtifactSnapshot] = field(default_factory=list)


class ExecutionPort(Protocol):
    """Port implemented by whatever engine actually starts work for V3."""

    def start_run(self, request: RunStartRequest) -> ExecutionStartResult: ...
