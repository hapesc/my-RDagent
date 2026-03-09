"""Structured LLM output schemas for MVP integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _as_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default


def _as_int_list(value: object) -> list[int]:
    return [item for item in _as_list(value) if isinstance(item, int) and not isinstance(item, bool)]


def _as_str_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


@dataclass
class ProposalDraft:
    summary: str
    constraints: list[str] = field(default_factory=list)
    virtual_score: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProposalDraft:
        return cls(
            summary=str(data.get("summary", "")),
            constraints=[str(item) for item in _as_list(data.get("constraints", []))],
            virtual_score=_as_float(data.get("virtual_score", 0.0), 0.0),
        )


@dataclass
class CodeDraft:
    artifact_id: str
    description: str
    location: str

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CodeDraft:
        return cls(
            artifact_id=str(data.get("artifact_id", "artifact-llm")),
            description=str(data.get("description", "")),
            location=str(data.get("location", "/tmp/rd_agent_workspace")),
        )


@dataclass
class FeedbackDraft:
    decision: bool
    acceptable: bool
    reason: str
    observations: str = ""
    code_change_summary: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FeedbackDraft:
        return cls(
            decision=bool(data.get("decision", False)),
            acceptable=bool(data.get("acceptable", False)),
            reason=str(data.get("reason", "")),
            observations=str(data.get("observations", "")),
            code_change_summary=str(data.get("code_change_summary", "")),
        )


@dataclass
class AnalysisResult:
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    current_performance: str = ""
    key_observations: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AnalysisResult:
        return cls(
            strengths=[str(item) for item in _as_list(data.get("strengths", []))],
            weaknesses=[str(item) for item in _as_list(data.get("weaknesses", []))],
            current_performance=str(data.get("current_performance", "")),
            key_observations=str(data.get("key_observations", "")),
        )


@dataclass
class ProblemIdentification:
    problem: str = ""
    severity: str = ""
    evidence: str = ""
    affected_component: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProblemIdentification:
        return cls(
            problem=str(data.get("problem", "")),
            severity=str(data.get("severity", "")),
            evidence=str(data.get("evidence", "")),
            affected_component=str(data.get("affected_component", "")),
        )


@dataclass
class HypothesisFormulation:
    hypothesis: str = ""
    mechanism: str = ""
    expected_improvement: str = ""
    testable_prediction: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HypothesisFormulation:
        return cls(
            hypothesis=str(data.get("hypothesis", "")),
            mechanism=str(data.get("mechanism", "")),
            expected_improvement=str(data.get("expected_improvement", "")),
            testable_prediction=str(data.get("testable_prediction", "")),
        )


@dataclass
class ExperimentDesign:
    summary: str = ""
    constraints: list[str] = field(default_factory=list)
    virtual_score: float = 0.0
    implementation_steps: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ExperimentDesign:
        return cls(
            summary=str(data.get("summary", "")),
            constraints=[str(item) for item in _as_list(data.get("constraints", []))],
            virtual_score=_as_float(data.get("virtual_score", 0.0), 0.0),
            implementation_steps=[str(item) for item in _as_list(data.get("implementation_steps", []))],
        )


@dataclass
class VirtualEvalResult:
    rankings: list[int] = field(default_factory=list)
    reasoning: str = ""
    selected_indices: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> VirtualEvalResult:
        return cls(
            rankings=_as_int_list(data.get("rankings", [])),
            reasoning=str(data.get("reasoning", "")),
            selected_indices=_as_int_list(data.get("selected_indices", [])),
        )


@dataclass
class PlanningStrategy:
    strategy_name: str = ""
    method_selection: str = ""
    exploration_weight: float = 0.5
    reasoning: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlanningStrategy:
        return cls(
            strategy_name=str(data.get("strategy_name", "")),
            method_selection=str(data.get("method_selection", "")),
            exploration_weight=_as_float(data.get("exploration_weight", 0.5), 0.5),
            reasoning=str(data.get("reasoning", "")),
        )


@dataclass
class HypothesisModification:
    modified_hypothesis: str = ""
    modification_type: str = ""
    source_hypothesis: str = ""
    reasoning: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HypothesisModification:
        return cls(
            modified_hypothesis=str(data.get("modified_hypothesis", "")),
            modification_type=str(data.get("modification_type", "")),
            source_hypothesis=str(data.get("source_hypothesis", "")),
            reasoning=str(data.get("reasoning", "")),
        )


@dataclass
class StructuredFeedback:
    """FC-3 three-dimensional structured feedback (execution + return_checking + code)."""

    execution: str = ""
    return_checking: str | None = None
    code: str = ""
    final_decision: bool | None = None
    reasoning: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StructuredFeedback:
        return cls(
            execution=str(data.get("execution", "")),
            return_checking=(str(data.get("return_checking")) if data.get("return_checking") is not None else None),
            code=str(data.get("code", "")),
            final_decision=(
                bool(data["final_decision"])
                if "final_decision" in data and data["final_decision"] is not None
                else None
            ),
            reasoning=str(data.get("reasoning", "")),
        )


@dataclass
class ReasoningTrace:
    """FC-3 reasoning pipeline trace record."""

    trace_id: str = ""
    stages: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ReasoningTrace:
        return cls(
            trace_id=str(data.get("trace_id", "")),
            stages=_as_str_dict(data.get("stages", {})),
            timestamp=str(data.get("timestamp", "")),
            metadata=_as_str_dict(data.get("metadata", {})),
        )
