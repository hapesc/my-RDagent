"""G-Eval based code correctness metric for RDAgent scenarios."""

from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

_QUANT_CRITERIA = """\
Evaluate whether the generated Python code correctly implements the requested \
quantitative factor. Score on these dimensions:
1. FUNCTIONAL CORRECTNESS: Does the code implement the described logic? \
   (e.g., 5-day momentum should use pct_change or shift with period=5)
2. API USAGE: Are pandas/numpy APIs used correctly? \
   (correct parameters, correct return types, proper groupby usage)
3. EDGE CASES: Does it handle NaN from rolling/pct_change? \
   Does it avoid look-ahead bias (no shift(-n))?
4. OUTPUT CONTRACT: Does it return a DataFrame with exactly \
   (date, stock_id, factor_value)?
5. CLEANLINESS: No placeholder text, no dead code, no print statements.\
"""

_DATA_SCIENCE_CRITERIA = """\
Evaluate whether the generated Python script correctly implements the \
requested data science pipeline. Score on these dimensions:
1. FUNCTIONAL CORRECTNESS: Does the code implement the described task? \
   (e.g., classification should train a model and compute metrics)
2. COMPLETENESS: Is it self-contained? Does it load data, train, and evaluate?
3. METRIC OUTPUT: Does it write results to metrics.json as required?
4. LIBRARY USAGE: Are sklearn/pandas APIs used correctly?
5. CLEANLINESS: No placeholder text, no hardcoded fake metrics.\
"""

_SCENARIO_CRITERIA: dict[str, str] = {
    "quant": _QUANT_CRITERIA,
    "data_science": _DATA_SCIENCE_CRITERIA,
}


def create_code_correctness_metric(
    scenario: str,
    threshold: float = 0.7,
) -> GEval:
    """Create a G-Eval metric for code correctness, scenario-aware."""
    criteria = _SCENARIO_CRITERIA.get(scenario, _DATA_SCIENCE_CRITERIA)
    return GEval(
        name=f"Code Correctness ({scenario})",
        criteria=criteria,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )
