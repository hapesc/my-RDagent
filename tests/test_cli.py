"""Tests for the quick-start CLI."""

from __future__ import annotations

import contextlib
import io
import logging
import sys
import unittest
from unittest.mock import MagicMock, patch

from cli import main

from tests._llm_test_utils import patch_runtime_llm_provider


class TestCli(unittest.TestCase):
    def test_dry_run_logs_config(self):
        with patch_runtime_llm_provider(), self.assertLogs("cli", level="INFO") as cm:
            result = main(["--task", "test task", "--dry-run"])

        assert result == 0
        log_text = "\n".join(cm.output)
        assert "scenario: data_science" in log_text
        assert "llm_provider: mock" in log_text
        assert "dry-run: exiting without starting loop" in log_text

    def test_scenario_override(self):
        with patch_runtime_llm_provider(), self.assertLogs("cli", level="INFO") as cm:
            result = main(["--task", "t", "--scenario", "synthetic_research", "--dry-run"])

        assert result == 0
        log_text = "\n".join(cm.output)
        assert "scenario: synthetic_research" in log_text

    def test_help_contains_all_flags(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                main(["--help"])
            except SystemExit:
                pass

        help_text = output.getvalue()
        assert "--scenario" in help_text
        assert "--task" in help_text
        assert "--max-steps" in help_text
        assert "--dry-run" in help_text


if __name__ == "__main__":
    unittest.main()
