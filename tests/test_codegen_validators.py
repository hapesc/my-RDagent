from __future__ import annotations

from dataclasses import is_dataclass
from importlib import import_module
from typing import Any

from llm.codegen.validators import (
    compile_check,
    count_quantitative_claims,
    function_body_nontrivial,
    function_has_return,
    function_uses_parameter,
    has_forbidden_import,
    has_placeholder,
    has_required_signature,
    has_structural_markers,
    hedging_ratio,
)


def _imports():
    module = import_module("llm.codegen.validators")
    ValidationResult = module.ValidationResult
    validate_compile = module.validate_compile
    detect_placeholders = module.detect_placeholders
    validate_content = module.validate_content
    validate_pipeline = module.validate_pipeline

    return ValidationResult, validate_compile, detect_placeholders, validate_content, validate_pipeline


def _assert_validation_result_shape(result: Any, ValidationResult: Any):
    assert isinstance(result, ValidationResult), "result must be ValidationResult"
    assert is_dataclass(result), "ValidationResult should be a dataclass"
    valid = result.valid
    errors = result.errors
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


def test_compile_check_accepts_valid_code() -> None:
    assert compile_check("def foo():\n    return 42") is True


def test_compile_check_rejects_syntax_error() -> None:
    assert compile_check("def foo(") is False


def test_placeholder_detector_catches_todo() -> None:
    assert has_placeholder("def foo():\n    # TODO: implement\n    pass") is True


def test_placeholder_detector_passes_real_code() -> None:
    assert has_placeholder("def foo():\n    return sum(range(10))") is False


def test_forbidden_import_detector_catches_os() -> None:
    code = "import os\nos.system('rm -rf /')"
    assert has_forbidden_import(code, forbidden=["os", "subprocess"]) is True


def test_forbidden_import_detector_passes_clean_code() -> None:
    assert has_forbidden_import("import pandas as pd", forbidden=["os", "subprocess"]) is False


def test_signature_check_passes_matching() -> None:
    assert has_required_signature("def compute_factor(df):\n    pass", "compute_factor") is True


def test_signature_check_fails_missing() -> None:
    assert has_required_signature("def other_func(x):\n    pass", "compute_factor") is False


def test_quantitative_claims_counts_numbers() -> None:
    text = "Temperature rose by 0.18°C per decade. The correlation is 0.95."
    assert count_quantitative_claims(text) == 2


def test_quantitative_claims_zero_for_vague_prose() -> None:
    text = "The results suggest interesting patterns. Further research is needed."
    assert count_quantitative_claims(text) == 0


def test_hedging_ratio_high_for_weasel_text() -> None:
    text = "It appears that trends may possibly exist. It seems likely that variables might be correlated."
    assert hedging_ratio(text) > 0.5


def test_hedging_ratio_low_for_concrete_text() -> None:
    text = "Temperature increased by 0.18°C per decade. CO2 correlation is 0.95."
    assert hedging_ratio(text) < 0.1


def test_structural_markers_found() -> None:
    assert has_structural_markers("## Findings\n1. First result", ["##", "1."]) is True


def test_structural_markers_missing_numbering() -> None:
    assert has_structural_markers("## Findings\nSome prose here", ["##", "1."]) is False


# --- function_uses_parameter ---


def test_function_uses_parameter_true():
    code = "def compute_factor(df):\n    return df['close'].pct_change(5)\n"
    assert function_uses_parameter(code, "compute_factor", "df") is True


def test_function_uses_parameter_false():
    code = "def compute_factor(df):\n    return 42\n"
    assert function_uses_parameter(code, "compute_factor", "df") is False


def test_function_uses_parameter_identity_return():
    """Bare `return df` still counts as 'using' the parameter."""
    code = "def compute_factor(df):\n    return df\n"
    assert function_uses_parameter(code, "compute_factor", "df") is True


def test_function_uses_parameter_missing_function():
    code = "def other(x):\n    return x\n"
    assert function_uses_parameter(code, "compute_factor", "df") is False


# --- function_has_return ---


def test_function_has_return_true():
    code = "def compute_factor(df):\n    return df\n"
    assert function_has_return(code, "compute_factor") is True


def test_function_has_return_false_pass():
    code = "def compute_factor(df):\n    pass\n"
    assert function_has_return(code, "compute_factor") is False


def test_function_has_return_false_sideeffect():
    code = "def compute_factor(df):\n    print(df)\n"
    assert function_has_return(code, "compute_factor") is False


# --- function_body_nontrivial ---


def test_body_nontrivial_real_code():
    code = "def compute_factor(df):\n    return df.groupby('stock_id')['close'].pct_change(5)\n"
    assert function_body_nontrivial(code, "compute_factor") is True


def test_body_nontrivial_rejects_pass():
    assert function_body_nontrivial("def f(df):\n    pass\n", "f") is False


def test_body_nontrivial_rejects_ellipsis():
    assert function_body_nontrivial("def f(df):\n    ...\n", "f") is False


def test_body_nontrivial_rejects_identity_return():
    assert function_body_nontrivial("def f(df):\n    return df\n", "f") is False


def test_body_nontrivial_rejects_return_none():
    assert function_body_nontrivial("def f(df):\n    return None\n", "f") is False


def test_body_nontrivial_accepts_two_line_body():
    code = "def f(df):\n    x = df + 1\n    return x\n"
    assert function_body_nontrivial(code, "f") is True
