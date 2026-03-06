"""LLM adapter with provider abstraction and structured output retries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Protocol, Type, TypeVar

T = TypeVar("T")


class LLMProvider(Protocol):
    """Provider interface for text completion."""

    def complete(self, prompt: str) -> str:
        ...


class MockLLMProvider:
    """Deterministic mock provider for testing structured outputs."""

    def __init__(self, responses: Optional[List[str]] = None) -> None:
        self._responses = list(responses or [])

    def complete(self, prompt: str) -> str:
        if self._responses:
            return self._responses.pop(0)

        if prompt.startswith("proposal:"):
            summary = prompt.split("proposal:", 1)[1].strip() or "proposal"
            return json.dumps(
                {
                    "summary": summary,
                    "constraints": ["llm-structured"],
                    "virtual_score": 0.5,
                }
            )
        if prompt.startswith("coding:"):
            summary = prompt.split("coding:", 1)[1].strip() or "code"
            return json.dumps(
                {
                    "artifact_id": "artifact-llm",
                    "description": summary,
                    "location": "/tmp/rd_agent_workspace",
                }
            )
        if prompt.startswith("feedback:"):
            reason = prompt.split("feedback:", 1)[1].strip() or "feedback"
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

    def generate_structured(self, prompt: str, schema_cls: Type[T]) -> T:
        last_error: Optional[Exception] = None
        attempts = self._config.max_retries + 1

        for _ in range(attempts):
            raw = self._provider.complete(prompt)
            try:
                payload = json.loads(raw)
                if not hasattr(schema_cls, "from_dict"):
                    raise TypeError(f"schema_cls missing from_dict: {schema_cls}")
                return schema_cls.from_dict(payload)
            except Exception as exc:
                last_error = exc

        raise ValueError(f"structured output parse failed after {attempts} attempts: {last_error}")
