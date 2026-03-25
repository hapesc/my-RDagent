from __future__ import annotations

from pathlib import Path

from rd_agent.contracts.exploration import NodeMetrics
from rd_agent.contracts.run import RunBoardSnapshot, RunStatus
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.dag_service import DAGService
from rd_agent.orchestration.select_parents_service import SelectParentsService


def _seed_run(state_store: ArtifactStateStore, *, current_round: int, max_rounds: int = 10) -> None:
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-parents",
            title="Phase 27 parent selection",
            status=RunStatus.ACTIVE,
            summary="Selection summary.",
            current_round=current_round,
            max_rounds=max_rounds,
        )
    )


def _seed_merge_nodes(dag_service: DAGService) -> dict[str, str]:
    quality = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(
            validation_score=0.95,
            diversity_score=0.20,
            complementarity_score=0.10,
        ),
    )
    complementary = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(
            validation_score=0.70,
            diversity_score=0.95,
            complementarity_score=0.95,
        ),
    )
    redundant = dag_service.create_node(
        run_id="run-parents",
        branch_id="branch-a",
        node_metrics=NodeMetrics(
            validation_score=0.78,
            diversity_score=0.25,
            complementarity_score=0.12,
        ),
    )
    return {
        "quality": quality.node_id,
        "complementary": complementary.node_id,
        "redundant": redundant.node_id,
    }


def test_merge_stage_uses_two_parents_and_complementarity_ordering(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    node_ids = _seed_merge_nodes(dag_service)
    _seed_run(state_store, current_round=9)

    recommendation = service.select_parents(run_id="run-parents", branch_id="branch-a")

    assert recommendation.parent_node_ids == [
        node_ids["quality"],
        node_ids["complementary"],
    ]
    assert "merge phase" in recommendation.rationale


def test_merge_stage_prefers_highest_complementarity_gap_for_second_parent(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    node_ids = _seed_merge_nodes(dag_service)
    _seed_run(state_store, current_round=9)

    recommendation = service.select_parents(run_id="run-parents", branch_id="branch-a")

    assert recommendation.parent_node_ids[0] == node_ids["quality"]
    assert recommendation.parent_node_ids[1] == node_ids["complementary"]
    assert node_ids["redundant"] not in recommendation.parent_node_ids


def test_non_merge_rounds_keep_existing_parent_counts(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    _seed_merge_nodes(dag_service)

    _seed_run(state_store, current_round=1)
    early = service.select_parents(run_id="run-parents", branch_id="branch-a")
    _seed_run(state_store, current_round=5)
    iteration = service.select_parents(run_id="run-parents", branch_id="branch-a")

    assert len(early.parent_node_ids) == 3
    assert len(iteration.parent_node_ids) == 1


def test_merge_stage_uses_node_metrics_complementarity_signal(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    service = SelectParentsService(state_store, dag_service)
    node_ids = _seed_merge_nodes(dag_service)
    _seed_run(state_store, current_round=9)

    recommendation = service.select_parents(run_id="run-parents", branch_id="branch-a")
    selected_nodes = [dag_service.get_node(node_id) for node_id in recommendation.parent_node_ids]

    assert all(node is not None for node in selected_nodes)
    assert selected_nodes[0].node_metrics.complementarity_score == 0.10
    assert selected_nodes[1].node_metrics.complementarity_score == 0.95
    assert node_ids["redundant"] not in recommendation.parent_node_ids
