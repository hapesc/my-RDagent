from __future__ import annotations

from pathlib import Path

import pytest

from v3.contracts.exploration import NodeMetrics
from v3.contracts.run import RunBoardSnapshot, RunStatus
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.dag_service import DAGService
from v3.orchestration.select_parents_service import ParentRecommendation, SelectParentsService


def _seed_run(state_store: ArtifactStateStore, *, current_round: int, max_rounds: int = 10) -> None:
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-parents",
            title="Parent selection",
            status=RunStatus.ACTIVE,
            summary="Parent selection summary.",
            current_round=current_round,
            max_rounds=max_rounds,
        )
    )


def _seed_nodes(dag_service: DAGService) -> dict[str, str]:
    quality = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(validation_score=1.0, diversity_score=0.0),
    )
    diverse = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(validation_score=0.2, diversity_score=1.5),
    )
    balanced = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(validation_score=0.7, diversity_score=0.6),
    )
    penalized = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(validation_score=0.9, generalization_gap=0.8, overfitting_risk=0.8),
    )
    return {
        "quality": quality.node_id,
        "diverse": diverse.node_id,
        "balanced": balanced.node_id,
        "penalized": penalized.node_id,
    }


def test_select_parents_uses_budget_phase_to_choose_k_and_ordering(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    node_ids = _seed_nodes(dag_service)

    _seed_run(state_store, current_round=1)
    early = service.select_parents(run_id="run-parents", branch_id="branch-a")
    _seed_run(state_store, current_round=5)
    iteration = service.select_parents(run_id="run-parents", branch_id="branch-a")
    _seed_run(state_store, current_round=9)
    merge = service.select_parents(run_id="run-parents", branch_id="branch-a")

    assert len(early.parent_node_ids) == 3
    assert len(iteration.parent_node_ids) == 1
    assert len(merge.parent_node_ids) == 1
    assert early.parent_node_ids[0] == node_ids["diverse"]
    assert merge.parent_node_ids == [node_ids["quality"]]


def test_select_parents_honors_max_parents_override_and_returns_context(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    _seed_nodes(dag_service)
    _seed_run(state_store, current_round=5)

    recommendation = service.select_parents(run_id="run-parents", branch_id="branch-a", max_parents=2)

    assert isinstance(recommendation, ParentRecommendation)
    assert len(recommendation.parent_node_ids) == 2
    assert recommendation.budget_ratio == pytest.approx(0.5)
    assert recommendation.diversity_weight == pytest.approx(0.5)
    assert "budget_ratio=0.50" in recommendation.rationale


def test_select_parents_raises_for_missing_branch_nodes(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    _seed_run(state_store, current_round=1)

    with pytest.raises(KeyError):
        service.select_parents(run_id="run-parents", branch_id="missing")


def test_select_parents_returns_existing_node_for_later_round_parent_linkage(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    first = dag_service.create_node(
        run_id="run-parents", branch_id="branch-a", node_metrics=NodeMetrics(diversity_score=0.4)
    )
    _seed_run(state_store, current_round=2)

    recommendation = service.select_parents(run_id="run-parents", branch_id="branch-a")

    assert recommendation.parent_node_ids == [first.node_id]
