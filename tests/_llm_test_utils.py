from __future__ import annotations

from unittest.mock import patch

from llm import LLMAdapter, MockLLMProvider


def make_mock_llm_adapter() -> LLMAdapter:
    return LLMAdapter(provider=MockLLMProvider())


def patch_runtime_llm_provider():
    return patch("app.runtime._create_llm_provider", return_value=MockLLMProvider())
