from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import runtime_checkable
from unittest.mock import patch

from litellm.exceptions import APIConnectionError as LiteLLMAPIConnectionError
from litellm.exceptions import AuthenticationError as LiteLLMAuthError
from litellm.exceptions import ServiceUnavailableError as LiteLLMServiceUnavailableError
from litellm.exceptions import Timeout as LiteLLMTimeout

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
    def test_chatgpt_subscription_model_detection_only_matches_chatgpt_prefix(self) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        self.assertTrue(LiteLLMProvider._is_chatgpt_subscription_model("chatgpt/gpt-5.3-codex"))
        self.assertFalse(LiteLLMProvider._is_chatgpt_subscription_model("gpt-5"))
        self.assertFalse(LiteLLMProvider._is_chatgpt_subscription_model("openai/gpt-4o-mini"))

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
            timeout=60,
            stream=False,
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
            timeout=60,
            response_format={"type": "json_object"},
            stream=False,
        )

    @patch("litellm.completion")
    def test_complete_omits_max_tokens_for_chatgpt_subscription_models(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("json output")
        provider = LiteLLMProvider(
            api_key="",
            model="chatgpt/gpt-5.3-codex",
        )
        model_config = ModelSelectorConfig(
            provider="litellm",
            model="chatgpt/gpt-5.3-codex",
            temperature=0.3,
            max_tokens=256,
            max_retries=5,
        )

        result = provider.complete("return json", model_config=model_config)

        self.assertEqual(result, "json output")
        kwargs = mock_completion.call_args.kwargs
        self.assertEqual(kwargs["model"], "chatgpt/gpt-5.3-codex")
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "return json"}])
        self.assertEqual(kwargs["temperature"], 0.3)
        self.assertEqual(kwargs["timeout"], 60)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(kwargs["stream"], False)
        self.assertNotIn("api_key", kwargs)
        self.assertNotIn("max_tokens", kwargs)

    @patch("litellm.completion")
    def test_complete_does_not_force_json_mode_for_mixed_json_and_code_prompt(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("mixed output")
        provider = LiteLLMProvider(api_key="sk-test", model="gpt-4o-mini")
        prompt = (
            "Return EXACTLY two sections:\\n"
            '{"artifact_id":"factor_v1","description":"desc","location":"factor.py"}\\n'
            '```python\\nprint("hi")\\n```'
        )

        provider.complete(prompt)

        kwargs = mock_completion.call_args.kwargs
        self.assertNotIn("response_format", kwargs)

    @patch("litellm.completion")
    def test_complete_does_not_force_json_mode_for_filename_mentions(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("script")
        provider = LiteLLMProvider(api_key="sk-test", model="gpt-4o-mini")

        provider.complete("Write a script that saves metrics.json after training.")

        kwargs = mock_completion.call_args.kwargs
        self.assertNotIn("response_format", kwargs)

    @patch("litellm.completion")
    def test_complete_uses_deterministic_thinking_timeout(self, mock_completion) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.return_value = _mock_response("thinking output")
        provider = LiteLLMProvider(api_key="sk-test", model="gemini/gemini-2.5-pro")

        provider.complete("think")

        mock_completion.assert_called_once_with(
            model="gemini/gemini-2.5-pro",
            messages=[{"role": "user", "content": "think"}],
            api_key="sk-test",
            max_tokens=16384,
            timeout=180,
            stream=False,
        )

    @patch("llm.providers.litellm_provider.time.sleep")
    @patch("litellm.completion")
    def test_complete_retries_on_connection_error_then_succeeds(self, mock_completion, mock_sleep) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.side_effect = [
            LiteLLMAPIConnectionError("network hiccup", llm_provider="gemini", model="gpt-4o-mini"),
            _mock_response("recovered"),
        ]
        provider = LiteLLMProvider(api_key="sk-test")

        result = provider.complete("hello")

        self.assertEqual(result, "recovered")
        self.assertEqual(mock_completion.call_count, 2)
        mock_sleep.assert_called_once_with(0.5)

    @patch("llm.providers.litellm_provider.time.sleep")
    @patch("litellm.completion")
    def test_complete_fails_after_bounded_unavailable_retries(self, mock_completion, mock_sleep) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.side_effect = LiteLLMServiceUnavailableError(
            "temporarily unavailable",
            llm_provider="gemini",
            model="gpt-4o-mini",
        )
        provider = LiteLLMProvider(api_key="sk-test")

        with self.assertRaises(RuntimeError) as ctx:
            provider.complete("hello")

        self.assertIn("LLM provider unavailable", str(ctx.exception))
        self.assertEqual(mock_completion.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(0.5)
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch("llm.providers.litellm_provider.time.sleep")
    @patch("litellm.completion")
    def test_complete_does_not_retry_timeout(self, mock_completion, mock_sleep) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.side_effect = LiteLLMTimeout(
            "timed out",
            model="gpt-4o-mini",
            llm_provider="gemini",
        )
        provider = LiteLLMProvider(api_key="sk-test")

        with self.assertRaises(RuntimeError) as ctx:
            provider.complete("hello")

        self.assertIn("LLM request timed out", str(ctx.exception))
        mock_completion.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("llm.providers.litellm_provider.time.sleep")
    @patch("litellm.completion")
    def test_complete_does_not_retry_authentication_error(self, mock_completion, mock_sleep) -> None:
        from llm.providers.litellm_provider import LiteLLMProvider

        mock_completion.side_effect = LiteLLMAuthError(
            "invalid key",
            llm_provider="gemini",
            model="gpt-4o-mini",
        )
        provider = LiteLLMProvider(api_key="sk-test")

        with self.assertRaises(RuntimeError) as ctx:
            provider.complete("hello")

        self.assertIn("LLM authentication failed", str(ctx.exception))
        mock_completion.assert_called_once()
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
