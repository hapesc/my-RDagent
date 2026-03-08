"""Task-05 tests for scaffolding and configuration loading."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app.config import load_config
from app.startup import main as startup_main


class ConfigLayerTests(unittest.TestCase):
    def test_load_config_defaults(self) -> None:
        config = load_config({})
        self.assertEqual(config.env, "dev")
        self.assertEqual(config.default_scenario, "data_science")
        self.assertEqual(config.sandbox_timeout_sec, 300)
        self.assertFalse(config.allow_local_execution)

    def test_load_config_from_env_map(self) -> None:
        config = load_config(
            {
                "AGENTRD_ENV": "prod",
                "AGENTRD_DEFAULT_SCENARIO": "custom",
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "900",
                "AGENTRD_TRACE_STORAGE_PATH": "/tmp/custom_trace.jsonl",
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
            }
        )
        self.assertEqual(config.env, "prod")
        self.assertEqual(config.default_scenario, "custom")
        self.assertEqual(config.sandbox_timeout_sec, 900)
        self.assertEqual(config.trace_storage_path, "/tmp/custom_trace.jsonl")
        self.assertTrue(config.allow_local_execution)

    def test_load_config_from_yaml_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "env: stage\ndefault_scenario: synthetic_research\nsandbox_timeout_sec: 120\n",
                encoding="utf-8",
            )
            config = load_config({}, config_path=str(config_path))
        self.assertEqual(config.env, "stage")
        self.assertEqual(config.default_scenario, "synthetic_research")
        self.assertEqual(config.sandbox_timeout_sec, 120)

    def test_env_overrides_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("env: stage\nallow_local_execution: false\n", encoding="utf-8")
            config = load_config(
                {
                    "AGENTRD_ENV": "prod",
                    "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                },
                config_path=str(config_path),
            )
        self.assertEqual(config.env, "prod")
        self.assertTrue(config.allow_local_execution)

    def test_default_config_path_is_used_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("env: qa\n", encoding="utf-8")
            with patch("app.config._default_config_path", return_value=config_path):
                config = load_config({})
        self.assertEqual(config.env, "qa")

    def test_startup_command_prints_valid_json(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = startup_main()
        self.assertEqual(code, 0)

        payload = json.loads(out.getvalue())
        self.assertIn("default_scenario", payload)
        self.assertIn("trace_storage_path", payload)

    def test_startup_command_supports_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("env: ci\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = startup_main(["--config", str(config_path)])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["env"], "ci")

    def test_required_scaffold_directories_exist(self) -> None:
        required_dirs = [
            "core",
            "core/loop",
            "core/plugins",
            "core/storage",
            "core/execution",
            "scenarios",
            "app",
            "ui",
            "tests",
        ]
        for path in required_dirs:
            self.assertTrue(Path(path).exists(), msg=f"missing scaffold directory: {path}")

    def test_explicit_config_path_to_missing_file_fails_clearly(self) -> None:
        """Explicit config_path pointing to a missing file should raise FileNotFoundError."""
        missing_path = "/nonexistent/path/to/config.yaml"
        with self.assertRaises(FileNotFoundError) as ctx:
            load_config({}, config_path=missing_path)
        self.assertIn("config file not found", str(ctx.exception))
        self.assertIn(missing_path, str(ctx.exception))

    def test_yaml_with_unknown_keys_fails_clearly(self) -> None:
        """YAML containing unknown keys should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "env: dev\nunknown_key_1: value1\nunknown_key_2: value2\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                load_config({}, config_path=str(config_path))
            error_msg = str(ctx.exception)
            self.assertIn("unknown config keys", error_msg)
            self.assertIn("unknown_key_1", error_msg)
            self.assertIn("unknown_key_2", error_msg)

    def test_empty_string_env_variable_is_treated_as_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "env: stage\nsandbox_timeout_sec: 120\nllm_api_key: yaml-key\n",
                encoding="utf-8",
            )
            config = load_config(
                {
                    "AGENTRD_ENV": "",
                    "AGENTRD_SANDBOX_TIMEOUT_SEC": "",
                    "RD_AGENT_LLM_API_KEY": "",
                },
                config_path=str(config_path),
            )
            self.assertEqual(config.env, "stage")
            self.assertEqual(config.sandbox_timeout_sec, 120)
            self.assertEqual(config.llm_api_key, "yaml-key")


if __name__ == "__main__":
    unittest.main()
