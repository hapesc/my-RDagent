from __future__ import annotations

from pathlib import Path

from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.exploration import (
    BranchDecisionKind,
    BranchDecisionSnapshot,
    BranchResolution,
    ExplorationMode,
)
from rd_agent.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.contracts.tool_io import BranchForkRequest, BranchPruneRequest
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.branch_lifecycle_service import BranchLifecycleService
from rd_agent.orchestration.branch_prune_service import BranchPruneService
from rd_agent.orchestration.branch_workspace_manager import BranchWorkspaceManager
from rd_agent.orchestration.run_board_service import RunBoardService


def _stage(stage_key: StageKey, summary: str) -> StageSnapshot:
    return StageSnapshot(
        stage_key=stage_key,
        status=StageStatus.IN_PROGRESS,
        summary=summary,
        next_stage_key=StageKey.BUILD if stage_key is StageKey.FRAMING else None,
    )


def _branch(
    *,
    branch_id: str,
    run_id: str,
    label: str,
    status: BranchStatus = BranchStatus.ACTIVE,
    resolution: BranchResolution | None = None,
) -> BranchSnapshot:
    stage = _stage(StageKey.FRAMING, f"{label} framing is active.")
    return BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label=label,
        status=status,
        resolution=resolution,
        current_stage_key=stage.stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.7,
            result_quality=0.4,
            rationale=f"{label} remains a viable branch.",
        ),
        lineage=BranchLineage(source_summary=f"{label} lineage."),
        artifact_ids=[],
    )


def test_branch_fork_assigns_global_unique_id_and_hypothesis_label(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_store = ArtifactStateStore(state_root)
    run_board_service = RunBoardService(state_store)
    workspace_manager = BranchWorkspaceManager(state_root)
    service = BranchLifecycleService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        run_board_service=run_board_service,
    )
    stage = _stage(StageKey.FRAMING, "Source framing is active.")
    source_branch = BranchSnapshot(
        branch_id="branch-source",
        run_id="run-001",
        label="Source hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage.stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.7,
            result_quality=0.4,
            rationale="Source remains viable.",
        ),
        lineage=BranchLineage(source_summary="Source hypothesis lineage."),
        artifact_ids=[],
    )
    state_store.write_branch_snapshot(source_branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
            title="Forkable run",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            branch_ids=[source_branch.branch_id],
            primary_branch_id=source_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Run summary.",
        )
    )

    result_one = service.fork_branch(
        BranchForkRequest(
            run_id="run-001",
            source_branch_id=source_branch.branch_id,
            label="Alternative hypothesis A",
            rationale="Probe a different mechanism.",
        )
    )
    result_two = service.fork_branch(
        BranchForkRequest(
            run_id="run-001",
            source_branch_id=source_branch.branch_id,
            label="Alternative hypothesis B",
            rationale="Probe another mechanism.",
        )
    )

    assert result_one.branch.branch_id.startswith("branch-")
    assert result_two.branch.branch_id.startswith("branch-")
    assert result_one.branch.branch_id != result_two.branch.branch_id
    assert result_one.branch.label == "Alternative hypothesis A"
    assert result_one.branch.model_dump(mode="json")["label"] == "Alternative hypothesis A"
    assert result_one.decision.kind is BranchDecisionKind.FORK
    assert result_one.decision.source_branch_id == "branch-source"


def test_branch_fork_allocates_isolated_workspace_from_source_branch(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    state_store = ArtifactStateStore(state_root)
    run_board_service = RunBoardService(state_store)
    workspace_manager = BranchWorkspaceManager(state_root)
    service = BranchLifecycleService(
        state_store=state_store,
        workspace_manager=workspace_manager,
        run_board_service=run_board_service,
    )
    source_branch = _branch(branch_id="branch-source", run_id="run-001", label="Source hypothesis")
    state_store.write_branch_snapshot(source_branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
            title="Forkable run",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            branch_ids=[source_branch.branch_id],
            primary_branch_id=source_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Run summary.",
        )
    )
    source_workspace = Path(
        workspace_manager.allocate_branch_workspace(run_id="run-001", branch_id=source_branch.branch_id)
    )
    source_file = source_workspace / "notes.txt"
    source_file.write_text("branch source data\n")

    result = service.fork_branch(
        BranchForkRequest(
            run_id="run-001",
            source_branch_id=source_branch.branch_id,
            label="Forked hypothesis",
            rationale="Carry source evidence into isolated workspace.",
        )
    )

    fork_workspace = Path(result.workspace_root)
    persisted_decisions = state_store.list_branch_decisions("run-001", branch_id=result.branch.branch_id)
    updated_source = state_store.load_branch_snapshot(source_branch.branch_id)
    updated_run = state_store.load_run_snapshot("run-001")

    assert fork_workspace.exists()
    assert fork_workspace != source_workspace
    assert (fork_workspace / "notes.txt").read_text() == "branch source data\n"
    source_file.write_text("source changed\n")
    assert (fork_workspace / "notes.txt").read_text() == "branch source data\n"
    assert result.branch.lineage.parent_branch_id == source_branch.branch_id
    assert result.branch.lineage.source_summary == (
        "Forked from Source hypothesis: Carry source evidence into isolated workspace."
    )
    assert [decision.decision_id for decision in persisted_decisions] == [result.decision.decision_id]
    assert updated_source is not None
    assert result.branch.branch_id in updated_source.lineage.child_branch_ids
    assert updated_run is not None
    assert updated_run.branch_ids == [source_branch.branch_id, result.branch.branch_id]
    assert updated_run.latest_branch_decision_id == result.decision.decision_id
    assert updated_run.exploration_mode is ExplorationMode.EXPLORATION


