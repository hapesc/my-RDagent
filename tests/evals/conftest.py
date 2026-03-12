from __future__ import annotations

import pytest

from llm import LLMAdapter, LLMAdapterConfig
from scripts.real_test_llm import build_test_llm_provider
from service_contracts import ModelSelectorConfig
from tests.golden_tasks.benchmark import resolve_benchmark_credentials


@pytest.fixture(scope="session")
def eval_llm_adapter() -> LLMAdapter:
    api_key, model = resolve_benchmark_credentials()
    if not api_key:
        pytest.skip("A supported API key is required for eval tests")
    provider = build_test_llm_provider(api_key)
    return LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=1))


@pytest.fixture(scope="session")
def eval_model_config() -> ModelSelectorConfig:
    _, model = resolve_benchmark_credentials()
    return ModelSelectorConfig(
        provider="litellm",
        model=model,
        temperature=0.0,
        max_tokens=4096,
        max_retries=1,
    )
