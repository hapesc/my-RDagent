from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from rd_agent.algorithms.decay import category_entropy, cosine_decay
from rd_agent.contracts.branch import BranchScore
from rd_agent.contracts.exploration import (
    ApproachCategory,
    DAGEdgeSnapshot,
    DAGNodeSnapshot,
    EdgeType,
    HypothesisSpec,
    NodeMetrics,
)
from rd_agent.contracts.run import RunBoardSnapshot, RunStatus


def test_branch_score_defaults_remain_backward_compatible() -> None:
    score = BranchScore(exploration_priority=0.5, result_quality=0.3, rationale="x")

    assert score.generalization_gap == 0.0
    assert score.overfitting_risk == 0.0


def test_branch_score_accepts_phase26_fields() -> None:
    score = BranchScore(
        exploration_priority=0.5,
        result_quality=0.3,
        rationale="x",
        generalization_gap=0.2,
        overfitting_risk=0.4,
    )

    assert score.generalization_gap == 0.2
    assert score.overfitting_risk == 0.4


@pytest.mark.parametrize("risk", [-0.1, 1.1])
def test_branch_score_rejects_invalid_overfitting_risk(risk: float) -> None:
    with pytest.raises(ValidationError):
        BranchScore(
            exploration_priority=0.5,
            result_quality=0.3,
            rationale="x",
            overfitting_risk=risk,
        )


def test_run_board_snapshot_defaults_remain_backward_compatible() -> None:
    run = RunBoardSnapshot(run_id="r1", title="t", status=RunStatus.ACTIVE, summary="s")

    assert run.current_round == 0
    assert run.max_rounds == 20


def test_run_board_snapshot_accepts_phase26_fields() -> None:
    run = RunBoardSnapshot(
        run_id="r1",
        title="t",
        status=RunStatus.ACTIVE,
        summary="s",
        current_round=5,
        max_rounds=20,
    )

    assert run.current_round == 5
    assert run.max_rounds == 20


def test_run_board_snapshot_rejects_invalid_max_rounds() -> None:
    with pytest.raises(ValidationError):
        RunBoardSnapshot(run_id="r1", title="t", status=RunStatus.ACTIVE, summary="s", max_rounds=0)


def test_edge_type_members_exist() -> None:
    assert EdgeType.PARENT.value == "parent"
    assert EdgeType.SHARED.value == "shared"
    assert EdgeType.MERGED.value == "merged"


def test_node_metrics_support_defaults_and_explicit_values() -> None:
    defaults = NodeMetrics()
    explicit = NodeMetrics(
        validation_score=0.8,
        generalization_gap=0.1,
        overfitting_risk=0.2,
        diversity_score=1.5,
    )

    assert defaults.validation_score == 0.0
    assert defaults.diversity_score == 0.0
    assert explicit.validation_score == 0.8
    assert explicit.diversity_score == 1.5


def test_dag_node_snapshot_defaults_and_self_reference_validation() -> None:
    node = DAGNodeSnapshot(node_id="n1", run_id="r1", branch_id="b1")

    assert node.parent_node_ids == []
    assert node.depth == 0

    with pytest.raises(ValidationError):
        DAGNodeSnapshot(node_id="n1", run_id="r1", branch_id="b1", parent_node_ids=["n1"])


def test_dag_edge_snapshot_defaults() -> None:
    edge = DAGEdgeSnapshot(source_node_id="n1", target_node_id="n2")

    assert edge.edge_type is EdgeType.PARENT
    assert edge.weight == 1.0


def test_approach_category_members_exist() -> None:
    expected = {
        "feature_engineering",
        "model_architecture",
        "data_augmentation",
        "ensemble",
        "loss_function",
        "training_strategy",
        "other",
    }

    assert {member.value for member in ApproachCategory} == expected


def test_hypothesis_spec_constructs() -> None:
    spec = HypothesisSpec(
        label="x",
        approach_category=ApproachCategory.ENSEMBLE,
        target_challenge="y",
        rationale="z",
    )

    assert spec.approach_category is ApproachCategory.ENSEMBLE


def test_cosine_decay_matches_expected_curve() -> None:
    assert cosine_decay(0.0) == pytest.approx(0.7)
    assert cosine_decay(0.5) == pytest.approx(0.5)
    assert cosine_decay(1.0) == pytest.approx(0.3)


def test_category_entropy_matches_expected_values() -> None:
    assert category_entropy({"a": 1, "b": 1, "c": 1}) == pytest.approx(math.log2(3))
    assert category_entropy({"a": 3}) == pytest.approx(0.0)
    assert category_entropy({}) == pytest.approx(0.0)
