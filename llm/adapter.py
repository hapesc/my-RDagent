"""LLM adapter with provider abstraction and structured output retries."""

from __future__ import annotations

import dataclasses
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, cast, get_args, get_origin

from service_contracts import ModelSelectorConfig

T = TypeVar("T")

_JSON_BLOCK_RE = re.compile(r"```(?:json)?[ \t]*\n(.*?)```", re.DOTALL)
_JSON_BLOCK_UNCLOSED_RE = re.compile(r"```(?:json)?[ \t]*\n(.*)", re.DOTALL)
_CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_-]*)\s*\n?(.*?)```", re.DOTALL)
_log = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Provider interface for text completion."""

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str: ...


class MockLLMProvider:
    """Deterministic mock provider for testing structured outputs."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])

    @staticmethod
    def _extract_section(prompt: str, legacy_prefix: str, section_header: str) -> str:
        if legacy_prefix and legacy_prefix in prompt:
            return prompt.split(legacy_prefix, 1)[1].split("\n")[0].strip()
        if section_header in prompt:
            after = prompt.split(section_header, 1)[1]
            return after.split("\n")[0].strip()
        return ""

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        def _metadata_tokens() -> list[str]:
            if model_config is None:
                return []
            tokens: list[str] = []
            if model_config.provider:
                tokens.append(f"provider:{model_config.provider}")
            if model_config.model:
                tokens.append(f"model:{model_config.model}")
            if model_config.temperature is not None:
                tokens.append(f"temperature:{model_config.temperature}")
            if model_config.max_tokens is not None:
                tokens.append(f"max_tokens:{model_config.max_tokens}")
            return tokens

        if self._responses:
            return self._responses.pop(0)

        prompt_lower = prompt.lower()
        is_merge = "research synthesizer" in prompt_lower or "completed traces" in prompt_lower
        if is_merge:
            return json.dumps(
                {
                    "summary": "Merged experiment design",
                    "constraints": ["merged-constraint-1", "merged-constraint-2"],
                    "virtual_score": 0.8,
                    "implementation_steps": ["merged step 1", "merged step 2"],
                }
            )

        is_proposal = "proposal:" in prompt or "`virtual_score`" in prompt
        is_coding = "coding:" in prompt or "`artifact_id`" in prompt
        is_feedback = "feedback:" in prompt or "`acceptable`" in prompt

        if is_proposal:
            summary = self._extract_section(prompt, "proposal:", "## Task\n") or "mock-proposal"
            constraints = ["llm-structured"] + _metadata_tokens()
            return json.dumps(
                {
                    "summary": summary,
                    "constraints": constraints,
                    "virtual_score": 0.5,
                }
            )
        if is_coding:
            summary = self._extract_section(prompt, "coding:", "## Research Proposal\n") or "mock-code"
            suffix = ""
            if model_config is not None and model_config.model:
                suffix = f" [model={model_config.model}]"
            return json.dumps(
                {
                    "artifact_id": "artifact-llm",
                    "description": f"{summary}{suffix}",
                    "location": "/tmp/rd_agent_workspace",
                }
            )
        if is_feedback:
            hypothesis = self._extract_section(prompt, "feedback:", "- Hypothesis: ")
            execution = self._extract_section(prompt, "", "- Execution: ")
            score = self._extract_section(prompt, "", "- Score: ")
            parts = [p for p in [hypothesis, execution, score] if p]
            reason = "; ".join(parts) if parts else "mock-feedback"
            if model_config is not None and model_config.model:
                reason = f"{reason};model={model_config.model}"
            return json.dumps(
                {
                    "decision": True,
                    "acceptable": True,
                    "reason": reason,
                    "observations": "llm-observation",
                    "code_change_summary": "llm-summary",
                }
            )

        # FC-3 Structured Feedback
        is_structured_feedback = "structured feedback" in prompt_lower or (
            "`execution`" in prompt and "`code`" in prompt and "`reasoning`" in prompt
        )
        if is_structured_feedback:
            return json.dumps(
                {
                    "execution": "Mock execution status: passed",
                    "return_checking": "Mock return check: values consistent",
                    "code": "Mock code review: clean implementation",
                    "final_decision": True,
                    "reasoning": "Mock reasoning: all checks passed",
                }
            )

        # FC-3 Reasoning Stages (check more specific patterns first)
        is_analysis = "`strengths`" in prompt or "`weaknesses`" in prompt
        if is_analysis:
            return json.dumps(
                {
                    "strengths": ["Mock strength 1", "Mock strength 2"],
                    "weaknesses": ["Mock weakness 1"],
                    "current_performance": "Mock analysis",
                    "key_observations": "Mock observation",
                }
            )

        is_problem = "`severity`" in prompt or "`affected_component`" in prompt
        if is_problem:
            return json.dumps(
                {
                    "problem": "Mock problem identified",
                    "severity": "High",
                    "evidence": "Mock evidence",
                    "affected_component": "Mock component",
                }
            )

        is_hypothesis = "`mechanism`" in prompt or "`testable_prediction`" in prompt
        if is_hypothesis:
            return json.dumps(
                {
                    "hypothesis": "Mock hypothesis",
                    "mechanism": "Mock mechanism",
                    "expected_improvement": "Mock improvement",
                    "testable_prediction": "Mock prediction",
                }
            )

        # FC-1 Planning Strategy
        is_planning = "`strategy_name`" in prompt and "`method_selection`" in prompt
        if is_planning:
            return json.dumps(
                {
                    "strategy_name": "balanced_exploration",
                    "method_selection": "targeted_improvement",
                    "exploration_weight": 0.6,
                    "reasoning": "Mock planning strategy based on current progress",
                }
            )

        # FC-4 Hypothesis Modification
        is_hyp_mod = "`modified_hypothesis`" in prompt and "`modification_type`" in prompt
        if is_hyp_mod:
            return json.dumps(
                {
                    "modified_hypothesis": "Mock modified hypothesis",
                    "modification_type": "modify",
                    "source_hypothesis": "Mock source hypothesis",
                    "reasoning": "Mock modification reasoning",
                }
            )

        is_experiment = "`implementation_steps`" in prompt
        if is_experiment:
            return json.dumps(
                {
                    "summary": "Mock experiment design",
                    "constraints": ["constraint-1", "constraint-2"],
                    "virtual_score": 0.7,
                    "implementation_steps": ["step 1", "step 2", "step 3"],
                }
            )

        is_virtual_eval = "`rankings`" in prompt or "`selected_indices`" in prompt
        if is_virtual_eval:
            candidates = 5
            if "candidate" in prompt_lower:
                match = re.search(r"(\d+)\s*candidate", prompt_lower)
                if match:
                    candidates = int(match.group(1))
            rankings = list(range(candidates))
            selected_count = max(1, candidates // 2)
            selected_indices = list(range(selected_count))
            return json.dumps(
                {
                    "rankings": rankings,
                    "reasoning": "Mock ranking strategy",
                    "selected_indices": selected_indices,
                }
            )

        return json.dumps({"message": "ok"})


@dataclass
class LLMAdapterConfig:
    """Adapter configuration."""

    max_retries: int = 2


@dataclass(frozen=True)
class ParseDiagnostic:
    attempt: int
    stage: str
    retryable: bool
    error: str


class StructuredOutputParseError(ValueError):
    def __init__(self, message: str, diagnostics: list[ParseDiagnostic]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics
        self.retry_count = max(0, len(diagnostics) - 1)
        self.failure_counts = dict(Counter(diagnostic.stage for diagnostic in diagnostics))
        self.failure_stages = tuple(diagnostic.stage for diagnostic in diagnostics)


class LLMAdapter:
    """Adapter that parses structured JSON outputs with retries."""

    def __init__(self, provider: LLMProvider, config: LLMAdapterConfig | None = None) -> None:
        self._provider = provider
        self._config = config or LLMAdapterConfig()

    def _build_schema_hint(self, schema_cls: type) -> str:
        """Build JSON schema hint from a dataclass with from_dict."""
        if not dataclasses.is_dataclass(schema_cls):
            return ""
        example: dict = {}
        for f in dataclasses.fields(schema_cls):
            ann = str(f.type)
            if ann in ("str", "<class 'str'>"):
                example[f.name] = "string"
            elif ann in ("float", "<class 'float'>"):
                example[f.name] = 0.0
            elif ann in ("bool", "<class 'bool'>"):
                example[f.name] = True
            elif "List[str]" in ann or "list[str]" in ann:
                example[f.name] = ["string"]
            elif "List[int]" in ann or "list[int]" in ann:
                example[f.name] = [0]
            elif "List[float]" in ann or "list[float]" in ann:
                example[f.name] = [0.0]
            else:
                example[f.name] = "value"
        return json.dumps(example, indent=2)

    def _enhance_prompt(self, prompt: str, schema_cls: type) -> str:
        schema_hint = self._build_schema_hint(schema_cls)
        if not schema_hint:
            return prompt
        return (
            f"{prompt}\n\n"
            f"--- OUTPUT FORMAT ---\n"
            f"Respond with a single raw JSON object. "
            f"Do NOT wrap in ```json``` or any markdown. "
            f"Do NOT include explanation before or after the JSON.\n"
            f"Schema:\n{schema_hint}"
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown code fences if present, including unclosed fences (truncated output)."""
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            return match.group(1).strip()
        # Handle unclosed fence (e.g. output truncated before closing ```)
        if raw.count("```") == 1:
            match = _JSON_BLOCK_UNCLOSED_RE.search(raw)
            if match:
                return match.group(1).strip()
        decoder = json.JSONDecoder()
        for idx, char in enumerate(raw):
            if char != "{":
                continue
            try:
                payload, end = decoder.raw_decode(raw[idx:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return raw[idx : idx + end].strip()
        return raw.strip()

    @staticmethod
    def _extract_code(raw: str) -> str:
        matches = list(_CODE_BLOCK_RE.finditer(raw))
        if not matches:
            return ""

        for match in matches:
            lang = (match.group(1) or "").strip().lower()
            if lang != "json":
                return match.group(2).strip()
        return matches[-1].group(2).strip()

    @staticmethod
    def _repair_json(raw: str) -> str:
        repaired = raw.strip()
        if not repaired:
            return repaired

        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        open_braces = repaired.count("{")
        close_braces = repaired.count("}")
        if close_braces < open_braces:
            repaired = repaired + ("}" * (open_braces - close_braces))

        open_brackets = repaired.count("[")
        close_brackets = repaired.count("]")
        if close_brackets < open_brackets:
            repaired = repaired + ("]" * (open_brackets - close_brackets))
        return repaired

    @staticmethod
    def _is_optional_field(field_type: Any) -> bool:
        origin = get_origin(field_type)
        if origin is None:
            return False
        args = get_args(field_type)
        return type(None) in args

    def _validate_required_fields(self, schema_cls: type, payload: dict[str, Any]) -> None:
        if not dataclasses.is_dataclass(schema_cls):
            return

        missing: list[str] = []
        null_fields: list[str] = []
        for field in dataclasses.fields(schema_cls):
            if self._is_optional_field(field.type):
                continue
            if field.name not in payload:
                missing.append(field.name)
                continue
            if payload[field.name] is None:
                null_fields.append(field.name)

        if missing or null_fields:
            parts: list[str] = []
            if missing:
                parts.append(f"missing={missing}")
            if null_fields:
                parts.append(f"null={null_fields}")
            raise ValueError("required fields validation failed: " + ", ".join(parts))

    @staticmethod
    def _is_valid_scalar_type(expected: str, value: Any) -> bool:
        if expected in ("str", "<class 'str'>"):
            return isinstance(value, str)
        if expected in ("float", "<class 'float'>"):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected in ("bool", "<class 'bool'>"):
            return isinstance(value, bool)
        return True

    @staticmethod
    def _is_valid_list_type(expected: str, value: Any) -> bool:
        if "List[str]" in expected or "list[str]" in expected:
            return isinstance(value, list) and all(isinstance(item, str) for item in value)
        if "List[int]" in expected or "list[int]" in expected:
            return isinstance(value, list) and all(
                isinstance(item, int) and not isinstance(item, bool) for item in value
            )
        if "List[float]" in expected or "list[float]" in expected:
            return isinstance(value, list) and all(
                isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
            )
        return True

    def _validate_field_types(self, schema_cls: type, payload: dict[str, Any]) -> None:
        if not dataclasses.is_dataclass(schema_cls):
            return

        mismatches: list[str] = []
        for field in dataclasses.fields(schema_cls):
            if field.name not in payload:
                continue
            value = payload[field.name]
            if value is None:
                continue

            field_type = str(field.type)
            if self._is_optional_field(field.type):
                args = [arg for arg in get_args(field.type) if arg is not type(None)]
                if len(args) == 1:
                    field_type = str(args[0])

            scalar_ok = self._is_valid_scalar_type(field_type, value)
            list_ok = self._is_valid_list_type(field_type, value)
            if not scalar_ok or not list_ok:
                mismatches.append(f"{field.name}: expected {field_type}, got {type(value).__name__}")

        if mismatches:
            raise ValueError("field type validation failed: " + "; ".join(mismatches))

    @staticmethod
    def _classify_parse_error(exc: Exception) -> tuple[bool, str]:
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return True, "provider_disconnect"
        if isinstance(exc, TypeError) and "schema_cls missing callable from_dict" in str(exc):
            return False, "schema"
        if isinstance(exc, json.JSONDecodeError):
            return True, "json_decode"
        if isinstance(exc, TypeError) and "payload must be a JSON object" in str(exc):
            return True, "payload_type"
        if isinstance(exc, ValueError) and "required fields validation failed" in str(exc):
            return True, "required_fields"
        if isinstance(exc, ValueError) and "field type validation failed" in str(exc):
            return True, "field_types"
        return True, "parse"

    def _parse_with_schema(self, raw: str, schema_cls: type[T]) -> T:
        cleaned = self._extract_json(raw)
        repaired = self._repair_json(cleaned)
        payload = json.loads(repaired)
        if not isinstance(payload, dict):
            raise TypeError(f"payload must be a JSON object, got {type(payload).__name__}")
        converter = getattr(schema_cls, "from_dict", None)
        if not callable(converter):
            raise TypeError(f"schema_cls missing callable from_dict: {schema_cls}")
        self._validate_required_fields(schema_cls, payload)
        self._validate_field_types(schema_cls, payload)
        parsed = cast(T, converter(payload))
        return parsed

    def generate_structured(
        self,
        prompt: str,
        schema_cls: type[T],
        model_config: ModelSelectorConfig | None = None,
    ) -> T:
        last_error: Exception | None = None
        diagnostics: list[ParseDiagnostic] = []
        max_retries = self._config.max_retries
        if model_config is not None and model_config.max_retries is not None:
            max_retries = model_config.max_retries
        attempts = max_retries + 1

        enhanced = self._enhance_prompt(prompt, schema_cls)

        for attempt in range(attempts):
            raw = ""
            try:
                raw = self._provider.complete(enhanced, model_config=model_config)
                if not raw or not raw.strip():
                    raise ConnectionError("LLM provider returned empty response")
                return self._parse_with_schema(raw, schema_cls)
            except Exception as exc:
                retryable, stage = self._classify_parse_error(exc)
                _log.warning(
                    "parse attempt %d/%d failed: %s  raw[:200]=%s", attempt + 1, attempts, exc, (raw or "")[:200]
                )
                diagnostics.append(
                    ParseDiagnostic(
                        attempt=attempt + 1,
                        stage=stage,
                        retryable=retryable,
                        error=str(exc),
                    )
                )
                last_error = exc
                if not retryable:
                    break

        details = "; ".join(
            f"attempt={d.attempt},stage={d.stage},retryable={d.retryable},error={d.error}" for d in diagnostics
        )
        raise StructuredOutputParseError(
            f"structured output parse failed after {len(diagnostics)} attempts: {last_error}; diagnostics=[{details}]",
            diagnostics,
        )

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        return self._provider.complete(prompt, model_config=model_config)

    def generate_code(
        self,
        prompt: str,
        metadata_schema_cls: type[T],
        model_config: ModelSelectorConfig | None = None,
    ) -> tuple[T, str]:
        max_retries = self._config.max_retries
        if model_config is not None and model_config.max_retries is not None:
            max_retries = model_config.max_retries
        attempts = max_retries + 1

        diagnostics: list[ParseDiagnostic] = []
        last_error: Exception | None = None
        for attempt in range(attempts):
            raw = ""
            try:
                raw = self._provider.complete(prompt, model_config=model_config)
                metadata = self._parse_with_schema(raw, metadata_schema_cls)
                code = self._extract_code(raw)
                return metadata, code
            except Exception as exc:
                retryable, stage = self._classify_parse_error(exc)
                diagnostics.append(
                    ParseDiagnostic(
                        attempt=attempt + 1,
                        stage=stage,
                        retryable=retryable,
                        error=str(exc),
                    )
                )
                last_error = exc
                if not retryable:
                    break

        details = "; ".join(
            f"attempt={d.attempt},stage={d.stage},retryable={d.retryable},error={d.error}" for d in diagnostics
        )
        raise StructuredOutputParseError(
            f"code generation parse failed after {len(diagnostics)} attempts: {last_error}; diagnostics=[{details}]",
            diagnostics,
        )
