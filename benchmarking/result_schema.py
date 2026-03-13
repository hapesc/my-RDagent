from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureBucket(str, Enum):
    INFRA_FAILURE = "infra_failure"
    GENERATION_FAILURE = "generation_failure"
    ARTIFACT_MISSING = "artifact_missing"
    STRUCTURAL_FAILURE = "structural_failure"
    SCENARIO_EVAL_FAILURE = "scenario_eval_failure"
    JUDGE_FAILURE = "judge_failure"
    QUALITY_FAILURE = "quality_failure"
    SUCCESS = "success"


@dataclass
class BenchmarkCaseResult:
    scenario: str
    task_id: str
    profile: str
    agent_status: str
    llm_provider: str
    llm_model: str
    judge_model: str | None
    failure_bucket: FailureBucket
    scenario_score: float | None = None
    scenario_metrics: dict[str, Any] = field(default_factory=dict)
    judge_scores: dict[str, Any] = field(default_factory=dict)
    timing: dict[str, Any] = field(default_factory=dict)
    artifact_refs: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkRunResult:
    run_id: str
    profile: str
    scenario: str
    case_results: list[BenchmarkCaseResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
