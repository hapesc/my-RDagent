from __future__ import annotations

from pathlib import Path

import pytest

from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import BranchBoardSnapshot, ExplorationMode, FinalSubmissionSnapshot
from v3.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchMergeRequest, ExploreRoundRequest, ExploreRoundResult
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.operator_guidance import build_finalization_guidance, render_operator_guidance_text
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.selection_service import SelectionService
from tests.test_phase27_merge_synthesis import _CapturingMerger, _seed_run


def _build_merge_service(tmp_path: Path, *, holdout_score: float) -> BranchMergeService:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    _seed_run(state_store, dag_service)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    return BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=_CapturingMerger(holdout_score=holdout_score),
        dag_service=dag_service,
    )


def _stage() -> StageSnapshot:
    return StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary="Build complete.",
        next_stage_key=StageKey.VERIFY,
    )


def _branch(branch_id: str, label: str, quality: float) -> BranchSnapshot:
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-phase28-activation",
        label=label,
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[_stage()],
        score=BranchScore(
            exploration_priority=quality,
            result_quality=quality,
            rationale=f"{label} quality snapshot.",
        ),
        lineage=BranchLineage(source_summary=f"{label} lineage."),
        artifact_ids=[],
    )


def _submission(run_id: str = "run-phase28-activation") -> FinalSubmissionSnapshot:
    return FinalSubmissionSnapshot(
        submission_id="submission-1",
        run_id=run_id,
        winner_node_id="winner-node",
        winner_branch_id="branch-primary",
        holdout_mean=0.92,
        holdout_std=0.01,
        ranked_candidates=[],
        ancestry_chain=["parent-node"],
    )


class _StubHoldoutService:
    def __init__(self, submission: FinalSubmissionSnapshot) -> None:
        self._submission = submission
        self.calls: list[str] = []

    def finalize(self, *, run_id: str) -> FinalSubmissionSnapshot:
        self.calls.append(run_id)
        return self._submission


def _build_activation_context(
    tmp_path: Path,
    *,
    current_round: int,
    max_rounds: int,
    holdout_service: _StubHoldoutService | None,
) -> tuple[ArtifactStateStore, MultiBranchService]:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    workspace_manager = BranchWorkspaceManager(tmp_path / "state")
    run_board_service = RunBoardService(state_store)
    branches = [
        _branch("branch-primary", "primary", 0.92),
        _branch("branch-peer", "peer", 0.84),
    ]
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-phase28-activation",
            title="Phase 28 activation",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Phase 28 activation summary.",
            current_round=current_round,
            max_rounds=max_rounds,
        )
    )
    multi_branch_service = MultiBranchService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        branch_lifecycle_service=BranchLifecycleService(
            state_store=state_store,
            workspace_manager=workspace_manager,
            run_board_service=run_board_service,
        ),
        branch_board_service=board_service,
        selection_service=SelectionService(state_store=state_store),
        branch_merge_service=BranchMergeService(
            state_store=state_store,
            convergence_service=convergence_service,
            board_service=board_service,
            dag_service=dag_service,
        ),
        dispatcher=lambda payload: payload,
        dag_service=dag_service,
        holdout_validation_service=holdout_service,
    )
    return state_store, multi_branch_service


def test_explore_round_result_accepts_optional_finalization_submission() -> None:
    board = BranchBoardSnapshot(
        board_id="board-1",
        run_id="run-phase28-activation",
        mode=ExplorationMode.EXPLORATION,
        active_cards=[],
        history_cards=[],
        summary="Activation board.",
    )
    result = ExploreRoundResult(
        selected_branch_id="branch-primary",
        recommended_next_step="continue",
        rationale="No finalization yet.",
        board=board,
        finalization_submission=None,
    )

    assert result.finalization_submission is None


def test_validate_merge_holdout_removed() -> None:
    with pytest.raises(ImportError):
        exec("from v3.algorithms.merge import validate_merge_holdout", {})


def test_merge_still_works_with_inline_comparison(tmp_path: Path) -> None:
    accepting_service = _build_merge_service(tmp_path / "accept", holdout_score=0.95)
    accepted = accepting_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9},
            "branch-b": {"ensemble": 0.9},
        },
    )

    rejecting_service = _build_merge_service(tmp_path / "reject", holdout_score=0.70)
    rejected = rejecting_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9},
            "branch-b": {"ensemble": 0.9},
        },
    )

    assert accepted.outcome.failure_reason is None
    assert accepted.outcome.merged_branch_id == "branch-a"
    assert rejected.outcome.failure_reason == "holdout_validation_failed"


def test_run_exploration_round_auto_finalizes_at_budget_exhaustion(tmp_path: Path) -> None:
    submission = _submission()
    holdout_service = _StubHoldoutService(submission)
    _state_store, multi_branch_service = _build_activation_context(
        tmp_path,
        current_round=4,
        max_rounds=5,
        holdout_service=holdout_service,
    )

    result = multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-activation",
            hypotheses=["primary", "peer"],
            auto_prune=False,
        )
    )

    assert result.finalization_submission == submission
    assert holdout_service.calls == ["run-phase28-activation"]


def test_run_exploration_round_skips_finalization_before_budget_exhaustion(tmp_path: Path) -> None:
    holdout_service = _StubHoldoutService(_submission())
    _state_store, multi_branch_service = _build_activation_context(
        tmp_path,
        current_round=2,
        max_rounds=5,
        holdout_service=holdout_service,
    )

    result = multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-activation",
            hypotheses=["primary", "peer"],
            auto_prune=False,
        )
    )

    assert result.finalization_submission is None
    assert holdout_service.calls == []


def test_run_exploration_round_without_holdout_service_never_finalizes(tmp_path: Path) -> None:
    _state_store, multi_branch_service = _build_activation_context(
        tmp_path,
        current_round=4,
        max_rounds=5,
        holdout_service=None,
    )

    result = multi_branch_service.run_exploration_round(
        ExploreRoundRequest(
            run_id="run-phase28-activation",
            hypotheses=["primary", "peer"],
            auto_prune=False,
        )
    )

    assert result.finalization_submission is None


def test_finalize_early_uses_holdout_service(tmp_path: Path) -> None:
    submission = _submission()
    holdout_service = _StubHoldoutService(submission)
    _state_store, multi_branch_service = _build_activation_context(
        tmp_path,
        current_round=1,
        max_rounds=5,
        holdout_service=holdout_service,
    )

    result = multi_branch_service.finalize_early(run_id="run-phase28-activation")

    assert result == submission
    assert holdout_service.calls == ["run-phase28-activation"]


def test_finalize_early_without_holdout_service_raises(tmp_path: Path) -> None:
    _state_store, multi_branch_service = _build_activation_context(
        tmp_path,
        current_round=1,
        max_rounds=5,
        holdout_service=None,
    )

    with pytest.raises(ValueError):
        multi_branch_service.finalize_early(run_id="run-phase28-activation")


def test_finalization_guidance_renders_winner_and_holdout_metrics() -> None:
    submission = _submission()

    guidance = build_finalization_guidance(submission=submission)
    rendered = render_operator_guidance_text(guidance)

    assert "finalization complete" in guidance.current_state.lower()
    assert submission.winner_node_id in guidance.current_state
    assert submission.winner_node_id in rendered
    assert "holdout_mean" in rendered
