"""TDD tests for LLM configuration fields in AppConfig."""

import unittest
from app.config import load_config


class TestLLMConfig(unittest.TestCase):
    """Test LLM provider configuration."""

    def test_default_llm_provider_is_mock(self):
        """Default LLM provider should be 'mock'."""
        config = load_config({})
        self.assertEqual(config.llm_provider, "mock")

    def test_default_llm_model(self):
        """Default LLM model should be 'gpt-4o-mini'."""
        config = load_config({})
        self.assertEqual(config.llm_model, "gpt-4o-mini")

    def test_env_override_provider(self):
        """Environment variable RD_AGENT_LLM_PROVIDER should override default."""
        config = load_config({"RD_AGENT_LLM_PROVIDER": "litellm"})
        self.assertEqual(config.llm_provider, "litellm")

    def test_env_override_api_key(self):
        """Environment variable RD_AGENT_LLM_API_KEY should set api_key."""
        config = load_config({"RD_AGENT_LLM_API_KEY": "sk-test"})
        self.assertEqual(config.llm_api_key, "sk-test")

    def test_env_override_model(self):
        """Environment variable RD_AGENT_LLM_MODEL should override default."""
        config = load_config({"RD_AGENT_LLM_MODEL": "gpt-4"})
        self.assertEqual(config.llm_model, "gpt-4")

    def test_env_override_base_url(self):
        """Environment variable RD_AGENT_LLM_BASE_URL should set base_url."""
        config = load_config({"RD_AGENT_LLM_BASE_URL": "http://localhost:8080"})
        self.assertEqual(config.llm_base_url, "http://localhost:8080")

    def test_default_api_key_is_none(self):
        """Default LLM API key should be None."""
        config = load_config({})
        self.assertIsNone(config.llm_api_key)

    def test_default_base_url_is_none(self):
        """Default LLM base URL should be None."""
        config = load_config({})
        self.assertIsNone(config.llm_base_url)

    def test_default_costeer_max_rounds(self):
        """Default costeer_max_rounds should be 1."""
        config = load_config({})
        self.assertEqual(config.costeer_max_rounds, 1)

    def test_env_override_costeer_max_rounds(self):
        """Environment variable RD_AGENT_COSTEER_MAX_ROUNDS should override default."""
        config = load_config({"RD_AGENT_COSTEER_MAX_ROUNDS": "3"})
        self.assertEqual(config.costeer_max_rounds, 3)


if __name__ == "__main__":
    unittest.main()
