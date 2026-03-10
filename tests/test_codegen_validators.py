from __future__ import annotations

from dataclasses import is_dataclass
from importlib import import_module
from typing import Any


def _imports():
    module = import_module("llm.codegen.validators")
    ValidationResult = getattr(module, "ValidationResult")
    validate_compile = getattr(module, "validate_compile")
    detect_placeholders = getattr(module, "detect_placeholders")
    validate_content = getattr(module, "validate_content")
    validate_pipeline = getattr(module, "validate_pipeline")

    return ValidationResult, validate_compile, detect_placeholders, validate_content, validate_pipeline


def _assert_validation_result_shape(result: Any, ValidationResult: Any):
    assert isinstance(result, ValidationResult), "result must be ValidationResult"
    assert is_dataclass(result), "ValidationResult should be a dataclass"
    valid = getattr(result, "valid", None)
    errors = getattr(result, "errors", None)
    assert isinstance(valid, bool), "ValidationResult.valid must be bool"
    assert isinstance(errors, list), "ValidationResult.errors must be list"
    assert all(isinstance(item, str) for item in errors), "ValidationResult.errors must be list[str]"


def test_compile_validator_valid_code():
    ValidationResult, validate_compile, _, _, _ = _imports()
    code = "def add(a, b):\n    return a + b\n"

    result = validate_compile(code)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_compile_validator_syntax_error():
    ValidationResult, validate_compile, _, _, _ = _imports()
    code = "def broken(:\n    return 1\n"

    result = validate_compile(code)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    joined = " ".join(result.errors).lower()
    assert "syntax" in joined or "compile" in joined


def test_placeholder_detector_clean():
    ValidationResult, _, detect_placeholders, _, _ = _imports()
    code = "def signal(df):\n    return df['close'].pct_change(5)\n"
    tokens = {"todo", "tbd", "placeholder", "template", "n/a", "na", "unknown", "null"}

    result = detect_placeholders(code, tokens=tokens)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_placeholder_detector_todo():
    ValidationResult, _, detect_placeholders, _, _ = _imports()
    code = "# TODO: implement alpha\ndef alpha(df):\n    return df\n"
    tokens = {"todo", "tbd", "placeholder", "template", "n/a", "na", "unknown", "null"}

    result = detect_placeholders(code, tokens=tokens)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    assert "todo" in " ".join(result.errors).lower()


def test_placeholder_detector_template_tokens():
    ValidationResult, _, detect_placeholders, _, _ = _imports()
    code = "# placeholder for template output\nvalue = 'n/a'\nflag = 'TBD'\n"
    tokens = {"todo", "tbd", "placeholder", "template", "n/a", "na", "unknown", "null"}

    result = detect_placeholders(code, tokens=tokens)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    lowered = " ".join(result.errors).lower()
    assert "placeholder" in lowered or "template" in lowered or "tbd" in lowered or "n/a" in lowered


def test_content_validator_has_function():
    ValidationResult, _, _, validate_content, _ = _imports()
    code = "def compute_factor(df):\n    return df['close'].pct_change(3)\n"

    result = validate_content(code, required_patterns=["def compute_factor("])

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_content_validator_missing_function():
    ValidationResult, _, _, validate_content, _ = _imports()
    code = "def helper(df):\n    return df\n"

    result = validate_content(code, required_patterns=["def compute_factor("])

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    assert "compute_factor" in " ".join(result.errors)


def test_content_validator_empty_code():
    ValidationResult, _, _, validate_content, _ = _imports()
    result = validate_content("", required_patterns=["def compute_factor("])

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    assert result.errors, "empty code must produce at least one error"


def test_ast_safety_not_blocking_imports():
    ValidationResult, _, _, _, validate_pipeline = _imports()
    from scenarios.quant.code_safety import validate_code_safety

    code = (
        "import numpy as np\nimport pandas as pd\n\ndef compute_factor(df):\n    return df['close'].rolling(5).mean()\n"
    )

    def ast_safety_validator(src: str):
        ok, reason = validate_code_safety(src)
        if ok:
            return ValidationResult(valid=True, errors=[])
        return ValidationResult(valid=False, errors=[reason or "ast safety failed"])

    result = validate_pipeline(code, validators=[ast_safety_validator])

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_full_pipeline_valid():
    ValidationResult, validate_compile, detect_placeholders, validate_content, validate_pipeline = _imports()
    code = "import numpy as np\n\ndef compute_factor(df):\n    return df['close'].pct_change(5)\n"
    tokens = {"todo", "tbd", "placeholder", "template", "n/a", "na", "unknown", "null"}

    validators = [
        validate_compile,
        lambda src: detect_placeholders(src, tokens=tokens),
        lambda src: validate_content(src, required_patterns=["def compute_factor("]),
    ]
    result = validate_pipeline(code, validators=validators)

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_full_pipeline_first_failure_stops():
    ValidationResult, _, _, _, validate_pipeline = _imports()

    calls = {"second": 0}

    def first_fail_validator(_src: str):
        return ValidationResult(valid=False, errors=["first failed"])

    def second_validator(_src: str):
        calls["second"] += 1
        return ValidationResult(valid=True, errors=[])

    result = validate_pipeline("print('x')", validators=[first_fail_validator, second_validator])

    _assert_validation_result_shape(result, ValidationResult)
    assert result.valid is False
    assert "first failed" in " ".join(result.errors).lower()
    assert calls["second"] == 0, "pipeline must stop after first failure"
