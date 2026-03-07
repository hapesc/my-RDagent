from __future__ import annotations

from typing import Any, Dict, Optional, cast

import litellm
from litellm.exceptions import AuthenticationError as LiteLLMAuthError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
from litellm.exceptions import Timeout as LiteLLMTimeout

from service_contracts import ModelSelectorConfig


_THINKING_MODEL_PREFIXES = ("gemini/gemini-2.5-pro", "o1", "o3", "o4")
_DEFAULT_THINKING_MAX_TOKENS = 8192


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

        try:
            response = litellm.completion(**kwargs)
        except LiteLLMAuthError as exc:
            raise RuntimeError(f"LLM authentication failed for model '{model}': {exc}") from exc
        except LiteLLMRateLimitError as exc:
            raise RuntimeError(f"LLM rate limit exceeded for model '{model}': {exc}") from exc
        except LiteLLMTimeout as exc:
            raise RuntimeError(f"LLM request timed out for model '{model}': {exc}") from exc

        completion_response = cast(Any, response)
        content = completion_response.choices[0].message.content
        return content if content is not None else ""
