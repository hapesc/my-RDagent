"""Bridge between RDAgent artifacts and DeepEval test cases."""

from __future__ import annotations

import json
from typing import Any

from deepeval.test_case import LLMTestCase


def golden_task_to_test_case(
    task: dict[str, Any],
    actual_output: str,
) -> LLMTestCase:
    """Convert a golden task JSON + generated artifact into a DeepEval test case."""
    return LLMTestCase(
        input=str(task["task_summary"]),
        actual_output=actual_output,
        context=[json.dumps(task.get("expected_properties", {}))],
    )


def proposal_to_test_case(
    task_summary: str,
    hypothesis_text: str,
    previous_hypotheses: list[str] | None = None,
) -> LLMTestCase:
    """Convert a proposal/hypothesis into a DeepEval test case."""
    context = previous_hypotheses or []
    return LLMTestCase(
        input=task_summary,
        actual_output=hypothesis_text,
        context=context,
    )


def report_to_test_case(
    task_summary: str,
    report_text: str,
    reference_topics: list[str] | None = None,
) -> LLMTestCase:
    """Convert a synthetic research report into a DeepEval test case."""
    context = reference_topics or []
    return LLMTestCase(
        input=task_summary,
        actual_output=report_text,
        context=context,
    )


def costeer_round_to_test_case(
    task_summary: str,
    code_at_round: str,
    feedback_text: str,
    round_index: int,
) -> LLMTestCase:
    """Convert a single CoSTEER round's output into a DeepEval test case."""
    return LLMTestCase(
        input=task_summary,
        actual_output=code_at_round,
        context=[f"Round {round_index} feedback: {feedback_text}"],
    )
