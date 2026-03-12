from __future__ import annotations

import os
from dataclasses import dataclass

from llm.providers.litellm_provider import LiteLLMProvider

TEST_LLM_MODEL = "openai/kimi-k2.5"
TEST_LLM_BASE_URL = "https://opencode.ai/zen/go/v1"
TEST_LLM_DISPLAY_NAME = "OpenCode Kimi K2.5"
CHATGPT_SUBSCRIPTION_MODEL = "chatgpt/gpt-5.3-codex"
CHATGPT_SUBSCRIPTION_DISPLAY_NAME = "ChatGPT Subscription (LiteLLM auth)"
_API_KEY_ENV_VARS = ("OPENCODE_API", "OPENCODE_API_KEY", "RD_AGENT_LLM_API_KEY", "GEMINI_API_KEY")
_CHATGPT_AUTH_FLAG_ENV_VARS = ("RD_AGENT_TEST_LLM_BACKEND", "RD_AGENT_USE_CHATGPT_AUTH", "LITELLM_CHATGPT_AUTH")


@dataclass(frozen=True)
class TestLLMBackend:
    mode: str
    model: str
    base_url: str | None
    display_name: str
    api_key: str


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "chatgpt", "chatgpt-auth", "chatgpt_auth"}


def _prefer_chatgpt_subscription_auth() -> bool:
    for env_var in _CHATGPT_AUTH_FLAG_ENV_VARS:
        value = os.environ.get(env_var, "")
        if not value.strip():
            continue
        if env_var == "RD_AGENT_TEST_LLM_BACKEND":
            return value.strip().lower() == "chatgpt"
        if _is_truthy(value):
            return True
    return False


def get_test_llm_api_key() -> str:
    for env_var in _API_KEY_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return ""


def resolve_test_llm_backend(api_key: str | None = None) -> TestLLMBackend:
    if _prefer_chatgpt_subscription_auth():
        return TestLLMBackend(
            mode="chatgpt_auth",
            model=CHATGPT_SUBSCRIPTION_MODEL,
            base_url=None,
            display_name=CHATGPT_SUBSCRIPTION_DISPLAY_NAME,
            api_key="",
        )

    resolved_api_key = (api_key or "").strip() or get_test_llm_api_key()
    return TestLLMBackend(
        mode="api_key_fallback",
        model=TEST_LLM_MODEL,
        base_url=TEST_LLM_BASE_URL,
        display_name=TEST_LLM_DISPLAY_NAME,
        api_key=resolved_api_key,
    )


def build_test_llm_provider(api_key: str | None = None) -> LiteLLMProvider:
    backend = resolve_test_llm_backend(api_key)
    return LiteLLMProvider(
        api_key=backend.api_key,
        model=backend.model,
        base_url=backend.base_url,
    )
