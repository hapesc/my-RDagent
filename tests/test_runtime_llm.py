"""Tests for RuntimeContext LLM provider selection."""

from __future__ import annotations

import pytest

from app.config import load_config
from app.runtime import build_runtime
from llm import LLMAdapter
from llm.providers.litellm_provider import LiteLLMProvider


def test_default_config_raises_runtime_error():
    """Default config (no env vars, provider='mock') should raise RuntimeError."""
    with pytest.raises(RuntimeError, match="Unknown or missing LLM provider"):
        build_runtime()


def test_litellm_provider_created_with_config(monkeypatch):
    """Config with llm_provider='litellm' should create LiteLLMProvider."""
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("RD_AGENT_LLM_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("RD_AGENT_LLM_MODEL", "gpt-4-turbo")
    monkeypatch.setenv("RD_AGENT_LLM_BASE_URL", "https://custom.api.com")

    runtime = build_runtime()

    assert isinstance(runtime.llm_adapter, LLMAdapter)
    assert isinstance(runtime.llm_adapter._provider, LiteLLMProvider)

    provider = runtime.llm_adapter._provider
    assert provider._api_key == "test-api-key-12345"
    assert provider._model == "gpt-4-turbo"
    assert provider._base_url == "https://custom.api.com"


def test_litellm_provider_with_minimal_config(monkeypatch):
    """LiteLLM with only provider and api_key set should use defaults."""
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("RD_AGENT_LLM_API_KEY", "test-key")

    runtime = build_runtime()

    assert isinstance(runtime.llm_adapter._provider, LiteLLMProvider)
    provider = runtime.llm_adapter._provider
    assert provider._api_key == "test-key"
    assert provider._model == "gpt-4o-mini"  # default from config
    assert provider._base_url is None


def test_real_provider_minimal_config_uses_conservative_runtime_defaults(monkeypatch):
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("RD_AGENT_LLM_API_KEY", "test-key")

    config = load_config()

    assert config.uses_real_llm_provider is True
    assert config.layer0_n_candidates == 1
    assert config.layer0_k_forward == 1
    assert config.costeer_max_rounds == 1
    assert config.sandbox_timeout_sec == 120
    assert config.real_provider_warnings == ()


def test_unknown_provider_raises_runtime_error(monkeypatch):
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "openai")

    with pytest.raises(RuntimeError, match="Unknown or missing LLM provider"):
        build_runtime()


def test_llm_adapter_available_in_runtime_context(monkeypatch):
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "litellm")
    monkeypatch.setenv("RD_AGENT_LLM_API_KEY", "test-key")

    runtime = build_runtime()

    assert hasattr(runtime, "llm_adapter")
    assert runtime.llm_adapter is not None
    assert isinstance(runtime.llm_adapter, LLMAdapter)
