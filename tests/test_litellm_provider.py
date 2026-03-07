from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import runtime_checkable
from unittest.mock import patch

from llm.adapter import LLMProvider
from service_contracts import ModelSelectorConfig


def _mock_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


class LiteLLMProviderTests(unittest.TestCase):
    def test_provider_satisfies_llmprovider_protocol(self) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        provider = LiteLLMProvider(api_key="sk-test")
        runtime_protocol = runtime_checkable(LLMProvider)
        self.assertIsInstance(provider, runtime_protocol)

    @patch("litellm.completion")
    def test_complete_calls_litellm_and_returns_content(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("hello from model")
        provider = LiteLLMProvider(
            api_key="sk-test",
            model="gpt-4o-mini",
            base_url="https://example.invalid/v1",
        )

        result = provider.complete("say hi")

        self.assertEqual(result, "hello from model")
        mock_completion.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "say hi"}],
            api_key="sk-test",
            base_url="https://example.invalid/v1",
        )

    @patch("litellm.completion")
    def test_complete_propagates_provider_errors(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.side_effect = RuntimeError("AuthenticationError: invalid api key")
        provider = LiteLLMProvider(api_key="sk-bad")

        with self.assertRaises(RuntimeError) as ctx:
            provider.complete("hello")

        self.assertIn("AuthenticationError", str(ctx.exception))

    @patch("litellm.completion")
    def test_complete_uses_model_config_overrides(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("json output")
        provider = LiteLLMProvider(
            api_key="sk-test",
            model="gpt-4o-mini",
            base_url="https://example.invalid/v1",
        )
        model_config = ModelSelectorConfig(
            provider="litellm",
            model="gpt-4.1-mini",
            temperature=0.3,
            max_tokens=256,
            max_retries=5,
        )

        result = provider.complete("return json", model_config=model_config)

        self.assertEqual(result, "json output")
        mock_completion.assert_called_once_with(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "return json"}],
            api_key="sk-test",
            base_url="https://example.invalid/v1",
            temperature=0.3,
            max_tokens=256,
        )


if __name__ == "__main__":
    unittest.main()
