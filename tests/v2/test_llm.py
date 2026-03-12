from __future__ import annotations

from pydantic import BaseModel

from v2.llm.adapter import V2LLMAdapter
from v2.llm.mock import FailThenSuccessMock, MockChatModel


class GreetingSchema(BaseModel):
    message: str


def test_complete_returns_str() -> None:
    llm = V2LLMAdapter(MockChatModel(response="hello"))

    assert llm.complete("test") == "hello"


def test_structured_output_returns_pydantic_model() -> None:
    llm = V2LLMAdapter(MockChatModel(structured_response={"message": "hi"}))

    result = llm.structured_output("test", GreetingSchema)

    assert isinstance(result, GreetingSchema)
    assert result.message == "hi"


def test_extract_code_reads_python_fence_block() -> None:
    llm = V2LLMAdapter(MockChatModel())

    code = llm.extract_code("""Before\n```python\nprint(1)\n```\nAfter""")

    assert code == "print(1)"


def test_retry_eventually_succeeds() -> None:
    model = FailThenSuccessMock(fail_count=2, response="success")
    llm = V2LLMAdapter(model, sleep_func=lambda _: None)

    result = llm.complete("test")

    assert result == "success"
    assert model.calls == 3
