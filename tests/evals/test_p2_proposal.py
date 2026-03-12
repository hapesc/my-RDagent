"""P2: Proposal/hypothesis quality evaluation."""

from __future__ import annotations

import pytest
from deepeval import assert_test

from evaluation_service.custom_metrics.proposal_quality import (
    create_feasibility_metric,
    create_specificity_metric,
)
from evaluation_service.deepeval_bridge import proposal_to_test_case

pytestmark = pytest.mark.eval


def test_specificity_metric_instantiable():
    try:
        metric = create_specificity_metric()
    except Exception as exc:
        if "API key" in str(exc):
            pytest.skip("OpenAI API key not configured")
        raise
    assert "Specificity" in metric.name


def test_feasibility_metric_instantiable():
    try:
        metric = create_feasibility_metric(scenario="quant")
    except Exception as exc:
        if "API key" in str(exc):
            pytest.skip("OpenAI API key not configured")
        raise
    assert "Feasibility" in metric.name


def test_specific_hypothesis_scores_high():
    """A detailed, actionable hypothesis should pass specificity check."""
    tc = proposal_to_test_case(
        task_summary="Mine alpha factors from OHLCV data",
        hypothesis_text=(
            "Compute a 5-day price momentum factor by calculating the "
            "percentage change in closing price over the last 5 trading days, "
            "grouped by stock_id. Handle NaN from pct_change by forward-filling. "
            "Expected Sharpe ratio > 0.3 on the backtest period."
        ),
    )
    metric = create_specificity_metric()
    assert_test(tc, [metric])


def test_vague_hypothesis_scores_low():
    """A vague hypothesis should score below threshold."""
    tc = proposal_to_test_case(
        task_summary="Mine alpha factors from OHLCV data",
        hypothesis_text="Try to find a good factor that makes money.",
    )
    metric = create_specificity_metric(threshold=0.3)
    metric.measure(tc)
    assert metric.score < 0.4, f"Vague hypothesis scored too high: {metric.score}"


def test_infeasible_hypothesis_scores_low():
    """A hypothesis requiring forbidden resources should score low."""
    tc = proposal_to_test_case(
        task_summary="Mine alpha factors from OHLCV data",
        hypothesis_text=(
            "Fetch real-time order book data from Binance API, "
            "compute microstructure features using the lobster library, "
            "and train a deep learning model with PyTorch."
        ),
    )
    metric = create_feasibility_metric(scenario="quant", threshold=0.3)
    metric.measure(tc)
    assert metric.score < 0.4, f"Infeasible hypothesis scored too high: {metric.score}"
