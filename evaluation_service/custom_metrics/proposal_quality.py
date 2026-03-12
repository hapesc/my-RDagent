"""G-Eval metrics for proposal/hypothesis quality."""

from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

_SCENARIO_CONSTRAINTS: dict[str, str] = {
    "quant": (
        "The hypothesis must be implementable as a single Python function "
        "using only pandas and numpy. It must operate on OHLCV data "
        "(date, stock_id, open, high, low, close, volume). "
        "No external APIs, no network calls, no subprocess."
    ),
    "data_science": (
        "The hypothesis must be implementable as a self-contained Python script "
        "using scikit-learn and standard libraries. It must load data, train, "
        "and output metrics to metrics.json."
    ),
    "synthetic_research": (
        "The hypothesis must be answerable through analysis and structured writing. No code execution is involved."
    ),
}


def create_specificity_metric(threshold: float = 0.6) -> GEval:
    """G-Eval: is the hypothesis specific enough to code directly?"""
    return GEval(
        name="Hypothesis Specificity",
        criteria="""\
Evaluate whether this hypothesis/proposal is specific enough for a developer \
to implement directly without asking clarifying questions. Score on:
1. CONCRETENESS: Does it name specific methods, algorithms, or transformations? \
   (e.g., "5-day rolling pct_change" vs "some momentum indicator")
2. MEASURABILITY: Does it define what success looks like? \
   (e.g., "Sharpe > 0.5" vs "should perform well")
3. SCOPE: Is it bounded to a single, implementable unit of work?
4. UNAMBIGUITY: Could two developers read this and write the same code?\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )


def create_feasibility_metric(
    scenario: str,
    threshold: float = 0.6,
) -> GEval:
    """G-Eval: is the hypothesis feasible within scenario constraints?"""
    constraints = _SCENARIO_CONSTRAINTS.get(scenario, "No specific constraints.")
    return GEval(
        name=f"Hypothesis Feasibility ({scenario})",
        criteria=f"""\
Evaluate whether this hypothesis is feasible given the scenario constraints:

CONSTRAINTS: {constraints}

Score on:
1. RESOURCE FEASIBILITY: Can it be done with the allowed libraries and data?
2. COMPLEXITY: Is the scope achievable in a single coding iteration?
3. NO IMPOSSIBLE REQUIREMENTS: Does it avoid asking for external data, \
   APIs, or resources that aren't available?
4. TECHNICAL SOUNDNESS: Is the proposed approach technically valid?\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )
