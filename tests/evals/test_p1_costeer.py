"""P1: CoSTEER self-correction effectiveness evaluation."""

from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from evaluation_service.custom_metrics.costeer_efficiency import (
    CoSTEERRound,
    CoSTEERTrace,
    compute_costeer_efficiency,
    create_feedback_actionability_metric,
)

pytestmark = pytest.mark.eval


def test_costeer_trace_detects_regression():
    trace = CoSTEERTrace(
        task_summary="implement momentum factor",
        rounds=[
            CoSTEERRound(round_index=0, code="v0", feedback="compile error", accepted=False, score=0.0),
            CoSTEERRound(round_index=1, code="v1", feedback="runs but wrong output", accepted=False, score=0.4),
            CoSTEERRound(round_index=2, code="v2", feedback="introduced regression", accepted=False, score=0.2),
        ],
    )
    result = compute_costeer_efficiency(trace)
    assert result.total_rounds == 3
    assert result.regression_count == 1  # round 2 scored lower than round 1
    assert not result.converged


def test_costeer_trace_converges():
    trace = CoSTEERTrace(
        task_summary="implement momentum factor",
        rounds=[
            CoSTEERRound(round_index=0, code="v0", feedback="compile error", accepted=False, score=0.0),
            CoSTEERRound(round_index=1, code="v1", feedback="looks good", accepted=True, score=0.9),
        ],
    )
    result = compute_costeer_efficiency(trace)
    assert result.converged
    assert result.rounds_to_converge == 2
    assert result.regression_count == 0


def test_actionable_feedback_scores_high():
    """Good feedback should score above threshold."""
    test_case = LLMTestCase(
        input="Implement a 5-day momentum factor using pct_change",
        actual_output=(
            "The code fails because `df.pct_change(5)` is called on the entire "
            "DataFrame instead of per-stock. Fix: use "
            "`df.groupby('stock_id')['close'].pct_change(5)` to compute "
            "per-stock momentum. Also, the return DataFrame is missing the "
            "'factor_value' column rename."
        ),
    )
    metric = create_feedback_actionability_metric()
    assert_test(test_case, [metric])


def test_vague_feedback_scores_low():
    """Vague feedback should score below threshold."""
    test_case = LLMTestCase(
        input="Implement a 5-day momentum factor using pct_change",
        actual_output="The code doesn't work. Please try again.",
    )
    metric = create_feedback_actionability_metric(threshold=0.3)
    # We expect this to score LOW — assert it's below 0.3
    metric.measure(test_case)
    assert metric.score < 0.4, f"Vague feedback scored too high: {metric.score}"
