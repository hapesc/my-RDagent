"""Migrated evaluation criteria text for benchmark judge evaluators."""

from __future__ import annotations

_SCENARIO_CONSTRAINTS: dict[str, str] = {
    "quant": (
        "The hypothesis must be implementable as a single Python function using only pandas and numpy, "
        "operating on OHLCV data without external APIs, network calls, or subprocess usage."
    ),
    "data_science": (
        "The hypothesis must be implementable as a self-contained Python script using scikit-learn and "
        "standard libraries, loading data, training, and writing metrics to metrics.json."
    ),
    "synthetic_research": (
        "The hypothesis must be answerable through analysis and structured writing without code execution."
    ),
}


HYPOTHESIS_SPECIFICITY_CRITERIA = """\
Evaluate whether this hypothesis/proposal is specific enough for a developer \
to implement directly without asking clarifying questions. Score on:
1. CONCRETENESS: Does it name specific methods, algorithms, or transformations? \
   (e.g., "5-day rolling pct_change" vs "some momentum indicator")
2. MEASURABILITY: Does it define what success looks like? \
   (e.g., "Sharpe > 0.5" vs "should perform well")
3. SCOPE: Is it bounded to a single, implementable unit of work?
4. UNAMBIGUITY: Could two developers read this and write the same code?\
"""


HYPOTHESIS_FEASIBILITY_CRITERIA = """\
Evaluate whether this hypothesis is feasible given the scenario constraints.

Score on:
1. RESOURCE FEASIBILITY: Can it be done with the allowed libraries and data?
2. COMPLEXITY: Is the scope achievable in a single coding iteration?
3. NO IMPOSSIBLE REQUIREMENTS: Does it avoid asking for external data, \
   APIs, or resources that are not available?
4. TECHNICAL SOUNDNESS: Is the proposed approach technically valid?\
"""


FEEDBACK_ACTIONABILITY_CRITERIA = """\
Evaluate whether this code feedback is actionable — meaning a developer \
could read it and know exactly what to change. Score on:
1. SPECIFICITY: Does it identify the exact lines/functions that are wrong?
2. ROOT CAUSE: Does it explain WHY the code fails, not just THAT it fails?
3. FIX SUGGESTION: Does it suggest a concrete code change?
4. CLARITY: Is it written in clear, unambiguous language?
A feedback that just says "code failed" or "try again" scores 0.\
"""


REPORT_DEPTH_CRITERIA = """\
Evaluate the analytical depth of this research report. Score on:
1. EVIDENCE: Does it cite specific numbers, measurements, or data points? \
   (e.g., "accuracy improved by 12%" vs "accuracy improved")
2. CAUSAL REASONING: Does it explain WHY results occur, not just WHAT happens?
3. COMPARATIVE ANALYSIS: Does it compare approaches with specific trade-offs?
4. NUANCE: Does it acknowledge limitations, edge cases, or conditions \
   where conclusions might not hold?
A report that merely restates the task or gives generic summaries scores 0.\
"""


REPORT_COHERENCE_CRITERIA = """\
Evaluate the logical coherence of this research report. Score on:
1. FLOW: Do paragraphs follow a logical progression? \
   (findings -> methodology -> conclusion)
2. CONSISTENCY: Are claims in one section consistent with claims in another?
3. TRANSITIONS: Are section transitions smooth, not abrupt?
4. COMPLETENESS: Does the conclusion follow from the findings presented?\
"""


REPORT_FAITHFULNESS_CRITERIA = """\
Evaluate whether this research report is faithful to the original task and bounded by the provided evidence. \
Score on:
1. TASK ALIGNMENT: Does it address the specific question asked?
2. EVIDENCE BOUNDING: Are claims bounded by the provided evidence and reference facts, \
   rather than invented unsupported details?
3. NO FABRICATION: Does it avoid invented studies, impossible numbers, or reference facts \
   that are not supported by the available context?
4. SCOPE ADHERENCE: Does it stay focused on the requested topic without irrelevant tangents?
5. TOPIC COVERAGE: If reference topics or reference facts were provided, are they adequately addressed?\
"""


def build_hypothesis_feasibility_criteria(scenario: str | None = None) -> str:
    constraints = _SCENARIO_CONSTRAINTS.get(scenario or "", "No additional scenario-specific constraints.")
    return f"{HYPOTHESIS_FEASIBILITY_CRITERIA}\n\nSCENARIO CONSTRAINTS: {constraints}"
