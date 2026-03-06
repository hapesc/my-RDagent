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
