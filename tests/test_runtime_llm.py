"""Tests for RuntimeContext LLM provider selection."""

from __future__ import annotations

import pytest

from app.config import load_config
from app.runtime import build_runtime
from llm import LLMAdapter, MockLLMProvider
from llm.providers.litellm_provider import LiteLLMProvider


def test_default_config_uses_mock_provider():
    """Default config (no env vars) should create MockLLMProvider."""
    runtime = build_runtime()
    
    assert hasattr(runtime, "llm_adapter")
    assert isinstance(runtime.llm_adapter, LLMAdapter)
    assert isinstance(runtime.llm_adapter._provider, MockLLMProvider)


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


def test_unknown_provider_falls_back_to_mock(monkeypatch):
    """Unknown provider should fall back to MockLLMProvider."""
    monkeypatch.setenv("RD_AGENT_LLM_PROVIDER", "openai")
    
    runtime = build_runtime()
    
    # Should fall back to mock for unknown providers
    assert isinstance(runtime.llm_adapter._provider, MockLLMProvider)


def test_llm_adapter_available_in_runtime_context():
    """RuntimeContext should expose llm_adapter field."""
    runtime = build_runtime()
    
    # Verify field exists and is accessible
    assert hasattr(runtime, "llm_adapter")
    assert runtime.llm_adapter is not None
    
    # Verify it's a working LLMAdapter
    result = runtime.llm_adapter._provider.complete("test prompt")
    assert isinstance(result, str)
