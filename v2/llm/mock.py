from __future__ import annotations

from collections.abc import Callable
from typing import Any


class _MockResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _StructuredMockChatModel:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def invoke(self, _: Any) -> Any:
        return self._payload


class MockChatModel:
    def __init__(self, response: str = "mock response", structured_response: Any | None = None) -> None:
        self._response = response
        self._structured_response = structured_response
        self.calls = 0

    def invoke(self, _: Any) -> _MockResponse:
        self.calls += 1
        return _MockResponse(self._response)

    def with_structured_output(self, schema: type[Any]) -> _StructuredMockChatModel:
        payload = self._structured_response
        if payload is None:
            payload = schema.model_validate({}) if hasattr(schema, "model_validate") else {}
        return _StructuredMockChatModel(payload)


class FailThenSuccessMock:
    def __init__(
        self, fail_count: int, response: str = "success", error_factory: Callable[[], Exception] | None = None
    ) -> None:
        self._remaining_failures = fail_count
        self._response = response
        self._error_factory = error_factory or (lambda: RuntimeError("transient mock failure"))
        self.calls = 0

    def invoke(self, _: Any) -> _MockResponse:
        self.calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise self._error_factory()
        return _MockResponse(self._response)

    def with_structured_output(self, _: type[Any]) -> "FailThenSuccessMock":
        return self
