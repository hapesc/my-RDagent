"""CLI tool-facing request and response contracts for the V3 surface."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .artifact import ArtifactKind, ArtifactSnapshot
from .branch import BranchSnapshot
from .exploration import (
    BranchBoardSnapshot,
    BranchDecisionSnapshot,
    CandidateSummarySnapshot,
    ExplorationMode,
    FinalSubmissionSnapshot,
    HypothesisSpec,
    MergeOutcomeSnapshot,
    ShortlistEntrySnapshot,
)
from .isolation import BranchIsolationSnapshot
from .memory import MemoryId, MemoryKind, MemoryNamespace
from .recovery import RecoveryAssessment
from .run import ExecutionMode, RunBoardSnapshot
from .stage import StageKey, StageSnapshot, StageStatus


class RunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    task_summary: str = Field(min_length=1)
    scenario_label: str = Field(min_length=1)
    initial_branch_label: str | None = None
    execution_mode: ExecutionMode = ExecutionMode.GATED
    exploration_mode: ExplorationMode = ExplorationMode.EXPLORATION
    branch_hypotheses: list[str] | None = None
    max_stage_iterations: int = Field(default=1, ge=1)


class RunGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)


class RunGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run: RunBoardSnapshot


class BranchGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)


class BranchGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch: BranchSnapshot


class BranchListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    include_completed: bool = True


class BranchListResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    items: list[BranchSnapshot] = Field(default_factory=list)


class BranchForkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_branch_id: str | None = None
    rationale: str = Field(min_length=1)


class BranchForkResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch: BranchSnapshot
    decision: BranchDecisionSnapshot
    workspace_root: str = Field(min_length=1)


class BranchBoardGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)


class BranchBoardGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    board: BranchBoardSnapshot


class BranchSelectNextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    include_completed: bool = False


class BranchSelectNextRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    exploration_priority: float = Field(ge=0.0)
    result_quality: float = Field(ge=0.0)
    current_stage_key: StageKey
    recommended_next_step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class BranchSelectNextResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    recommendation: BranchSelectNextRecommendation


class BranchPruneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    relative_threshold: float = Field(default=0.5, ge=0.0)
    min_active_branches: int = Field(default=2, ge=1)


class BranchPruneResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    active_branch_ids: list[str] = Field(default_factory=list)
    pruned_branch_ids: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    board: BranchBoardSnapshot


class BranchShareAssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    source_branch_id: str = Field(min_length=1)
    target_branch_id: str = Field(min_length=1)
    similarity: float = Field(ge=0.0, le=1.0)
    judge_allows_share: bool = True


class BranchShareAssessResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligible: bool
    granularity: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    decision: BranchDecisionSnapshot


class BranchShareApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    source_branch_id: str = Field(min_length=1)
    target_branch_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    similarity: float = Field(ge=0.0, le=1.0)
    judge_allows_share: bool = True


class BranchShareApplyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1)
    granularity: str = Field(min_length=1)
    decision: BranchDecisionSnapshot
    board: BranchBoardSnapshot
    owner_branch_id: str = Field(min_length=1)
    shared_namespace: str | None = None


class BranchShortlistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    minimum_quality: float = Field(default=0.7, ge=0.0, le=1.0)


class BranchShortlistResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_summary: CandidateSummarySnapshot
    shortlist: list[ShortlistEntrySnapshot] = Field(default_factory=list)
    board: BranchBoardSnapshot


class BranchMergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    minimum_quality: float = Field(default=0.7, ge=0.0, le=1.0)


class BranchMergeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome: MergeOutcomeSnapshot
    board: BranchBoardSnapshot


class BranchFallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    minimum_quality: float = Field(default=0.7, ge=0.0, le=1.0)


class BranchFallbackResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_branch_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    shortlist: list[ShortlistEntrySnapshot] = Field(default_factory=list)


class ExploreRoundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    hypotheses: list[str] = Field(default_factory=list)
    hypothesis_specs: list[HypothesisSpec] | None = None
    auto_prune: bool = Field(default=True)


class ExploreRoundResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_branch_id: str = Field(min_length=1)
    recommended_next_step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    board: BranchBoardSnapshot
    dispatched_branch_ids: list[str] = Field(default_factory=list)
    sharing_candidate_ids: list[str] = Field(default_factory=list)
    pruned_branch_ids: list[str] = Field(default_factory=list)
    dag_node_ids: list[str] = Field(default_factory=list)
    round_diversity_score: float | None = None
    finalization_submission: FinalSubmissionSnapshot | None = None


class ConvergeRoundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    minimum_quality: float = Field(default=0.7, ge=0.0, le=1.0)


class ConvergeRoundResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_branch_id: str = Field(min_length=1)
    recommended_next_step: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    board: BranchBoardSnapshot
    merge_summary: str = Field(min_length=1)


class StageGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    stage_key: StageKey


class StageGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    stage: StageSnapshot
    items: list[ArtifactSnapshot] = Field(default_factory=list)


class _StageWriteRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    stage_iteration: int = Field(default=1, ge=1)
    summary: str = Field(min_length=1)
    artifact_ids: list[str] = Field(default_factory=list)
    next_stage_key: StageKey | None = None


class StageStartRequest(_StageWriteRequestBase):
    pass


class StageCompleteRequest(_StageWriteRequestBase):
    pass


class StageBlockRequest(_StageWriteRequestBase):
    blocking_reasons: list[str] = Field(default_factory=list)


class StageTransitionRequest(_StageWriteRequestBase):
    status: StageStatus
    blocking_reasons: list[str] = Field(default_factory=list)


class StageWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    branch: BranchSnapshot
    stage: StageSnapshot


class ArtifactListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str | None = None
    stage_key: StageKey | None = None
    kind: ArtifactKind | None = None


class ArtifactListResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str | None = None
    items: list[ArtifactSnapshot] = Field(default_factory=list)


class RecoveryAssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey


class RecoveryAssessResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assessment: RecoveryAssessment


class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    hypothesis: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    reason: str = Field(min_length=1)
    kind: MemoryKind = MemoryKind.ATOMIC
    memory_id: MemoryId | None = Field(default=None)
    evidence: list[str] | None = None
    outcome: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str | None = Field(default=None, min_length=1)
    owner_branch_id: str | None = Field(default=None, min_length=1)


class MemoryListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    stage_key: StageKey
    task_query: str
    limit: int = Field(default=10, ge=1)


class MemoryPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str | None = Field(default=None, min_length=1)
    owner_branch_id: str | None = Field(default=None, min_length=1)
    promoted_by: str = Field(min_length=1)
    promotion_reason: str = Field(min_length=1)


class MemoryResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str = Field(min_length=1)
    owner_branch_id: str = Field(min_length=1)
    stage_key: StageKey
    kind: MemoryKind
    hypothesis: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    reason: str = Field(min_length=1)
    evidence: list[str] | None = None
    outcome: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_namespace: MemoryNamespace
    shared_namespace: MemoryNamespace | None = None
    promotion_reason: str | None = None


class MemoryGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: MemoryId
    run_id: str = Field(min_length=1)
    owner_branch_id: str = Field(min_length=1)
    stage_key: StageKey
    kind: MemoryKind
    hypothesis: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    reason: str = Field(min_length=1)
    evidence: list[str] | None = None
    outcome: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_namespace: MemoryNamespace
    shared_namespace: MemoryNamespace | None = None
    promotion_reason: str | None = None
    can_promote: bool | None = None


class MemoryListResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    items: list[MemoryResultItem] = Field(default_factory=list)


class BranchPathsGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)


class BranchPathsGetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    paths: BranchIsolationSnapshot


# Backward-compatible aliases while later plans migrate to the Phase 13 names.
RunBoardRequest = RunGetRequest
RunBoardResponse = RunGetResult
BranchCatalogRequest = BranchListRequest
BranchCatalogResponse = BranchListResult
ArtifactCatalogRequest = ArtifactListRequest
ArtifactCatalogResponse = ArtifactListResult
RecoveryAssessmentRequest = RecoveryAssessRequest
RecoveryAssessmentResponse = RecoveryAssessResult


__all__ = [
    "ArtifactCatalogRequest",
    "ArtifactCatalogResponse",
    "ArtifactListRequest",
    "ArtifactListResult",
    "BranchCatalogRequest",
    "BranchCatalogResponse",
    "BranchBoardGetRequest",
    "BranchBoardGetResult",
    "BranchForkRequest",
    "BranchForkResult",
    "BranchPruneRequest",
    "BranchPruneResult",
    "BranchShareApplyRequest",
    "BranchShareApplyResult",
    "BranchShareAssessRequest",
    "BranchShareAssessResult",
    "BranchShortlistRequest",
    "BranchShortlistResult",
    "BranchMergeRequest",
    "BranchMergeResult",
    "BranchFallbackRequest",
    "BranchFallbackResult",
    "ConvergeRoundRequest",
    "ConvergeRoundResult",
    "ExploreRoundRequest",
    "ExploreRoundResult",
    "BranchSelectNextRecommendation",
    "BranchSelectNextRequest",
    "BranchSelectNextResult",
    "BranchGetRequest",
    "BranchGetResult",
    "BranchListRequest",
    "BranchListResult",
    "BranchPathsGetRequest",
    "BranchPathsGetResult",
    "MemoryCreateRequest",
    "MemoryGetRequest",
    "MemoryGetResult",
    "MemoryListRequest",
    "MemoryListResult",
    "MemoryPromoteRequest",
    "MemoryResultItem",
    "RecoveryAssessRequest",
    "RecoveryAssessResult",
    "RecoveryAssessmentRequest",
    "RecoveryAssessmentResponse",
    "RunBoardRequest",
    "RunBoardResponse",
    "RunGetRequest",
    "RunGetResult",
    "RunStartRequest",
    "StageGetRequest",
    "StageGetResult",
    "StageBlockRequest",
    "StageCompleteRequest",
    "StageStartRequest",
    "StageTransitionRequest",
    "StageWriteResult",
]
