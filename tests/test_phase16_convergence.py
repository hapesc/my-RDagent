from __future__ import annotations

from pathlib import Path

from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.run import RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.contracts.tool_io import BranchFallbackRequest, BranchMergeRequest, BranchShortlistRequest
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.branch_merge_service import BranchMergeService
from rd_agent.orchestration.convergence_service import ConvergenceService
from rd_agent.tools.exploration_tools import rd_branch_fallback, rd_branch_merge, rd_branch_shortlist


def _branch(branch_id: str, *, run_id: str = "run-converge", quality: float, priority: float) -> BranchSnapshot:
    stage = StageSnapshot(
        stage_key=StageKey.VERIFY,
        status=StageStatus.COMPLETED,
        summary=f"{branch_id} verified.",
        next_stage_key=StageKey.SYNTHESIZE,
    )
    return BranchSnapshot(
        branch_id=branch_id,
        run_id=run_id,
        label=f"{branch_id} hypothesis",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.VERIFY,
        stages=[stage],
        score=BranchScore(
            exploration_priority=priority,
            result_quality=quality,
            rationale=f"{branch_id} quality {quality:.2f}.",
        ),
        lineage=BranchLineage(source_summary=f"Evidence for {branch_id}."),
        artifact_ids=[],
    )


def _seed_run(state_store: ArtifactStateStore, branches: list[BranchSnapshot]) -> None:
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-converge",
            title="Convergence board",
            status=RunStatus.ACTIVE,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Convergence summary.",
        )
    )


def test_candidate_summary_precedes_merge_attempt(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branches = [
        _branch("branch-a", quality=0.91, priority=0.55),
        _branch("branch-b", quality=0.82, priority=0.62),
    ]
    _seed_run(state_store, branches)
    service = ConvergenceService(state_store=state_store, board_service=BranchBoardService(state_store))

    result = rd_branch_shortlist(BranchShortlistRequest(run_id="run-converge", minimum_quality=0.8), service=service)

    assert result["structuredContent"]["candidate_summary"]["branch_ids"] == ["branch-a", "branch-b"]
    assert [entry["branch_id"] for entry in result["structuredContent"]["shortlist"]] == ["branch-a", "branch-b"]
    assert result["structuredContent"]["candidate_summary"]["conclusions"][0].startswith("branch-a hypothesis")


def test_merge_success_publishes_synthesis_artifact_with_source_provenance(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branches = [
        _branch("branch-a", quality=0.91, priority=0.55),
        _branch("branch-b", quality=0.84, priority=0.62),
    ]
    _seed_run(state_store, branches)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merge_service = BranchMergeService(
        state_store=state_store, convergence_service=convergence_service, board_service=board_service
    )

    result = rd_branch_merge(BranchMergeRequest(run_id="run-converge", minimum_quality=0.8), service=merge_service)

    assert result["structuredContent"]["outcome"]["merged_branch_id"] == "branch-a"
    assert result["structuredContent"]["outcome"]["source_branch_ids"] == ["branch-a", "branch-b"]
    assert "Synthesis of branch-a and branch-b." in result["structuredContent"]["outcome"]["summary"]


def test_merge_failure_records_reason_and_quality_ordered_shortlist(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branches = [
        _branch("branch-a", quality=0.95, priority=0.55),
        _branch("branch-b", quality=0.72, priority=0.62),
        _branch("branch-c", quality=0.69, priority=0.51),
    ]
    _seed_run(state_store, branches)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merge_service = BranchMergeService(
        state_store=state_store, convergence_service=convergence_service, board_service=board_service
    )

    result = rd_branch_merge(BranchMergeRequest(run_id="run-converge", minimum_quality=0.7), service=merge_service)

    assert result["structuredContent"]["outcome"]["failure_reason"] == "quality_gap_too_wide"
    assert [entry["branch_id"] for entry in result["structuredContent"]["outcome"]["shortlist"]] == [
        "branch-a",
        "branch-b",
    ]
    assert "quality_gap_too_wide" in result["structuredContent"]["outcome"]["summary"]


def test_merge_quality_degradation_falls_back_to_top1_candidate(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    branches = [
        _branch("branch-a", quality=0.95, priority=0.55),
        _branch("branch-b", quality=0.72, priority=0.62),
        _branch("branch-c", quality=0.69, priority=0.51),
    ]
    _seed_run(state_store, branches)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    merge_service = BranchMergeService(
        state_store=state_store, convergence_service=convergence_service, board_service=board_service
    )

    result = rd_branch_fallback(
        BranchFallbackRequest(run_id="run-converge", minimum_quality=0.7), service=merge_service
    )

    assert result["structuredContent"]["selected_branch_id"] == "branch-a"
    assert [entry["branch_id"] for entry in result["structuredContent"]["shortlist"]] == ["branch-a", "branch-b"]
