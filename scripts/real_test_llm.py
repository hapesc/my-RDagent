from __future__ import annotations

import os

from llm.providers.litellm_provider import LiteLLMProvider

TEST_LLM_MODEL = "openai/kimi-k2.5"
TEST_LLM_BASE_URL = "https://opencode.ai/zen/go/v1"
TEST_LLM_DISPLAY_NAME = "OpenCode Kimi K2.5"
_API_KEY_ENV_VARS = ("OPENCODE_API", "OPENCODE_API_KEY", "RD_AGENT_LLM_API_KEY", "GEMINI_API_KEY")


def get_test_llm_api_key() -> str:
    for env_var in _API_KEY_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return ""


def build_test_llm_provider(api_key: str | None = None) -> LiteLLMProvider:
    resolved_api_key = (api_key or "").strip() or get_test_llm_api_key()
    return LiteLLMProvider(
        api_key=resolved_api_key,
        model=TEST_LLM_MODEL,
        base_url=TEST_LLM_BASE_URL,
    )
