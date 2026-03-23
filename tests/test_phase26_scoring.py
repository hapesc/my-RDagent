from __future__ import annotations

from v3.orchestration.scoring_service import (
    BranchSelectionSignal,
    compute_generalization_signals,
    project_branch_score,
)


def test_compute_generalization_gap_returns_expected_difference() -> None:
    gap, risk = compute_generalization_signals(validation_score=0.7, training_score=0.9)

    assert gap == 0.2
    assert risk == 0.4


def test_compute_generalization_signals_surfaces_overfitting_risk() -> None:
    gap, risk = compute_generalization_signals(
        validation_score=0.7,
        training_score=1.0,
        cross_fold_variance=0.15,
        score_trend=-0.1,
    )

    assert gap == 0.3
    assert risk > 0.5


def test_compute_generalization_signals_default_without_training_data() -> None:
    assert compute_generalization_signals(validation_score=0.7) == (0.0, 0.0)


def test_project_branch_score_remains_backward_compatible() -> None:
    score = project_branch_score(
        BranchSelectionSignal(
            branch_id="b1",
            branch_potential=0.8,
            sibling_potentials=(0.8, 0.4),
            avg_value=0.4,
            visits=2,
            total_visits=8,
        )
    )

    assert score.exploration_priority >= 0.0
    assert score.result_quality >= 0.0
    assert score.generalization_gap == 0.0
    assert score.overfitting_risk == 0.0
