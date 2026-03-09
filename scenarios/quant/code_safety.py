"""AST-based code safety validator for factor code submitted by the LLM."""

from __future__ import annotations

import ast
from typing import Optional

from .constants import BLOCKED_IMPORTS, SAFE_IMPORTS

_DANGEROUS_BUILTINS: frozenset[str] = frozenset(
    {"exec", "eval", "compile", "__import__", "open", "globals", "locals", "vars", "dir"}
)


def validate_code_safety(code: str) -> tuple[bool, Optional[str]]:
    """Validate that *code* is safe to execute in the backtest sandbox.

    Returns:
        (True, None)        — code passes all checks
        (False, reason_str) — code fails; reason_str explains why
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            reason = _check_import_node(node)
            if reason:
                return False, reason

        if isinstance(node, ast.Call):
            reason = _check_call_node(node)
            if reason:
                return False, reason

        if isinstance(node, ast.Name) and node.id in _DANGEROUS_BUILTINS:
            if isinstance(node.ctx, ast.Load):
                return False, f"Dangerous builtin reference: '{node.id}'"

    return True, None


def _check_import_node(node: ast.Import | ast.ImportFrom) -> Optional[str]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in BLOCKED_IMPORTS:
                return f"Blocked import: '{alias.name}'"
            if top not in SAFE_IMPORTS:
                return f"Import not in allowlist: '{alias.name}'"
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        top = module.split(".")[0]
        if top in BLOCKED_IMPORTS:
            return f"Blocked import: '{module}'"
        if top and top not in SAFE_IMPORTS:
            return f"Import not in allowlist: '{module}'"
    return None


def _check_call_node(node: ast.Call) -> Optional[str]:
    if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_BUILTINS:
        return f"Dangerous builtin call: '{node.func.id}()'"
    if isinstance(node.func, ast.Attribute):
        if node.func.attr in _DANGEROUS_BUILTINS:
            return f"Dangerous attribute call: '.{node.func.attr}()'"
    return None
