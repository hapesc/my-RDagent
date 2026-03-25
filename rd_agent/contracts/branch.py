"""V3 branch-first public contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .exploration import BranchResolution
from .stage import StageKey, StageSnapshot


class BranchStatus(StrEnum):
    """Top-level public status for a V3 branch."""

    CANDIDATE = "candidate"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"


class BranchScore(BaseModel):
    """Public branch value projection over private selection logic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exploration_priority: float = Field(ge=0.0)
    result_quality: float = Field(ge=0.0)
    rationale: str = Field(min_length=1)
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class BranchLineage(BaseModel):
    """High-level public relationship summary for a branch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    parent_branch_id: str | None = None
    child_branch_ids: list[str] = Field(default_factory=list)
    source_summary: str | None = None


class BranchSnapshot(BaseModel):
    """First-class public work unit for the V3 runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: BranchStatus
    resolution: BranchResolution | None = None
    current_stage_key: StageKey
    stages: list[StageSnapshot] = Field(default_factory=list)
    score: BranchScore
    lineage: BranchLineage = Field(default_factory=BranchLineage)
    artifact_ids: list[str] = Field(default_factory=list)


__all__ = ["BranchLineage", "BranchScore", "BranchSnapshot", "BranchStatus"]
