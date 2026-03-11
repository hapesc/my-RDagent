from __future__ import annotations

import os

import pytest

from llm import LLMAdapter, LLMAdapterConfig
from llm.providers.litellm_provider import LiteLLMProvider
from service_contracts import ModelSelectorConfig
from tests.golden_tasks.benchmark import resolve_benchmark_credentials


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-llm", action="store_true", help="Run LLM-backed benchmark tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-llm"):
        return
    skip = pytest.mark.skip(reason="need --run-llm to run")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def benchmark_llm_adapter() -> LLMAdapter:
    api_key, model = resolve_benchmark_credentials()
    if not api_key:
        pytest.skip("A supported benchmark API key is required for benchmark tests")

    base_url = os.environ.get("BENCHMARK_LLM_BASE_URL")
    provider = LiteLLMProvider(api_key=api_key, model=model, base_url=base_url)
    return LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=0))


@pytest.fixture(scope="session")
def benchmark_model_config() -> ModelSelectorConfig:
    _, model = resolve_benchmark_credentials()
    return ModelSelectorConfig(
        provider="litellm",
        model=model,
        temperature=float(os.environ.get("BENCHMARK_LLM_TEMPERATURE", "0.0")),
        max_tokens=4096,
        max_retries=0,
    )
