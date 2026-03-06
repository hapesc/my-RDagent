"""Task-05 tests for scaffolding and configuration loading."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.config import load_config
from app.startup import main as startup_main


class ConfigLayerTests(unittest.TestCase):
    def test_load_config_defaults(self) -> None:
        config = load_config({})
        self.assertEqual(config.env, "dev")
        self.assertEqual(config.default_scenario, "data_science")
        self.assertEqual(config.sandbox_timeout_sec, 300)

    def test_load_config_from_env_map(self) -> None:
        config = load_config(
            {
                "AGENTRD_ENV": "prod",
                "AGENTRD_DEFAULT_SCENARIO": "custom",
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "900",
                "AGENTRD_TRACE_STORAGE_PATH": "/tmp/custom_trace.jsonl",
            }
        )
        self.assertEqual(config.env, "prod")
        self.assertEqual(config.default_scenario, "custom")
        self.assertEqual(config.sandbox_timeout_sec, 900)
        self.assertEqual(config.trace_storage_path, "/tmp/custom_trace.jsonl")

    def test_startup_command_prints_valid_json(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = startup_main()
        self.assertEqual(code, 0)

        payload = json.loads(out.getvalue())
        self.assertIn("default_scenario", payload)
        self.assertIn("trace_storage_path", payload)

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


if __name__ == "__main__":
    unittest.main()
