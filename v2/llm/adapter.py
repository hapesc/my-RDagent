from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import Any, Protocol, TypeVar, cast

from pydantic import BaseModel

from v2.llm.codegen import extract_first_code, validate_code

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class SupportsInvoke(Protocol):
    def invoke(self, input_value: Any) -> Any: ...


class SupportsStructuredOutput(Protocol):
    def with_structured_output(self, schema: type[Any]) -> SupportsInvoke: ...


@dataclass(frozen=True)
class RetryDiagnostics:
    attempts: int
    last_error: str


class V2LLMAdapterError(RuntimeError):
    def __init__(self, message: str, diagnostics: RetryDiagnostics) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class V2LLMAdapter:
    def __init__(
        self,
        model: SupportsInvoke,
        *,
        max_attempts: int = 3,
        sleep_func: Callable[[float], None] = sleep,
    ) -> None:
        self._model = model
        self._max_attempts = max_attempts
        self._sleep = sleep_func

    def complete(self, prompt: str, system: str | None = None) -> str:
        response = self._retry_invoke(self._model, prompt, system)
        return self._coerce_text(response)

    def structured_output(self, prompt: str, schema: type[SchemaT], system: str | None = None) -> SchemaT:
        if not hasattr(self._model, "with_structured_output"):
            diagnostics = RetryDiagnostics(attempts=0, last_error="model does not support structured output")
            raise V2LLMAdapterError("Structured output unavailable", diagnostics)

        structured_model = cast(SupportsStructuredOutput, self._model).with_structured_output(schema)
        result = self._retry_invoke(structured_model, prompt, system)
        if isinstance(result, schema):
            return result
        if isinstance(result, BaseModel):
            return schema.model_validate(result.model_dump())
        return schema.model_validate(result)

    def extract_code(self, text: str) -> str:
        code = extract_first_code(text)
        if not validate_code(code):
            raise ValueError("Extracted code failed quality gate")
        return code

    def _retry_invoke(self, model: SupportsInvoke, prompt: str, system: str | None) -> Any:
        delays = (0.5, 1.0)
        last_error: Exception | None = None
        payload = self._build_input(prompt, system)

        for attempt in range(1, self._max_attempts + 1):
            try:
                return model.invoke(payload)
            except Exception as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break
                self._sleep(delays[min(attempt - 1, len(delays) - 1)])

        diagnostics = RetryDiagnostics(attempts=self._max_attempts, last_error=str(last_error))
        raise V2LLMAdapterError("LLM invocation failed after retries", diagnostics) from last_error

    @staticmethod
    def _build_input(prompt: str, system: str | None) -> Any:
        try:
            messages_module = importlib.import_module("langchain_core.messages")
        except ImportError:
            if system:
                return f"SYSTEM: {system}\n\nUSER: {prompt}"
            return prompt

        human_message = messages_module.HumanMessage
        system_message = messages_module.SystemMessage
        messages: list[Any] = []
        if system:
            messages.append(system_message(content=system))
        messages.append(human_message(content=prompt))
        return messages

    @staticmethod
    def _coerce_text(response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else getattr(item, "text", str(item)) for item in content
            )
        return str(content)
