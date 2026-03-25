"""Execution handoff boundary for V3-owned run starts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rd_agent.contracts.artifact import ArtifactSnapshot
from rd_agent.contracts.branch import BranchSnapshot
from rd_agent.contracts.stage import StageSnapshot
from rd_agent.contracts.tool_io import RunStartRequest


@dataclass(frozen=True)
class ExecutionStartResult:
    """Minimal execution result needed to publish initial V3 truth."""

    branch: BranchSnapshot
    stage: StageSnapshot
    artifacts: list[ArtifactSnapshot] = field(default_factory=list)


class ExecutionPort(Protocol):
    """Port implemented by whatever engine actually starts work for V3."""

    def start_run(self, request: RunStartRequest) -> ExecutionStartResult: ...
