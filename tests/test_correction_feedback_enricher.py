"""Tests for shared feedback enrichment logic."""

from __future__ import annotations

import unittest


class TestEnrichFeedbackContext(unittest.TestCase):
    def test_no_feedback_returns_summary_unchanged(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        result = enrich_feedback_context("my proposal", {})
        self.assertEqual(result, "my proposal")

    def test_plain_costeer_feedback_appended(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {"_costeer_feedback": "code had syntax error"}
        result = enrich_feedback_context("my proposal", hypothesis)
        self.assertIn("my proposal", result)
        self.assertIn("code had syntax error", result)

    def test_fc3_structured_feedback_all_dimensions(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {
            "_costeer_feedback": "overall reasoning",
            "_costeer_feedback_execution": "exit code 1",
            "_costeer_feedback_code": "missing import",
            "_costeer_feedback_return": "no output file",
            "_costeer_round": 2,
        }
        result = enrich_feedback_context("proposal text", hypothesis)
        self.assertIn("exit code 1", result)
        self.assertIn("missing import", result)
        self.assertIn("no output file", result)
        self.assertIn("overall reasoning", result)

    def test_fc3_partial_dimensions(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {
            "_costeer_feedback": "reasoning only",
            "_costeer_feedback_execution": "timeout",
            "_costeer_round": 1,
        }
        result = enrich_feedback_context("proposal", hypothesis)
        self.assertIn("timeout", result)
        self.assertIn("reasoning only", result)
        self.assertNotIn("Code Quality", result)
        self.assertNotIn("Output Check", result)

    def test_code_source_failed_adds_warning(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {"_code_source": "failed"}
        result = enrich_feedback_context("proposal", hypothesis)
        self.assertIn("FAILED", result.upper())
        self.assertIn("fallback", result.lower())

    def test_code_source_llm_no_warning(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {"_code_source": "llm"}
        result = enrich_feedback_context("proposal", hypothesis)
        self.assertNotIn("FAILED", result)

    def test_empty_feedback_strings_ignored(self) -> None:
        from core.correction.feedback_enricher import enrich_feedback_context

        hypothesis = {
            "_costeer_feedback": "",
            "_costeer_feedback_execution": "  ",
            "_costeer_round": 1,
        }
        result = enrich_feedback_context("proposal", hypothesis)
        self.assertEqual(result, "proposal")


if __name__ == "__main__":
    unittest.main()
