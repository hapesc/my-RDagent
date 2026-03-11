from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass

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


_PLACEHOLDER_MARKERS = ("todo", "tbd", "placeholder", "lorem ipsum", "fill in", "{{", "}}")
_QUANTITATIVE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?%?|\bR²\b|\br2\b|correlation|increased by|decreased|higher than|lower than|pearson|×)",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_HEDGING_PHRASES = (
    "it appears",
    "it seems",
    "may possibly",
    "might be",
    "could potentially",
    "it is unclear",
    "further investigation",
    "further research",
    "remains to be seen",
    "warrant further",
    "additional research",
    "further examination",
    "further exploration",
    "more thorough examination",
    "appears to",
    "seems to",
    "probably",
    "somewhat",
    "to some extent",
    "in some ways",
)


def compile_check(code: str) -> bool:
    try:
        compile(code, "<codegen>", "exec")
    except SyntaxError:
        return False
    return True


def has_placeholder(code: str, markers: tuple[str, ...] | None = None) -> bool:
    haystack = code.lower()
    return any(marker in haystack for marker in markers or _PLACEHOLDER_MARKERS)


def has_forbidden_import(code: str, forbidden: list[str]) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    forbidden_set = set(forbidden)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in forbidden_set:
                    return True
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".", 1)[0] in forbidden_set:
            return True
    return False


def has_required_signature(code: str, function_name: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    return any(isinstance(node, ast.FunctionDef) and node.name == function_name for node in ast.walk(tree))


def count_quantitative_claims(text: str) -> int:
    count = 0
    for sentence in _split_sentences(text):
        normalized = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", sentence)
        if _QUANTITATIVE_PATTERN.search(normalized):
            count += 1
    return count


def hedging_ratio(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 0.0
    hedging_count = sum(1 for sentence in sentences if any(phrase in sentence.lower() for phrase in _HEDGING_PHRASES))
    return hedging_count / len(sentences)


def has_structural_markers(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)


def _split_sentences(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in _SENTENCE_SPLIT_RE.split(text.strip()) if chunk.strip()]
    if chunks:
        return chunks
    stripped = text.strip()
    return [stripped] if stripped else []
