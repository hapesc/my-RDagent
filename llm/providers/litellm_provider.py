from __future__ import annotations

import logging
import time
from typing import Any, cast

import litellm
from litellm.exceptions import APIConnectionError as LiteLLMAPIConnectionError
from litellm.exceptions import AuthenticationError as LiteLLMAuthError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
from litellm.exceptions import ServiceUnavailableError as LiteLLMServiceUnavailableError
from litellm.exceptions import Timeout as LiteLLMTimeout

from service_contracts import ModelSelectorConfig

_log = logging.getLogger(__name__)

_THINKING_MODEL_PREFIXES = ("gemini/gemini-2.5-pro", "o1", "o3", "o4")
_DEFAULT_THINKING_MAX_TOKENS = 16384
_DEFAULT_TIMEOUT_SEC = 60
_DEFAULT_THINKING_TIMEOUT_SEC = 180
_TRANSIENT_RETRY_DELAYS_SEC = (0.5, 1.0, 2.0)
_RETRYABLE_TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    LiteLLMAPIConnectionError,
    LiteLLMServiceUnavailableError,
)
_JSON_MODE_HINTS = (
    "return json",
    "valid json",
    "json object",
    "output json",
    "respond in json",
    "schema",
)


class LiteLLMProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._temperature: float | None = None
        self._max_tokens: int | None = None

    @staticmethod
    def _is_thinking_model(model: str) -> bool:
        return any(model.startswith(p) for p in _THINKING_MODEL_PREFIXES)

    @staticmethod
    def _is_chatgpt_subscription_model(model: str) -> bool:
        return model.startswith("chatgpt/")

    def complete(self, prompt: str, model_config: ModelSelectorConfig | None = None) -> str:
        model = self._model
        temperature = self._temperature
        max_tokens = self._max_tokens

        if model_config is not None:
            if model_config.model and model_config.provider not in (None, "", "mock"):
                model = model_config.model
            if model_config.temperature is not None:
                temperature = model_config.temperature
            if model_config.max_tokens is not None:
                max_tokens = model_config.max_tokens

        is_thinking = self._is_thinking_model(model)

        if max_tokens is None and is_thinking:
            max_tokens = _DEFAULT_THINKING_MAX_TOKENS

        timeout = _DEFAULT_THINKING_TIMEOUT_SEC if is_thinking else _DEFAULT_TIMEOUT_SEC

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url is not None:
            kwargs["base_url"] = self._base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None and not self._is_chatgpt_subscription_model(model):
            kwargs["max_tokens"] = max_tokens
        kwargs["timeout"] = timeout

        # Force JSON output mode for structured output prompts.
        # This makes Gemini Thinking models put results in content (not only reasoning_content).
        if self._should_force_json_mode(prompt):
            kwargs["response_format"] = {"type": "json_object"}

        # Disable streaming for structured output to avoid truncation bugs
        kwargs["stream"] = False

        attempts = len(_TRANSIENT_RETRY_DELAYS_SEC) + 1
        response: Any = None
        for attempt_idx in range(attempts):
            try:
                response = litellm.completion(**kwargs)
                break
            except LiteLLMAuthError as exc:
                raise RuntimeError(f"LLM authentication failed for model '{model}': {exc}") from exc
            except LiteLLMRateLimitError as exc:
                raise RuntimeError(f"LLM rate limit exceeded for model '{model}': {exc}") from exc
            except LiteLLMTimeout as exc:
                raise RuntimeError(f"LLM request timed out for model '{model}': {exc}") from exc
            except _RETRYABLE_TRANSIENT_ERRORS as exc:
                if attempt_idx >= len(_TRANSIENT_RETRY_DELAYS_SEC):
                    raise RuntimeError(
                        f"LLM provider unavailable for model '{model}' after {attempts} attempts: {exc}"
                    ) from exc
                _log.warning("Transient error (attempt %d/%d): %s", attempt_idx + 1, attempts, exc)
                time.sleep(_TRANSIENT_RETRY_DELAYS_SEC[attempt_idx])

        completion_response = cast(Any, response)
        message = completion_response.choices[0].message
        content = message.content

        # For thinking models, content may be empty while reasoning_content has the answer
        if content is None or (isinstance(content, str) and not content.strip()):
            reasoning = getattr(message, "reasoning_content", None)
            if reasoning and isinstance(reasoning, str) and reasoning.strip():
                _log.warning(
                    "Model '%s' returned empty content but has reasoning_content (%d chars). "
                    "Using reasoning_content as fallback.",
                    model,
                    len(reasoning),
                )
                content = reasoning

        # Final empty check — raise so adapter can retry
        if content is None or (isinstance(content, str) and not content.strip()):
            finish_reason = getattr(completion_response.choices[0], "finish_reason", "unknown")
            raise ConnectionError(
                f"LLM returned empty content for model '{model}' "
                f"(finish_reason={finish_reason}). "
                "This may indicate the model's safety filter blocked the response, "
                "max_tokens was insufficient, or a thinking model routing issue."
            )

        return content

    @staticmethod
    def _should_force_json_mode(prompt: str) -> bool:
        prompt_lower = prompt.lower()
        return any(hint in prompt_lower for hint in _JSON_MODE_HINTS)
