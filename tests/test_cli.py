"""Tests for the deprecated quick-start CLI."""

from __future__ import annotations

import unittest

from cli import main


class TestCli(unittest.TestCase):
    def test_cli_is_deprecated_and_returns_nonzero(self):
        with self.assertLogs("cli", level="ERROR") as cm:
            result = main(["--task", "test task"])

        assert result != 0
        assert "deprecated" in "\n".join(cm.output).lower()


if __name__ == "__main__":
    unittest.main()
