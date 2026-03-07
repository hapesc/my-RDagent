"""Structured LLM output schemas for MVP integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ProposalDraft:
    summary: str
    constraints: List[str] = field(default_factory=list)
    virtual_score: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ProposalDraft":
        return cls(
            summary=str(data.get("summary", "")),
            constraints=[str(item) for item in data.get("constraints", [])],
            virtual_score=float(data.get("virtual_score", 0.0)),
        )


@dataclass
class CodeDraft:
    artifact_id: str
    description: str
    location: str

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "CodeDraft":
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
    def from_dict(cls, data: Dict[str, object]) -> "FeedbackDraft":
        return cls(
            decision=bool(data.get("decision", False)),
            acceptable=bool(data.get("acceptable", False)),
            reason=str(data.get("reason", "")),
            observations=str(data.get("observations", "")),
            code_change_summary=str(data.get("code_change_summary", "")),
        )


@dataclass
class AnalysisResult:
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    current_performance: str = ""
    key_observations: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "AnalysisResult":
        return cls(
            strengths=[str(item) for item in data.get("strengths", [])],
            weaknesses=[str(item) for item in data.get("weaknesses", [])],
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
    def from_dict(cls, data: Dict[str, object]) -> "ProblemIdentification":
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
    def from_dict(cls, data: Dict[str, object]) -> "HypothesisFormulation":
        return cls(
            hypothesis=str(data.get("hypothesis", "")),
            mechanism=str(data.get("mechanism", "")),
            expected_improvement=str(data.get("expected_improvement", "")),
            testable_prediction=str(data.get("testable_prediction", "")),
        )


@dataclass
class ExperimentDesign:
    summary: str = ""
    constraints: List[str] = field(default_factory=list)
    virtual_score: float = 0.0
    implementation_steps: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ExperimentDesign":
        return cls(
            summary=str(data.get("summary", "")),
            constraints=[str(item) for item in data.get("constraints", [])],
            virtual_score=float(data.get("virtual_score", 0.0)),
            implementation_steps=[str(item) for item in data.get("implementation_steps", [])],
        )


@dataclass
class VirtualEvalResult:
    rankings: List[int] = field(default_factory=list)
    reasoning: str = ""
    selected_indices: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "VirtualEvalResult":
        return cls(
            rankings=[int(item) for item in data.get("rankings", [])],
            reasoning=str(data.get("reasoning", "")),
            selected_indices=[int(item) for item in data.get("selected_indices", [])],
        )
