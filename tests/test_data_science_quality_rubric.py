from __future__ import annotations

from scenarios.data_science.plugin import evaluate_data_science_quality


def test_metrics_with_accuracy_passes() -> None:
    metrics = {"accuracy": 0.91, "row_count": 100, "column_count": 8}
    code = "from sklearn.ensemble import RandomForestClassifier\n\ndef main():\n    return 1\n"
    assert evaluate_data_science_quality(code=code, metrics=metrics).passed is True


def test_row_count_only_metrics_fail() -> None:
    metrics = {"row_count": 100, "column_count": 8, "status": "ok"}
    result = evaluate_data_science_quality(code="import csv", metrics=metrics)
    assert result.passed is False
    assert "missing experiment metric" in result.reasons[0]


def test_placeholder_pipeline_fails_even_with_good_metrics() -> None:
    code = "# TODO: implement real pipeline\npass"
    metrics = {"accuracy": 0.91}
    result = evaluate_data_science_quality(code=code, metrics=metrics)
    assert result.passed is False


def test_template_only_pipeline_fails() -> None:
    code = "row_count = 0\ncolumn_count = 0\ncsv.DictReader([])"
    metrics = {"row_count": 50, "column_count": 5, "status": "ok"}
    result = evaluate_data_science_quality(code=code, metrics=metrics)
    assert result.passed is False
