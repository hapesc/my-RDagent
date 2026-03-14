from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

worktree_root = Path(__file__).parent.parent
if str(worktree_root) not in sys.path:
    sys.path.insert(0, str(worktree_root))

# Guard LLM imports — litellm is an optional dependency (the `llm` extra).
# Tests that don't need a real LLM provider must be collectible without it.
try:
    from llm import LLMAdapter, LLMAdapterConfig
    from scripts.real_test_llm import build_test_llm_provider
    from service_contracts import ModelSelectorConfig
    from tests.golden_tasks.benchmark import resolve_benchmark_credentials

    _HAS_LLM_DEPS = True
except ImportError:
    _HAS_LLM_DEPS = False


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-llm", action="store_true", help="Run LLM-backed benchmark tests")
    parser.addoption("--run-evals", action="store_true", help="Run legacy evaluation regression tests")
    parser.addoption("--run-benchmarks", action="store_true", help="Run LangSmith benchmark tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--run-llm"):
        skip = pytest.mark.skip(reason="need --run-llm to run")
        for item in items:
            if "llm" in item.keywords:
                item.add_marker(skip)
    if not config.getoption("--run-evals"):
        skip_eval = pytest.mark.skip(reason="need --run-evals to run")
        for item in items:
            if "eval" in item.keywords:
                item.add_marker(skip_eval)
    if not config.getoption("--run-benchmarks"):
        skip_bench = pytest.mark.skip(reason="need --run-benchmarks to run")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_bench)


if _HAS_LLM_DEPS:

    @pytest.fixture(scope="session")
    def benchmark_llm_adapter() -> LLMAdapter:
        api_key, model = resolve_benchmark_credentials()
        if not api_key:
            pytest.skip("A supported benchmark API key is required for benchmark tests")

        provider = build_test_llm_provider(api_key)
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
