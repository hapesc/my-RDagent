from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from llm.codegen.extractors import extract_code_and_metadata
from llm.codegen.validators import (
    compile_check,
    count_quantitative_claims,
    function_body_nontrivial,
    function_has_return,
    function_uses_parameter,
    has_forbidden_import,
    has_placeholder,
    has_required_signature,
    has_structural_markers,
    hedging_ratio,
)

ArtifactType = Literal["code", "structured_text"]


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    reasons: list[str]
    extracted_code: str | None = None
    metadata: dict[str, object] | None = None


@dataclass
class CodeQualityConfig:
    required_signature: str | None = None
    forbidden_imports: list[str] = field(default_factory=list)
    custom_validators: list[Callable[[str], str | None]] = field(default_factory=list)


@dataclass
class TextQualityConfig:
    min_length_chars: int = 80
    required_structural_markers: list[str] = field(default_factory=lambda: ["##", "1."])
    min_quantitative_claims: int = 1
    max_hedging_ratio: float = 0.3
    custom_validators: list[Callable[[str], str | None]] = field(default_factory=list)


@dataclass
class ScenarioQualityConfig:
    artifact_type: ArtifactType
    code_config: CodeQualityConfig | None = None
    text_config: TextQualityConfig | None = None


_SCENARIO_CONFIGS: dict[str, ScenarioQualityConfig] = {
    "quant": ScenarioQualityConfig(
        artifact_type="code",
        code_config=CodeQualityConfig(
            required_signature="compute_factor",
            forbidden_imports=["os", "subprocess", "requests", "sys"],
            custom_validators=[
                lambda code: (
                    "compute_factor ignores its df parameter"
                    if not function_uses_parameter(code, "compute_factor", "df")
                    else None
                ),
                lambda code: (
                    "compute_factor has no return statement"
                    if not function_has_return(code, "compute_factor")
                    else None
                ),
                lambda code: (
                    "compute_factor body is trivial (pass/return df/...)"
                    if not function_body_nontrivial(code, "compute_factor")
                    else None
                ),
            ],
        ),
    ),
    "data_science": ScenarioQualityConfig(
        artifact_type="code",
        code_config=CodeQualityConfig(forbidden_imports=["subprocess"]),
    ),
    "synthetic_research": ScenarioQualityConfig(
        artifact_type="structured_text",
        text_config=TextQualityConfig(),
    ),
}


class CodegenQualityGate:
    def __init__(self, scenario: str, extra_config: ScenarioQualityConfig | None = None) -> None:
        self._scenario = scenario
        self._config = extra_config or _SCENARIO_CONFIGS[scenario]

    def evaluate(self, raw_output: str) -> QualityResult:
        if self._config.artifact_type == "code":
            return self._evaluate_code(raw_output)
        return self._evaluate_text(raw_output)

    def _evaluate_code(self, raw_output: str) -> QualityResult:
        extracted = extract_code_and_metadata(raw_output)
        code = extracted.code
        reasons: list[str] = []

        if not code.strip():
            reasons.append("no code block extracted")
            return QualityResult(False, reasons, extracted_code=None, metadata=extracted.metadata)
        if not compile_check(code):
            reasons.append("compile check failed")
        if has_placeholder(code):
            reasons.append("placeholder content detected")

        code_config = self._config.code_config or CodeQualityConfig()
        if code_config.forbidden_imports and has_forbidden_import(code, code_config.forbidden_imports):
            reasons.append("forbidden import detected")
        if code_config.required_signature and not has_required_signature(code, code_config.required_signature):
            reasons.append(f"missing required signature: {code_config.required_signature}")
        for validator in code_config.custom_validators:
            reason = validator(code)
            if reason:
                reasons.append(reason)

        return QualityResult(
            passed=not reasons,
            reasons=reasons,
            extracted_code=code,
            metadata=extracted.metadata,
        )

    def _evaluate_text(self, raw_output: str) -> QualityResult:
        extracted = extract_code_and_metadata(raw_output)
        text = (extracted.code or raw_output).strip()
        reasons: list[str] = []
        config = self._config.text_config or TextQualityConfig()

        if not text:
            reasons.append("empty structured text")
            return QualityResult(False, reasons, extracted_code=None)
        if has_placeholder(text):
            reasons.append("placeholder content detected")
        if len(text) < config.min_length_chars:
            reasons.append("structured text too short")
        if not has_structural_markers(text, config.required_structural_markers):
            reasons.append("structured text missing required structure")
        if _looks_like_task_restatement(text):
            reasons.append("structured text is a task restatement without findings")

        quantitative_claims = count_quantitative_claims(text)
        if quantitative_claims < config.min_quantitative_claims:
            reasons.append("structured text lacks quantitative substance")

        if hedging_ratio(text) > config.max_hedging_ratio:
            reasons.append("structured text is too hedging-heavy")

        for validator in config.custom_validators:
            reason = validator(text)
            if reason:
                reasons.append(reason)

        return QualityResult(
            passed=not reasons,
            reasons=reasons,
            extracted_code=text,
            metadata=extracted.metadata or None,
        )


def _looks_like_task_restatement(text: str) -> bool:
    lowered = text.lower()
    if "## task" in lowered:
        return True
    return "the task is to" in lowered and count_quantitative_claims(text) == 0
