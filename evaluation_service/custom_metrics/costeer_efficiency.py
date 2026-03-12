"""CoSTEER self-correction effectiveness metrics."""

from __future__ import annotations

from dataclasses import dataclass

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


@dataclass(frozen=True)
class CoSTEERRound:
    round_index: int
    code: str
    feedback: str
    accepted: bool
    score: float  # 0.0-1.0 from G-Eval or structural checks


@dataclass(frozen=True)
class CoSTEERTrace:
    task_summary: str
    rounds: list[CoSTEERRound]


@dataclass(frozen=True)
class CoSTEEREfficiencyResult:
    total_rounds: int
    converged: bool
    rounds_to_converge: int | None
    regression_count: int
    score_deltas: list[float]
    final_score: float


def compute_costeer_efficiency(trace: CoSTEERTrace) -> CoSTEEREfficiencyResult:
    """Compute efficiency metrics from a CoSTEER trace.

    Measures: convergence, regression count, round-over-round deltas.
    """
    rounds = trace.rounds
    if not rounds:
        return CoSTEEREfficiencyResult(
            total_rounds=0,
            converged=False,
            rounds_to_converge=None,
            regression_count=0,
            score_deltas=[],
            final_score=0.0,
        )

    deltas: list[float] = []
    regression_count = 0
    rounds_to_converge: int | None = None

    for i in range(1, len(rounds)):
        delta = rounds[i].score - rounds[i - 1].score
        deltas.append(delta)
        if delta < 0:
            regression_count += 1

    converged = any(r.accepted for r in rounds)
    if converged:
        for r in rounds:
            if r.accepted:
                rounds_to_converge = r.round_index + 1
                break

    return CoSTEEREfficiencyResult(
        total_rounds=len(rounds),
        converged=converged,
        rounds_to_converge=rounds_to_converge,
        regression_count=regression_count,
        score_deltas=deltas,
        final_score=rounds[-1].score,
    )


def create_feedback_actionability_metric(threshold: float = 0.6) -> GEval:
    """G-Eval: is the CoSTEER feedback actionable?"""
    return GEval(
        name="Feedback Actionability",
        criteria="""\
Evaluate whether this code feedback is actionable — meaning a developer \
could read it and know exactly what to change. Score on:
1. SPECIFICITY: Does it identify the exact lines/functions that are wrong?
2. ROOT CAUSE: Does it explain WHY the code fails, not just THAT it fails?
3. FIX SUGGESTION: Does it suggest a concrete code change?
4. CLARITY: Is it written in clear, unambiguous language?
A feedback that just says "code failed" or "try again" scores 0.\
""",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=threshold,
    )
