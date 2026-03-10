from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

DEFAULT_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {
        "todo",
        "tbd",
        "lorem ipsum",
        "placeholder",
        "fill in",
        "insert here",
        "{{",
        "}}",
    }
)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    validator_name: str = ""


def validate_compile(code: str) -> ValidationResult:
    if not code or not code.strip():
        return ValidationResult(
            valid=False,
            errors=["Code is empty"],
            validator_name="validate_compile",
        )
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Compile/Syntax validation failed: {exc}"],
            validator_name="validate_compile",
        )
    except Exception as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Compile validation failed: {exc}"],
            validator_name="validate_compile",
        )
    return ValidationResult(valid=True, errors=[], validator_name="validate_compile")


def detect_placeholders(code: str, tokens: set[str] | None = None) -> ValidationResult:
    token_set = tokens or DEFAULT_PLACEHOLDER_TOKENS
    normalized_code = code.lower()

    detected: list[str] = []
    for token in sorted(token_set):
        normalized_token = token.lower()
        if re.fullmatch(r"[a-z0-9_]+", normalized_token):
            pattern = rf"\b{re.escape(normalized_token)}\b"
            if re.search(pattern, normalized_code):
                detected.append(token)
        elif normalized_token in normalized_code:
            detected.append(token)

    if detected:
        return ValidationResult(
            valid=False,
            errors=[f"Placeholder tokens detected: {', '.join(detected)}"],
            validator_name="detect_placeholders",
        )
    return ValidationResult(valid=True, errors=[], validator_name="detect_placeholders")


def validate_content(code: str, required_patterns: list[str]) -> ValidationResult:
    errors: list[str] = []

    if not code or not code.strip():
        errors.append("Code content is empty")

    for pattern in required_patterns:
        if pattern not in code:
            errors.append(f"Missing required pattern: {pattern}")

    return ValidationResult(
        valid=not errors,
        errors=errors,
        validator_name="validate_content",
    )


def validate_pipeline(code: str, validators: list[Callable[[str], ValidationResult]]) -> ValidationResult:
    for validator in validators:
        result = validator(code)
        if not result.valid:
            return result
    return ValidationResult(valid=True, errors=[], validator_name="validate_pipeline")
