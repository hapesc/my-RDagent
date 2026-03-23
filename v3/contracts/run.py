"""V3 run-board public contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .exploration import ExplorationMode


class ExecutionMode(StrEnum):
    """Operator-visible autonomy mode for a V3 run."""

    GATED = "gated"
    UNATTENDED = "unattended"


class RunStatus(StrEnum):
    """Top-level public state for the branch board."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    NEEDS_ATTENTION = "needs_attention"


class RunStopReason(StrEnum):
    """Operator-visible stop reason for a bounded V3 run."""

    AWAITING_OPERATOR = "awaiting_operator"
    ITERATION_CEILING_REACHED = "iteration_ceiling_reached"
    STAGE_BLOCKED = "stage_blocked"
    RUN_COMPLETED = "run_completed"


class RunBoardSnapshot(BaseModel):
    """Container summary for branch-first V3 public truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    scenario_label: str | None = None
    status: RunStatus
    current_stage_iteration: int = Field(default=1, ge=1)
    execution_mode: ExecutionMode = ExecutionMode.GATED
    max_stage_iterations: int = Field(default=1, ge=1)
    completed_stage_iterations: int = Field(default=0, ge=0)
    stop_reason: RunStopReason | None = None
    exploration_mode: ExplorationMode | None = None
    primary_branch_id: str | None = None
    branch_ids: list[str] = Field(default_factory=list)
    highlighted_artifact_ids: list[str] = Field(default_factory=list)
    latest_branch_decision_id: str | None = None
    latest_merge_outcome_id: str | None = None
    latest_branch_board_id: str | None = None
    summary: str = Field(min_length=1)
    current_round: int = Field(default=0, ge=0)
    max_rounds: int = Field(default=20, ge=1)


__all__ = ["ExecutionMode", "RunBoardSnapshot", "RunStatus", "RunStopReason"]
