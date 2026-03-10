"""Plugin contracts for scenario-extensible loop execution."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from data_models import (
    ArtifactVerificationStatus,
    CodeArtifact,
    ContextPack,
    ExecutionOutcomeContract,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    ProcessExecutionStatus,
    Proposal,
    RunSession,
    Score,
    UsefulnessEligibilityStatus,
)
from service_contracts import StepOverrideConfig


@dataclass
class ScenarioContext:
    """Scenario-scoped runtime context."""

    run_id: str
    scenario_name: str
    input_payload: dict[str, Any]
    config: dict[str, Any] = field(default_factory=dict)
    task_summary: str = ""
    step_config: StepOverrideConfig = field(default_factory=StepOverrideConfig)


@runtime_checkable
class ScenarioPlugin(Protocol):
    """Builds scenario context from run metadata and input payload."""

    def build_context(self, run_session: RunSession, input_payload: dict[str, Any]) -> ScenarioContext: ...


@runtime_checkable
class ProposalEngine(Protocol):
    """Generates proposals from loop state and memory context."""

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: list[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal: ...


@runtime_checkable
class ExperimentGenerator(Protocol):
    """Converts proposal output into an executable experiment node."""

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: list[str],
    ) -> ExperimentNode: ...


@runtime_checkable
class Coder(Protocol):
    """Turns experiment definition into runnable code artifact."""

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact: ...


@runtime_checkable
class Runner(Protocol):
    """Executes a code artifact and returns runtime result."""

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult: ...


@runtime_checkable
class FeedbackAnalyzer(Protocol):
    """Summarizes run outputs into a normalized feedback record."""

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Score | None = None,
    ) -> FeedbackRecord: ...


@dataclass
class UsefulnessGateSignal:
    eligible: bool
    stage: str
    reason: str


@dataclass
class UsefulnessGateInput:
    scenario: ScenarioContext
    result: ExecutionResult
    artifact_paths: list[str]
    artifact_texts: dict[str, str]
    normalized_text: str
    structured_payload: dict[str, Any] | None = None


SceneUsefulnessValidator = Callable[[UsefulnessGateInput], str | None]


class CommonUsefulnessGate:
    _PLACEHOLDER_TOKENS = (
        "todo",
        "tbd",
        "lorem ipsum",
        "placeholder",
        "fill in",
        "insert here",
        "{{",
        "}}",
    )
    _POSITIVE_STATUS = ("ok", "success", "completed", "done")
    _NEGATIVE_STATUS = ("error", "failed", "failure", "exception", "traceback", "timeout")
    _NON_INFORMATIVE_KEYS = {
        "status",
        "result",
        "outcome",
        "message",
        "ok",
        "success",
        "state",
        "detail",
    }

    def evaluate(
        self,
        result: ExecutionResult,
        scenario: ScenarioContext,
        scene_validator: SceneUsefulnessValidator | None = None,
    ) -> tuple[ExecutionOutcomeContract, UsefulnessGateSignal]:
        outcome = result.resolve_outcome()
        if outcome.process_status != ProcessExecutionStatus.SUCCESS:
            outcome.usefulness_status = UsefulnessEligibilityStatus.INELIGIBLE
            result.outcome = outcome
            return outcome, UsefulnessGateSignal(
                eligible=False,
                stage="syntax",
                reason="process did not succeed",
            )

        if outcome.artifact_status != ArtifactVerificationStatus.VERIFIED:
            outcome.usefulness_status = UsefulnessEligibilityStatus.INELIGIBLE
            result.outcome = outcome
            return outcome, UsefulnessGateSignal(
                eligible=False,
                stage="semantic",
                reason=f"artifact verification failed: {outcome.artifact_status.value}",
            )

        artifact_paths = self._decode_artifact_paths(result.artifacts_ref)
        artifact_texts = self._load_artifact_texts(artifact_paths)
        normalized_text = self._normalize_text(result.logs_ref, list(artifact_texts.values()))
        gate_input = UsefulnessGateInput(
            scenario=scenario,
            result=result,
            artifact_paths=artifact_paths,
            artifact_texts=artifact_texts,
            normalized_text=normalized_text,
            structured_payload=self._extract_payload(result.logs_ref, artifact_texts),
        )

        semantic_reject = self._semantic_rejection(gate_input)
        if semantic_reject is not None:
            outcome.usefulness_status = UsefulnessEligibilityStatus.INELIGIBLE
            if not artifact_paths:
                outcome.artifact_status = ArtifactVerificationStatus.MISSING_REQUIRED
            result.outcome = outcome
            return outcome, UsefulnessGateSignal(eligible=False, stage="semantic", reason=semantic_reject)

        utility_reject = self._utility_rejection(gate_input)
        if utility_reject is not None:
            outcome.usefulness_status = UsefulnessEligibilityStatus.INELIGIBLE
            result.outcome = outcome
            return outcome, UsefulnessGateSignal(eligible=False, stage="utility", reason=utility_reject)

        if scene_validator is not None:
            scene_reason = scene_validator(gate_input)
            if isinstance(scene_reason, str) and scene_reason.strip():
                outcome.usefulness_status = UsefulnessEligibilityStatus.INELIGIBLE
                result.outcome = outcome
                return outcome, UsefulnessGateSignal(
                    eligible=False,
                    stage="utility",
                    reason=f"scene validator rejected: {scene_reason.strip()}",
                )

        outcome.usefulness_status = UsefulnessEligibilityStatus.ELIGIBLE
        result.outcome = outcome
        return outcome, UsefulnessGateSignal(eligible=True, stage="utility", reason="eligible")

    def _semantic_rejection(self, gate_input: UsefulnessGateInput) -> str | None:
        if not gate_input.artifact_paths:
            return "missing required artifact"
        if not gate_input.normalized_text.strip():
            return "empty output"
        if self._is_template_only(gate_input.normalized_text):
            return "template-only output"
        return None

    def _utility_rejection(self, gate_input: UsefulnessGateInput) -> str | None:
        payload = gate_input.structured_payload
        if isinstance(payload, dict):
            has_status = any(key.lower() in {"status", "result", "outcome", "success"} for key in payload)
            informative_keys = [
                key for key in payload if key.lower() not in self._NON_INFORMATIVE_KEYS and payload[key] is not None
            ]
            if has_status and not informative_keys:
                return "missing key field"
            if self._is_contradictory_status(payload):
                return "contradictory status"
            return None

        if self._contains_contradictory_status_terms(gate_input.normalized_text):
            return "contradictory status"
        return None

    def _decode_artifact_paths(self, artifacts_ref: str) -> list[str]:
        value = (artifacts_ref or "").strip()
        if not value:
            return []
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]

        if isinstance(decoded, list):
            return [str(item) for item in decoded if str(item).strip()]
        if isinstance(decoded, dict):
            return [str(item) for item in decoded.values() if str(item).strip()]
        if isinstance(decoded, str):
            return [decoded] if decoded.strip() else []
        return []

    def _load_artifact_texts(self, artifact_paths: list[str]) -> dict[str, str]:
        texts: dict[str, str] = {}
        for raw_path in artifact_paths:
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if content.strip():
                texts[str(path)] = content[:4000]
        return texts

    def _normalize_text(self, logs_ref: str, artifact_texts: Sequence[str]) -> str:
        chunks = [logs_ref or ""]
        chunks.extend(artifact_texts)
        normalized = "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())
        return normalized.lower()

    def _extract_payload(self, logs_ref: str, artifact_texts: dict[str, str]) -> dict[str, Any] | None:
        for content in artifact_texts.values():
            payload = self._parse_first_json_object(content)
            if payload is not None:
                return payload
        return self._parse_first_json_object(logs_ref)

    def _parse_first_json_object(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None
        stripped = text.strip()
        try:
            decoded = json.loads(stripped)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass

        for line in stripped.splitlines():
            line = line.strip()
            if not (line.startswith("{") and line.endswith("}")):
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
        return None

    def _is_template_only(self, normalized_text: str) -> bool:
        if not normalized_text.strip():
            return True
        return any(token in normalized_text for token in self._PLACEHOLDER_TOKENS)

    def _is_contradictory_status(self, payload: dict[str, Any]) -> bool:
        status_value = str(payload.get("status", payload.get("result", payload.get("outcome", "")))).lower()
        if not status_value:
            return False
        has_positive = any(token in status_value for token in self._POSITIVE_STATUS)
        has_negative = any(token in status_value for token in self._NEGATIVE_STATUS)
        return has_positive and has_negative

    def _contains_contradictory_status_terms(self, normalized_text: str) -> bool:
        has_positive = any(token in normalized_text for token in self._POSITIVE_STATUS)
        has_negative = any(token in normalized_text for token in self._NEGATIVE_STATUS)
        return has_positive and has_negative


@dataclass
class PluginBundle:
    """Complete plugin bundle required by the loop engine."""

    scenario_name: str
    scenario_plugin: ScenarioPlugin
    proposal_engine: ProposalEngine
    experiment_generator: ExperimentGenerator
    coder: Coder
    runner: Runner
    feedback_analyzer: FeedbackAnalyzer
    scene_usefulness_validator: SceneUsefulnessValidator | None = None
    default_step_overrides: StepOverrideConfig = field(default_factory=StepOverrideConfig)
