from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.exploration import (
    BranchBoardSnapshot,
    ExplorationMode,
    FinalSubmissionSnapshot,
)
from rd_agent.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.multi_branch_service import MultiBranchService


def _run(
    *,
    run_id: str = "run-phase31",
    current_round: int = 0,
    max_rounds: int = 1,
    exploration_mode: ExplorationMode | None = None,
    branch_ids: list[str] | None = None,
    primary_branch_id: str | None = None,
) -> RunBoardSnapshot:
    return RunBoardSnapshot(
        run_id=run_id,
        title="Phase 31 contracts",
        status=RunStatus.ACTIVE,
        execution_mode=ExecutionMode.GATED,
        exploration_mode=exploration_mode,
        branch_ids=branch_ids or [],
        primary_branch_id=primary_branch_id,
        highlighted_artifact_ids=[],
        summary="Phase 31 contract test run.",
        current_round=current_round,
        max_rounds=max_rounds,
    )


def _branch(*, branch_id: str = "branch-phase31", run_id: str = "run-phase31") -> BranchSnapshot:
    return BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label="phase31-branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.FRAMING,
        score=BranchScore(
            exploration_priority=0.5,
            result_quality=0.4,
            rationale="Phase 31 branch score.",
        ),
        lineage=BranchLineage(source_summary="Seeded for phase 31."),
        artifact_ids=[],
    )


def _submission(run_id: str = "run-phase31") -> FinalSubmissionSnapshot:
    return FinalSubmissionSnapshot(
        submission_id="submission-phase31",
        run_id=run_id,
        winner_node_id="node-winner",
        winner_branch_id="branch-phase31",
        holdout_mean=0.91,
        holdout_std=0.02,
        ranked_candidates=[],
        ancestry_chain=[],
    )


def _service(
    state_store: ArtifactStateStore,
    *,
    holdout_validation_service: object | None = None,
) -> MultiBranchService:
    return MultiBranchService(
        state_store=state_store,
        workspace_manager=MagicMock(),
        branch_lifecycle_service=MagicMock(),
        branch_board_service=MagicMock(),
        selection_service=MagicMock(),
        branch_merge_service=MagicMock(),
        holdout_validation_service=holdout_validation_service,
    )


def test_exploration_mode_finalized_is_valid_str_enum_member() -> None:
    assert ExplorationMode.FINALIZED == "finalized"
    assert ExplorationMode("finalized") is ExplorationMode.FINALIZED


def test_branch_board_snapshot_accepts_finalized_mode() -> None:
    board = BranchBoardSnapshot(
        board_id="board-phase31",
        run_id="run-phase31",
        mode=ExplorationMode.FINALIZED,
        summary="Finalized board.",
    )

    assert board.mode is ExplorationMode.FINALIZED


def test_run_board_snapshot_model_copy_accepts_finalized_mode() -> None:
    run = _run()

    finalized = run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})

    assert finalized.exploration_mode is ExplorationMode.FINALIZED


def test_try_finalize_writes_finalized_mode_on_success(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run())
    holdout_service = MagicMock()
    holdout_service.finalize.return_value = _submission()
    service = _service(state_store, holdout_validation_service=holdout_service)

    submission = service._try_finalize("run-phase31")
    run = state_store.load_run_snapshot("run-phase31")

    assert submission is not None
    assert submission.winner_node_id == "node-winner"
    assert run is not None
    assert run.current_round == 1
    assert run.exploration_mode is ExplorationMode.FINALIZED


def test_try_finalize_does_not_write_finalized_when_finalization_fails(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run())
    holdout_service = MagicMock()
    holdout_service.finalize.side_effect = ValueError("holdout failed")
    service = _service(state_store, holdout_validation_service=holdout_service)

    submission = service._try_finalize("run-phase31")
    run = state_store.load_run_snapshot("run-phase31")

    assert submission is None
    assert run is not None
    assert run.current_round == 1
    assert run.exploration_mode is None


def test_finalize_early_writes_finalized_mode_on_success(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run(max_rounds=5))
    holdout_service = MagicMock()
    holdout_service.finalize.return_value = _submission()
    service = _service(state_store, holdout_validation_service=holdout_service)

    submission = service.finalize_early(run_id="run-phase31")
    run = state_store.load_run_snapshot("run-phase31")

    assert submission.winner_branch_id == "branch-phase31"
    assert run is not None
    assert run.exploration_mode is ExplorationMode.FINALIZED


def test_should_finalize_returns_true_when_round_budget_exhausted_and_holdout_available(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run(current_round=3, max_rounds=3))
    service = _service(state_store, holdout_validation_service=MagicMock())

    assert service.should_finalize("run-phase31") is True


def test_should_finalize_returns_false_when_round_budget_not_exhausted(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run(current_round=2, max_rounds=3))
    service = _service(state_store, holdout_validation_service=MagicMock())

    assert service.should_finalize("run-phase31") is False


def test_should_finalize_returns_false_when_holdout_service_missing(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    state_store.write_run_snapshot(_run(current_round=3, max_rounds=3))
    service = _service(state_store, holdout_validation_service=None)

    assert service.should_finalize("run-phase31") is False


def test_should_finalize_returns_false_when_run_is_missing(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = _service(state_store, holdout_validation_service=MagicMock())

    assert service.should_finalize("run-phase31") is False


def test_branch_board_service_propagates_finalized_mode_from_run(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branch = _branch()
    state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        _run(
            exploration_mode=ExplorationMode.FINALIZED,
            branch_ids=[branch.branch_id],
            primary_branch_id=branch.branch_id,
        )
    )
    board_service = BranchBoardService(state_store)

    board = board_service.get_board("run-phase31")

    assert board.mode is ExplorationMode.FINALIZED
