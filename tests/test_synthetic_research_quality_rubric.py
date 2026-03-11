from __future__ import annotations

from scenarios.synthetic_research.plugin import evaluate_synthetic_quality


def test_structured_findings_pass() -> None:
    output = "## Findings\n1. Model accuracy improved by 15%\n2. Feature X is most predictive"
    assert evaluate_synthetic_quality(output=output).passed is True


def test_task_restatement_only_fails() -> None:
    output = "The task is to analyze the dataset and find patterns."
    result = evaluate_synthetic_quality(output=output)
    assert result.passed is False
    assert "restatement" in result.reasons[0].lower() or "no findings" in result.reasons[0].lower()


def test_empty_summary_fails() -> None:
    assert evaluate_synthetic_quality(output="").passed is False


def test_placeholder_findings_fail() -> None:
    output = "## Findings\n1. TODO: fill in results\n2. TBD"
    result = evaluate_synthetic_quality(output=output)
    assert result.passed is False
