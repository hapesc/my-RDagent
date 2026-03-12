"""G-Eval metrics for synthetic research report quality."""

from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_report_depth_metric(threshold: float = 0.6) -> GEval:
    """G-Eval: does the report have analytical depth?"""
    return GEval(
        name="Report Depth",
        criteria="""\
Evaluate the analytical depth of this research report. Score on:
1. EVIDENCE: Does it cite specific numbers, measurements, or data points? \
   (e.g., "accuracy improved by 12%" vs "accuracy improved")
2. CAUSAL REASONING: Does it explain WHY results occur, not just WHAT happens?
3. COMPARATIVE ANALYSIS: Does it compare approaches with specific trade-offs?
4. NUANCE: Does it acknowledge limitations, edge cases, or conditions \
   where conclusions might not hold?
A report that merely restates the task or gives generic summaries scores 0.\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )


def create_report_coherence_metric(threshold: float = 0.6) -> GEval:
    """G-Eval: is the report logically coherent?"""
    return GEval(
        name="Report Coherence",
        criteria="""\
Evaluate the logical coherence of this research report. Score on:
1. FLOW: Do paragraphs follow a logical progression? \
   (findings → methodology → conclusion)
2. CONSISTENCY: Are claims in one section consistent with claims in another?
3. TRANSITIONS: Are section transitions smooth, not abrupt?
4. COMPLETENESS: Does the conclusion follow from the findings presented?\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )


def create_report_faithfulness_metric(threshold: float = 0.6) -> GEval:
    """G-Eval: is the report faithful to the task and reference topics?"""
    return GEval(
        name="Report Faithfulness",
        criteria="""\
Evaluate whether this research report is faithful to the original task. \
Score on:
1. TASK ALIGNMENT: Does it address the specific question asked?
2. NO FABRICATION: Are the claims plausible and internally consistent? \
   (Exact factual verification is not possible, but obvious fabrications \
   like citing non-existent studies or impossible numbers should be penalized)
3. SCOPE ADHERENCE: Does it stay focused on the requested topic \
   without irrelevant tangents?
4. TOPIC COVERAGE: If reference topics were given (in context), \
   are they adequately addressed?\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=threshold,
    )
