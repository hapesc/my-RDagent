"""V3-owned contracts for multi-branch exploration state."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .stage import StageKey


class ExplorationMode(StrEnum):
    """Operator-visible multi-branch mode."""

    EXPLORATION = "exploration"
    CONVERGENCE = "convergence"


class BranchResolution(StrEnum):
    """Typed exploration outcome separate from top-level branch status."""

    OPEN = "open"
    PRUNED = "pruned"
    SHORTLISTED = "shortlisted"
    MERGED = "merged"
    REJECTED = "rejected"


class BranchDecisionKind(StrEnum):
    """Recorded branch-management decisions for Phase 16."""

    FORK = "fork"
    SELECT = "select"
    PRUNE = "prune"
    SHARE = "share"
    SHORTLIST = "shortlist"
    MERGE = "merge"


class BranchDecisionRef(BaseModel):
    """Compact pointer to the latest persisted decision for a branch or run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    kind: BranchDecisionKind
    resolution: BranchResolution | None = None


class BranchResolutionRef(BaseModel):
    """Lightweight branch-resolution pointer that preserves the source decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resolution: BranchResolution
    decision_id: str = Field(min_length=1)


class BranchDecisionSnapshot(BaseModel):
    """Persisted explanation artifact for a branch-level exploration decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    kind: BranchDecisionKind
    mode: ExplorationMode
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    resolution: BranchResolution | None = None
    source_branch_id: str | None = None
    affected_branch_ids: list[str] = Field(default_factory=list)


class BranchCardSnapshot(BaseModel):
    """Card-ready branch board row without leaking graph internals."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: str = Field(min_length=1)
    resolution: BranchResolution | None = None
    current_stage_key: StageKey
    explanation: str = Field(min_length=1)
    latest_decision_kind: BranchDecisionKind | None = None
    latest_decision_id: str | None = None
    shared_from_branch_ids: list[str] = Field(default_factory=list)


class BranchBoardSnapshot(BaseModel):
    """Run-scoped read model for active branch cards and history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    board_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    mode: ExplorationMode
    active_cards: list[BranchCardSnapshot] = Field(default_factory=list)
    history_cards: list[BranchCardSnapshot] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class CandidateSummarySnapshot(BaseModel):
    """Typed pre-merge summary over the leading branch set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_ids: list[str] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    hypothesis_evolution: list[str] = Field(default_factory=list)


class ShortlistEntrySnapshot(BaseModel):
    """Ordered shortlist member for merge fallback or operator review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    rationale: str = Field(min_length=1)


class MergeOutcomeSnapshot(BaseModel):
    """Typed summary of a merge attempt or convergence fallback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    mode: ExplorationMode = ExplorationMode.CONVERGENCE
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    merged_branch_id: str | None = None
    source_branch_ids: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    shortlist: list[ShortlistEntrySnapshot] = Field(default_factory=list)


class MergeOutcomeRef(BaseModel):
    """Compact pointer to the latest convergence artifact for a run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_id: str = Field(min_length=1)
    merged_branch_id: str | None = None
    failure_reason: str | None = None


class BranchBoardRef(BaseModel):
    """Pointer to the persisted board read-model currently highlighted for a run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    board_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    mode: ExplorationMode


__all__ = [
    "BranchBoardRef",
    "BranchBoardSnapshot",
    "BranchCardSnapshot",
    "CandidateSummarySnapshot",
    "BranchDecisionRef",
    "BranchDecisionKind",
    "BranchDecisionSnapshot",
    "BranchResolution",
    "BranchResolutionRef",
    "ExplorationMode",
    "MergeOutcomeRef",
    "MergeOutcomeSnapshot",
    "ShortlistEntrySnapshot",
]
