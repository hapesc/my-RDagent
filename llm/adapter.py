"""LLM adapter with provider abstraction and structured output retries."""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Protocol, Type, TypeVar

from service_contracts import ModelSelectorConfig

T = TypeVar("T")

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


class LLMProvider(Protocol):
    """Provider interface for text completion."""

    def complete(self, prompt: str, model_config: Optional[ModelSelectorConfig] = None) -> str:
        ...


class MockLLMProvider:
    """Deterministic mock provider for testing structured outputs."""

    def __init__(self, responses: Optional[List[str]] = None) -> None:
        self._responses = list(responses or [])

    def complete(self, prompt: str, model_config: Optional[ModelSelectorConfig] = None) -> str:
        def _metadata_tokens() -> List[str]:
            if model_config is None:
                return []
            tokens: List[str] = []
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

        if "proposal:" in prompt:
            summary = prompt.split("proposal:", 1)[1].split("\n")[0].strip() or "proposal"
            constraints = ["llm-structured"] + _metadata_tokens()
            return json.dumps(
                {
                    "summary": summary,
                    "constraints": constraints,
                    "virtual_score": 0.5,
                }
            )
        if "coding:" in prompt:
            summary = prompt.split("coding:", 1)[1].split("\n")[0].strip() or "code"
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
        if "feedback:" in prompt:
            reason = prompt.split("feedback:", 1)[1].split("\n")[0].strip() or "feedback"
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

        return json.dumps({"message": "ok"})


@dataclass
class LLMAdapterConfig:
    """Adapter configuration."""

    max_retries: int = 2


class LLMAdapter:
    """Adapter that parses structured JSON outputs with retries."""

    def __init__(self, provider: LLMProvider, config: Optional[LLMAdapterConfig] = None) -> None:
        self._provider = provider
        self._config = config or LLMAdapterConfig()

    def _build_schema_hint(self, schema_cls: Type) -> str:
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
            elif "List[str]" in ann:
                example[f.name] = ["string"]
            else:
                example[f.name] = "value"
        return json.dumps(example, indent=2)

    def _enhance_prompt(self, prompt: str, schema_cls: Type) -> str:
        """Wrap user prompt with JSON output instructions."""
        schema_hint = self._build_schema_hint(schema_cls)
        if not schema_hint:
            return prompt
        return (
            f"{prompt}\n\n"
            f"You MUST respond with ONLY a valid JSON object matching this schema (no markdown, no explanation):\n"
            f"{schema_hint}"
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown code fences if present."""
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            return match.group(1).strip()
        return raw.strip()

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        model_config: Optional[ModelSelectorConfig] = None,
    ) -> T:
        last_error: Optional[Exception] = None
        max_retries = self._config.max_retries
        if model_config is not None and model_config.max_retries is not None:
            max_retries = model_config.max_retries
        attempts = max_retries + 1

        enhanced = self._enhance_prompt(prompt, schema_cls)

        for _ in range(attempts):
            raw = self._provider.complete(enhanced, model_config=model_config)
            try:
                cleaned = self._extract_json(raw)
                payload = json.loads(cleaned)
                if not hasattr(schema_cls, "from_dict"):
                    raise TypeError(f"schema_cls missing from_dict: {schema_cls}")
                return schema_cls.from_dict(payload)
            except Exception as exc:
                last_error = exc

        raise ValueError(f"structured output parse failed after {attempts} attempts: {last_error}")
