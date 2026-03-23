from __future__ import annotations

from pathlib import Path

import pytest

from v3.algorithms.prune import prune_branch_candidates
from v3.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from v3.contracts.exploration import BranchDecisionKind, BranchResolution, ExplorationMode
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.contracts.tool_io import BranchPruneRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_prune_service import BranchPruneService


def _branch(
    branch_id: str,
    *,
    quality: float,
    generalization_gap: float = 0.0,
    overfitting_risk: float = 0.0,
) -> BranchSnapshot:
    stage = StageSnapshot(
        stage_key=StageKey.BUILD,
        status=StageStatus.COMPLETED,
        summary=f"{branch_id} build complete.",
        next_stage_key=StageKey.VERIFY,
    )
    return BranchSnapshot(
        branch_id=branch_id,
        run_id="run-prune",
        label=f"{branch_id} label",
        status=BranchStatus.ACTIVE,
        current_stage_key=StageKey.BUILD,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.5,
            result_quality=quality,
            rationale=f"{branch_id} score.",
            generalization_gap=generalization_gap,
            overfitting_risk=overfitting_risk,
        ),
        lineage=BranchLineage(source_summary=f"{branch_id} lineage."),
        artifact_ids=[],
    )


def _seed_run(
    state_store: ArtifactStateStore,
    branches: list[BranchSnapshot],
    *,
    current_round: int = 0,
    max_rounds: int = 20,
) -> None:
    for branch in branches:
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-prune",
            title="Prune run",
            status=RunStatus.ACTIVE,
            branch_ids=[branch.branch_id for branch in branches],
            primary_branch_id=branches[0].branch_id,
            highlighted_artifact_ids=[],
            summary="Prune summary.",
            exploration_mode=ExplorationMode.EXPLORATION,
            current_round=current_round,
            max_rounds=max_rounds,
        )
    )


def test_prune_branch_candidates_remains_backward_compatible() -> None:
    assert prune_branch_candidates([("b1", 0.8), ("b2", 0.3)], relative_threshold=0.5) == ["b2"]


def test_prune_branch_candidates_uses_budget_ratio_for_dynamic_threshold() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.2)]

    assert prune_branch_candidates(candidates, budget_ratio=0.0) == ["b3"]
    assert prune_branch_candidates(candidates, budget_ratio=1.0) == ["b2", "b3"]
    assert prune_branch_candidates(candidates, relative_threshold=0.1, budget_ratio=1.0) == ["b2", "b3"]


def test_prune_branch_candidates_protects_generalization_and_prioritizes_overfitting() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.4)]

    protected = prune_branch_candidates(
        candidates,
        budget_ratio=1.0,
        generalization_gaps={"b2": 0.05, "b3": 0.2},
    )
    prioritized = prune_branch_candidates(
        candidates,
        budget_ratio=1.0,
        overfitting_risks={"b2": 0.8, "b3": 0.2},
    )

    assert protected == ["b3"]
    assert prioritized == ["b2", "b3"]


def test_prune_branch_candidates_respects_min_active_branches_and_edge_cases() -> None:
    candidates = [("b1", 0.9), ("b2", 0.5), ("b3", 0.4)]

    assert prune_branch_candidates(candidates, budget_ratio=1.0, min_active_branches=2) == ["b2"]
    assert prune_branch_candidates([], budget_ratio=1.0) == []
    assert prune_branch_candidates([("b1", 0.9)], budget_ratio=1.0) == []
    assert prune_branch_candidates(
        [("b1", 0.8), ("b2", 0.3)],
        relative_threshold=0.5,
        generalization_gaps=None,
        overfitting_risks=None,
    ) == ["b2"]


def test_branch_prune_request_stays_backward_compatible() -> None:
    request = BranchPruneRequest(run_id="run-prune")

    assert request.relative_threshold == 0.5
    assert request.min_active_branches == 2


def test_branch_prune_service_passes_multi_signal_parameters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    service = BranchPruneService(state_store=state_store, board_service=board_service)
    branches = [
        _branch("branch-a", quality=0.9, generalization_gap=0.01, overfitting_risk=0.1),
        _branch("branch-b", quality=0.4, generalization_gap=0.2, overfitting_risk=0.8),
        _branch("branch-c", quality=0.3, generalization_gap=0.3, overfitting_risk=0.2),
    ]
    _seed_run(state_store, branches, current_round=10, max_rounds=20)
    seen: dict[str, object] = {}

    def _fake_prune(candidates, **kwargs):
        seen["candidates"] = candidates
        seen.update(kwargs)
        return ["branch-b"]

    monkeypatch.setattr("v3.orchestration.branch_prune_service.prune_branch_candidates", _fake_prune)

    result = service.prune(BranchPruneRequest(run_id="run-prune"))
    decisions = state_store.list_branch_decisions("run-prune", branch_id="branch-b")

    assert seen["budget_ratio"] == pytest.approx(0.5)
    assert seen["generalization_gaps"] == {
        "branch-a": 0.01,
        "branch-b": 0.2,
        "branch-c": 0.3,
    }
    assert seen["overfitting_risks"] == {
        "branch-a": 0.1,
        "branch-b": 0.8,
        "branch-c": 0.2,
    }
    assert seen["min_active_branches"] == 2
    assert result.pruned_branch_ids == ["branch-b"]
    assert "multi-signal criteria" in decisions[-1].rationale
    assert "budget_ratio=0.50" in decisions[-1].rationale


def test_branch_prune_service_uses_default_min_active_branches_and_current_round_zero(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    service = BranchPruneService(state_store=state_store, board_service=board_service)
    branches = [
        _branch("branch-a", quality=0.9),
        _branch("branch-b", quality=0.4, overfitting_risk=0.8),
        _branch("branch-c", quality=0.3),
    ]
    _seed_run(state_store, branches, current_round=0, max_rounds=20)

    result = service.prune(BranchPruneRequest(run_id="run-prune"))

    assert result.pruned_branch_ids == []


def test_branch_prune_service_enforces_two_active_branch_floor_with_real_algorithm(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    board_service = BranchBoardService(state_store)
    service = BranchPruneService(state_store=state_store, board_service=board_service)
    branches = [
        _branch("branch-a", quality=0.9),
        _branch("branch-b", quality=0.5, overfitting_risk=0.8),
        _branch("branch-c", quality=0.4),
    ]
    _seed_run(state_store, branches, current_round=20, max_rounds=20)

    result = service.prune(BranchPruneRequest(run_id="run-prune"))

    assert result.pruned_branch_ids == ["branch-b"]
    assert result.active_branch_ids == ["branch-a", "branch-c"]
    assert state_store.load_branch_snapshot("branch-b").resolution is BranchResolution.PRUNED
    assert state_store.list_branch_decisions("run-prune", branch_id="branch-b")[-1].kind is BranchDecisionKind.PRUNE
