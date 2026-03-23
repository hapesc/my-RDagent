"""V3-owned contracts for multi-branch exploration state."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class EdgeType(StrEnum):
    """Typed DAG edge relationships reserved for exploration topology."""

    PARENT = "parent"
    SHARED = "shared"
    MERGED = "merged"


class ComponentClass(StrEnum):
    """Structured solution component buckets for merge-stage complementarity."""

    DATA_LOAD = "data_load"
    FEATURE_ENG = "feature_eng"
    MODEL = "model"
    ENSEMBLE = "ensemble"
    WORKFLOW = "workflow"


class NodeMetrics(BaseModel):
    """Convergence-specific metrics attached to a DAG node."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity_score: float = Field(default=0.0, ge=0.0)
    complementarity_score: float = Field(default=0.0, ge=0.0)


class DAGNodeSnapshot(BaseModel):
    """Persisted run-scoped DAG node separate from branch lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    parent_node_ids: list[str] = Field(default_factory=list)
    depth: int = Field(default=0, ge=0)
    node_metrics: NodeMetrics = Field(default_factory=NodeMetrics)

    @model_validator(mode="after")
    def _validate_no_self_reference(self) -> DAGNodeSnapshot:
        if self.node_id in self.parent_node_ids:
            raise ValueError("node_id cannot reference itself as a parent")
        return self


class DAGEdgeSnapshot(BaseModel):
    """Persisted DAG edge for topology traversal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    edge_type: EdgeType = EdgeType.PARENT
    weight: float = Field(default=1.0, ge=0.0)


class ApproachCategory(StrEnum):
    """Structured hypothesis buckets for first-layer diversity enforcement."""

    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_ARCHITECTURE = "model_architecture"
    DATA_AUGMENTATION = "data_augmentation"
    ENSEMBLE = "ensemble"
    LOSS_FUNCTION = "loss_function"
    TRAINING_STRATEGY = "training_strategy"
    OTHER = "other"


class HypothesisSpec(BaseModel):
    """Structured hypothesis metadata for multi-branch exploration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    approach_category: ApproachCategory
    target_challenge: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    component_classes: tuple[ComponentClass, ...] = Field(default_factory=tuple)


__all__ = [
    "ApproachCategory",
    "BranchBoardRef",
    "BranchBoardSnapshot",
    "BranchCardSnapshot",
    "CandidateSummarySnapshot",
    "ComponentClass",
    "DAGEdgeSnapshot",
    "DAGNodeSnapshot",
    "BranchDecisionRef",
    "BranchDecisionKind",
    "BranchDecisionSnapshot",
    "BranchResolution",
    "BranchResolutionRef",
    "EdgeType",
    "ExplorationMode",
    "HypothesisSpec",
    "MergeOutcomeRef",
    "MergeOutcomeSnapshot",
    "NodeMetrics",
    "ShortlistEntrySnapshot",
]
