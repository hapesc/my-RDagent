from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple, Type, cast

import litellm
from litellm.exceptions import AuthenticationError as LiteLLMAuthError
from litellm.exceptions import APIConnectionError as LiteLLMAPIConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
from litellm.exceptions import ServiceUnavailableError as LiteLLMServiceUnavailableError
from litellm.exceptions import Timeout as LiteLLMTimeout

from service_contracts import ModelSelectorConfig


_THINKING_MODEL_PREFIXES = ("gemini/gemini-2.5-pro", "o1", "o3", "o4")
_DEFAULT_THINKING_MAX_TOKENS = 8192
_DEFAULT_TIMEOUT_SEC = 60
_DEFAULT_THINKING_TIMEOUT_SEC = 120
_TRANSIENT_RETRY_DELAYS_SEC = (0.1, 0.3)
_RETRYABLE_TRANSIENT_ERRORS: Tuple[Type[Exception], ...] = (
    LiteLLMAPIConnectionError,
    LiteLLMServiceUnavailableError,
)


class LiteLLMProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._temperature: Optional[float] = None
        self._max_tokens: Optional[int] = None

    @staticmethod
    def _is_thinking_model(model: str) -> bool:
        return any(model.startswith(p) for p in _THINKING_MODEL_PREFIXES)

    def complete(self, prompt: str, model_config: Optional[ModelSelectorConfig] = None) -> str:
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

        if max_tokens is None and self._is_thinking_model(model):
            max_tokens = _DEFAULT_THINKING_MAX_TOKENS

        timeout = _DEFAULT_THINKING_TIMEOUT_SEC if self._is_thinking_model(model) else _DEFAULT_TIMEOUT_SEC

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url is not None:
            kwargs["base_url"] = self._base_url
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        kwargs["timeout"] = timeout

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
                time.sleep(_TRANSIENT_RETRY_DELAYS_SEC[attempt_idx])

        completion_response = cast(Any, response)
        content = completion_response.choices[0].message.content
        return content if content is not None else ""
