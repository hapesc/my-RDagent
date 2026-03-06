"""LLM adapter with provider abstraction and structured output retries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Protocol, Type, TypeVar

from service_contracts import ModelSelectorConfig

T = TypeVar("T")


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

        if prompt.startswith("proposal:"):
            summary = prompt.split("proposal:", 1)[1].strip() or "proposal"
            constraints = ["llm-structured"] + _metadata_tokens()
            return json.dumps(
                {
                    "summary": summary,
                    "constraints": constraints,
                    "virtual_score": 0.5,
                }
            )
        if prompt.startswith("coding:"):
            summary = prompt.split("coding:", 1)[1].strip() or "code"
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
        if prompt.startswith("feedback:"):
            reason = prompt.split("feedback:", 1)[1].strip() or "feedback"
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

        for _ in range(attempts):
            raw = self._provider.complete(prompt, model_config=model_config)
            try:
                payload = json.loads(raw)
                if not hasattr(schema_cls, "from_dict"):
                    raise TypeError(f"schema_cls missing from_dict: {schema_cls}")
                return schema_cls.from_dict(payload)
            except Exception as exc:
                last_error = exc

        raise ValueError(f"structured output parse failed after {attempts} attempts: {last_error}")