def test_branch_board_read_model_separates_active_and_history_cards(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    active_branch = _branch(branch_id="branch-active", run_id="run-001", label="Active hypothesis")
    history_branch = _branch(
        branch_id="branch-history",
        run_id="run-001",
        label="Pruned hypothesis",
        status=BranchStatus.SUPERSEDED,
        resolution=BranchResolution.PRUNED,
    )

    state_store.write_branch_snapshot(active_branch)
    state_store.write_branch_snapshot(history_branch)
    state_store.write_branch_decision(
        BranchDecisionSnapshot(
            decision_id="decision-prune",
            run_id="run-001",
            branch_id=history_branch.branch_id,
            kind=BranchDecisionKind.PRUNE,
            mode=ExplorationMode.EXPLORATION,
            summary="Pruned after weaker evidence.",
            rationale="The branch failed the quality threshold.",
            resolution=BranchResolution.PRUNED,
            affected_branch_ids=[history_branch.branch_id],
        )
    )
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
            title="Multi-branch board",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            branch_ids=[active_branch.branch_id, history_branch.branch_id],
            primary_branch_id=active_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Board summary.",
            exploration_mode=ExplorationMode.EXPLORATION,
            latest_branch_decision_id="decision-prune",
            latest_branch_board_id="branch-board:run-001",
        )
    )

    loaded_board = board_service.get_board("run-001")
    run = state_store.load_run_snapshot("run-001")
    decisions = state_store.list_branch_decisions("run-001")

    assert loaded_board is not None
    assert [card.branch_id for card in loaded_board.active_cards] == ["branch-active"]
    assert [card.branch_id for card in loaded_board.history_cards] == ["branch-history"]
    assert loaded_board.board_id == "branch-board:run-001"
    assert loaded_board.active_cards[0].explanation == active_branch.score.rationale
    assert loaded_board.history_cards[0].explanation == "Pruned after weaker evidence."
    assert run is not None
    assert run.exploration_mode is ExplorationMode.EXPLORATION
    assert run.latest_branch_decision_id == "decision-prune"
    assert run.latest_branch_board_id == "branch-board:run-001"
    assert [decision.decision_id for decision in decisions] == ["decision-prune"]


def test_branch_prune_persists_decision_and_moves_branch_to_history(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    prune_service = BranchPruneService(state_store=state_store, board_service=board_service)
    active_branch = _branch(branch_id="branch-active", run_id="run-001", label="Active hypothesis")
    pruned_branch = _branch(branch_id="branch-pruned", run_id="run-001", label="Pruned hypothesis")
    pruned_branch = pruned_branch.model_copy(
        update={
            "score": pruned_branch.score.model_copy(update={"result_quality": 0.15}),
        }
    )
    state_store.write_branch_snapshot(active_branch)
    state_store.write_branch_snapshot(pruned_branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-001",
            title="Prune board",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            branch_ids=[active_branch.branch_id, pruned_branch.branch_id],
            primary_branch_id=active_branch.branch_id,
            highlighted_artifact_ids=[],
            summary="Board summary.",
        )
    )

    result = prune_service.prune(BranchPruneRequest(run_id="run-001", relative_threshold=0.6))
    persisted_branch = state_store.load_branch_snapshot(pruned_branch.branch_id)
    decisions = state_store.list_branch_decisions("run-001", branch_id=pruned_branch.branch_id)

    assert result.pruned_branch_ids == [pruned_branch.branch_id]
    assert persisted_branch is not None
    assert persisted_branch.status is BranchStatus.SUPERSEDED
    assert persisted_branch.resolution is BranchResolution.PRUNED
    assert decisions[-1].kind is BranchDecisionKind.PRUNE
    assert [card.branch_id for card in result.board.history_cards] == [pruned_branch.branch_id]
