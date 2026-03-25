"""Boundary for loading public recovery inputs without checkpoint leakage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rd_agent.contracts.artifact import ArtifactSnapshot
from rd_agent.contracts.branch import BranchSnapshot
from rd_agent.contracts.stage import StageKey, StageSnapshot


@dataclass(frozen=True)
class RecoveryInputs:
    """State-first inputs used to assess whether a branch-stage can be reused."""

    branch: BranchSnapshot
    stage: StageSnapshot
    artifacts: list[ArtifactSnapshot] = field(default_factory=list)


class RecoveryPort(Protocol):
    """Port for loading recovery inputs from V3-owned state or translated history."""

    def load_recovery_inputs(self, branch_id: str, stage_key: StageKey) -> RecoveryInputs | None: ...
