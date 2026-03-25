from __future__ import annotations

from pathlib import Path

from rd_agent.algorithms.prune import prune_branch_candidates
from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.exploration import (
    ApproachCategory,
    ExplorationMode,
    HypothesisSpec,
    NodeMetrics,
)
from rd_agent.contracts.run import ExecutionMode, RunBoardSnapshot, RunStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.contracts.tool_io import BranchPruneRequest
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.branch_board_service import BranchBoardService
from rd_agent.orchestration.branch_prune_service import BranchPruneService
from rd_agent.orchestration.dag_service import DAGService


def test_signal4_exempts_branch_with_unique_components() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("novel", 0.20), ("duplicate", 0.25)],
        relative_threshold=0.5,
        branch_component_classes={
            "best": {"model"},
            "novel": {"ensemble"},
            "duplicate": {"model"},
        },
        global_best_component_classes={"model"},
    )

    assert pruned == ["duplicate"]


def test_signal4_still_prunes_branch_without_unique_components() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("duplicate", 0.20)],
        relative_threshold=0.5,
        branch_component_classes={
            "best": {"model", "ensemble"},
            "duplicate": {"model"},
        },
        global_best_component_classes={"model", "ensemble"},
    )

    assert pruned == ["duplicate"]


def test_signal4_is_skipped_when_component_data_is_missing() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("candidate", 0.20)],
        relative_threshold=0.5,
        branch_component_classes=None,
        global_best_component_classes={"model"},
    )

    assert pruned == ["candidate"]


def test_signal4_still_respects_min_active_branches() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.95), ("novel", 0.20), ("candidate", 0.10)],
        relative_threshold=0.5,
        min_active_branches=3,
        branch_component_classes={
            "best": {"model"},
            "novel": {"ensemble"},
            "candidate": {"model"},
        },
        global_best_component_classes={"model"},
    )

    assert pruned == []


def test_existing_three_signal_behavior_is_unchanged_without_component_data() -> None:
    pruned = prune_branch_candidates(
        [("best", 0.90), ("protected", 0.50), ("overfit", 0.40)],
        budget_ratio=1.0,
        generalization_gaps={"protected": 0.05, "overfit": 0.20},
        overfitting_risks={"protected": 0.10, "overfit": 0.80},
    )

    assert pruned == ["overfit"]


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
        run_id="run-prune",
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


def test_branch_prune_service_uses_persisted_component_classes_for_signal4(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    board_service = BranchBoardService(state_store)
    service = BranchPruneService(
        state_store=state_store,
        board_service=board_service,
        dag_service=dag_service,
    )
    best = _branch("branch-best", "best", 0.95)
    novel = _branch("branch-novel", "novel", 0.20)
    duplicate = _branch("branch-duplicate", "duplicate", 0.15)
    for branch in (best, novel, duplicate):
        state_store.write_branch_snapshot(branch)
    state_store.write_run_snapshot(
        RunBoardSnapshot(
            run_id="run-prune",
            title="Prune run",
            status=RunStatus.ACTIVE,
            execution_mode=ExecutionMode.GATED,
            exploration_mode=ExplorationMode.EXPLORATION,
            branch_ids=[best.branch_id, novel.branch_id, duplicate.branch_id],
            primary_branch_id=best.branch_id,
            highlighted_artifact_ids=[],
            summary="Prune summary.",
            current_round=5,
            max_rounds=10,
        )
    )
    state_store.write_hypothesis_spec(
        best.branch_id,
        HypothesisSpec(
            label=best.label,
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="quality",
            rationale="Best branch.",
            component_classes=("model",),
        ),
    )
    state_store.write_hypothesis_spec(
        novel.branch_id,
        HypothesisSpec(
            label=novel.label,
            approach_category=ApproachCategory.ENSEMBLE,
            target_challenge="novelty",
            rationale="Novel branch.",
            component_classes=("ensemble",),
        ),
    )
    state_store.write_hypothesis_spec(
        duplicate.branch_id,
        HypothesisSpec(
            label=duplicate.label,
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="duplicate",
            rationale="Duplicate branch.",
            component_classes=("model",),
        ),
    )
    dag_service.create_node(
        run_id="run-prune",
        branch_id=best.branch_id,
        node_metrics=NodeMetrics(validation_score=0.95),
    )
    dag_service.create_node(
        run_id="run-prune",
        branch_id=novel.branch_id,
        node_metrics=NodeMetrics(validation_score=0.20),
    )
    dag_service.create_node(
        run_id="run-prune",
        branch_id=duplicate.branch_id,
        node_metrics=NodeMetrics(validation_score=0.15),
    )

    result = service.prune(BranchPruneRequest(run_id="run-prune", relative_threshold=0.5))

    assert duplicate.branch_id in result.pruned_branch_ids
    assert novel.branch_id not in result.pruned_branch_ids
