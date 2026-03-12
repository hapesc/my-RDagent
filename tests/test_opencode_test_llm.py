from __future__ import annotations

import os
from unittest.mock import patch

from llm.providers.litellm_provider import LiteLLMProvider
from scripts.real_test_llm import (
    CHATGPT_SUBSCRIPTION_MODEL,
    TEST_LLM_BASE_URL,
    TEST_LLM_DISPLAY_NAME,
    TEST_LLM_MODEL,
    build_test_llm_provider,
    get_test_llm_api_key,
    resolve_test_llm_backend,
)


def test_test_llm_constants_match_opencode_kimi_k25() -> None:
    assert TEST_LLM_MODEL == "openai/kimi-k2.5"
    assert TEST_LLM_BASE_URL == "https://opencode.ai/zen/go/v1"
    assert "kimi k2.5" in TEST_LLM_DISPLAY_NAME.lower()


def test_api_key_prefers_opencode_key() -> None:
    with patch.dict(
        os.environ,
        {
            "OPENCODE_API": "opencode-key",
            "OPENCODE_API_KEY": "legacy-opencode-key",
            "RD_AGENT_LLM_API_KEY": "rd-key",
            "GEMINI_API_KEY": "gemini-key",
        },
        clear=False,
    ):
        assert get_test_llm_api_key() == "opencode-key"


def test_api_key_falls_back_to_rd_agent_key() -> None:
    with patch.dict(os.environ, {"RD_AGENT_LLM_API_KEY": "rd-key"}, clear=True):
        assert get_test_llm_api_key() == "rd-key"


def test_build_test_llm_provider_uses_opencode_defaults() -> None:
    provider = build_test_llm_provider("secret")
    assert isinstance(provider, LiteLLMProvider)
    assert provider._api_key == "secret"
    assert provider._model == TEST_LLM_MODEL
    assert provider._base_url == TEST_LLM_BASE_URL


def test_resolve_test_llm_backend_prefers_chatgpt_auth_mode() -> None:
    with patch.dict(
        os.environ,
        {
            "RD_AGENT_TEST_LLM_BACKEND": "chatgpt",
            "OPENCODE_API": "opencode-key",
        },
        clear=True,
    ):
        backend = resolve_test_llm_backend()

    assert backend.mode == "chatgpt_auth"
    assert backend.model == CHATGPT_SUBSCRIPTION_MODEL
    assert backend.base_url is None
    assert backend.api_key == ""


def test_build_test_llm_provider_uses_chatgpt_subscription_backend() -> None:
    with patch.dict(os.environ, {"RD_AGENT_TEST_LLM_BACKEND": "chatgpt"}, clear=True):
        provider = build_test_llm_provider()

    assert isinstance(provider, LiteLLMProvider)
    assert provider._api_key == ""
    assert provider._model == CHATGPT_SUBSCRIPTION_MODEL
    assert provider._base_url is None
