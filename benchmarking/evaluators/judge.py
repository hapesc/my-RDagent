"""BYO-LLM judge evaluators for benchmark criteria."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from benchmarking.evaluators.criteria import (
    FEEDBACK_ACTIONABILITY_CRITERIA,
    HYPOTHESIS_SPECIFICITY_CRITERIA,
    REPORT_COHERENCE_CRITERIA,
    REPORT_DEPTH_CRITERIA,
    REPORT_FAITHFULNESS_CRITERIA,
    build_hypothesis_feasibility_criteria,
)


@dataclass(frozen=True)
class JudgeScore:
    score: float
    reasoning: str

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "JudgeScore":
        if "score" not in data:
            raise ValueError("judge payload missing required field: score")
        if "reasoning" not in data:
            raise ValueError("judge payload missing required field: reasoning")
        return cls(
            score=float(data["score"]),
            reasoning=str(data["reasoning"]),
        )


def _build_prompt(*, criteria: str, inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> str:
    return (
        "Evaluate the following benchmark case and return JSON with keys `score` and `reasoning`.\n\n"
        f"CRITERIA:\n{criteria}\n\n"
        f"INPUTS:\n{json.dumps(inputs, ensure_ascii=False, sort_keys=True)}\n\n"
        f"OUTPUTS:\n{json.dumps(outputs, ensure_ascii=False, sort_keys=True)}\n\n"
        f"REFERENCE_OUTPUTS:\n{json.dumps(reference_outputs, ensure_ascii=False, sort_keys=True)}\n"
    )


def _make_judge(llm_adapter: Any, criteria_builder: Callable[[], str]) -> Callable[..., dict[str, Any]]:
    def evaluator(*, inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]) -> dict[str, Any]:
        if not inputs and not outputs and not reference_outputs:
            return {"score": 0.0, "reasoning": "empty benchmark case"}
        prompt = _build_prompt(
            criteria=criteria_builder(),
            inputs=inputs,
            outputs=outputs,
            reference_outputs=reference_outputs,
        )
        result = llm_adapter.generate_structured(prompt, JudgeScore)
        return {"score": result.score, "reasoning": result.reasoning}

    return evaluator


def create_hypothesis_specificity_judge(llm_adapter: Any) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: HYPOTHESIS_SPECIFICITY_CRITERIA)


def create_hypothesis_feasibility_judge(llm_adapter: Any, *, scenario: str | None = None) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: build_hypothesis_feasibility_criteria(scenario))


def create_feedback_actionability_judge(llm_adapter: Any) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: FEEDBACK_ACTIONABILITY_CRITERIA)


def create_report_depth_judge(llm_adapter: Any) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: REPORT_DEPTH_CRITERIA)


def create_report_coherence_judge(llm_adapter: Any) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: REPORT_COHERENCE_CRITERIA)


def create_report_faithfulness_judge(llm_adapter: Any) -> Callable[..., dict[str, Any]]:
    return _make_judge(llm_adapter, lambda: REPORT_FAITHFULNESS_CRITERIA)
