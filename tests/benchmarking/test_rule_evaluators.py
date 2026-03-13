from __future__ import annotations

from benchmarking.evaluators.rules import (
    evaluate_forbidden_imports,
    evaluate_python_syntax,
    evaluate_required_function_signatures,
    evaluate_required_outputs,
)


def test_evaluate_python_syntax_accepts_valid_python() -> None:
    result = evaluate_python_syntax("def compute_factor(df):\n    return df\n")

    assert result["passed"] is True
    assert result["reason"] == "syntax valid"


def test_evaluate_python_syntax_rejects_invalid_python() -> None:
    result = evaluate_python_syntax("def broken(:\n    pass\n")

    assert result["passed"] is False
    assert "syntax error" in result["reason"].lower()


def test_evaluate_forbidden_imports_rejects_banned_modules() -> None:
    code = "import os\nfrom subprocess import run\n"

    result = evaluate_forbidden_imports(code, forbidden_imports=("os", "subprocess"))

    assert result["passed"] is False
    assert result["forbidden_imports"] == ["os", "subprocess"]


def test_evaluate_forbidden_imports_accepts_allowed_modules() -> None:
    result = evaluate_forbidden_imports("import math\n", forbidden_imports=("os", "subprocess"))

    assert result["passed"] is True
    assert result["forbidden_imports"] == []


def test_evaluate_required_function_signatures_requires_expected_function() -> None:
    code = "def other_name(df):\n    return df\n"

    result = evaluate_required_function_signatures(code, required_functions=("compute_factor",))

    assert result["passed"] is False
    assert result["missing_functions"] == ["compute_factor"]


def test_evaluate_required_function_signatures_accepts_expected_function() -> None:
    result = evaluate_required_function_signatures(
        "def compute_factor(df):\n    return df\n",
        required_functions=("compute_factor",),
    )

    assert result["passed"] is True
    assert result["missing_functions"] == []


def test_evaluate_required_outputs_checks_output_keys_and_files() -> None:
    outputs = {"metrics": {"accuracy": 0.9}}
    artifact_refs = {"report": "artifacts/report.md"}

    result = evaluate_required_outputs(
        outputs=outputs,
        artifact_refs=artifact_refs,
        required_output_keys=("metrics", "summary"),
        required_artifact_refs=("report", "metrics_json"),
    )

    assert result["passed"] is False
    assert result["missing_output_keys"] == ["summary"]
    assert result["missing_artifact_refs"] == ["metrics_json"]


def test_evaluate_required_outputs_accepts_present_output_keys_and_files() -> None:
    result = evaluate_required_outputs(
        outputs={"metrics": {"accuracy": 0.9}},
        artifact_refs={"report": "artifacts/report.md", "metrics_json": "artifacts/metrics.json"},
        required_output_keys=("metrics",),
        required_artifact_refs=("report", "metrics_json"),
    )

    assert result["passed"] is True
    assert result["missing_output_keys"] == []
    assert result["missing_artifact_refs"] == []
