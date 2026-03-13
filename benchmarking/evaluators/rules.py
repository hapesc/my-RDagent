"""Pure-Python structural rule evaluators for benchmark cases."""

from __future__ import annotations

import ast
from typing import Any


def evaluate_python_syntax(code: str) -> dict[str, Any]:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return {"passed": False, "reason": f"syntax error: {exc.msg}"}
    return {"passed": True, "reason": "syntax valid"}


def evaluate_forbidden_imports(code: str, forbidden_imports: tuple[str, ...]) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"passed": False, "forbidden_imports": [], "reason": f"syntax error: {exc.msg}"}
    banned: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in forbidden_imports and root not in banned:
                    banned.append(root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in forbidden_imports and root not in banned:
                banned.append(root)
    return {
        "passed": not banned,
        "forbidden_imports": banned,
        "reason": "no forbidden imports" if not banned else f"forbidden imports: {', '.join(banned)}",
    }


def evaluate_required_function_signatures(code: str, required_functions: tuple[str, ...]) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"passed": False, "missing_functions": list(required_functions), "reason": f"syntax error: {exc.msg}"}
    present = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    missing = [name for name in required_functions if name not in present]
    return {
        "passed": not missing,
        "missing_functions": missing,
        "reason": "all required functions present" if not missing else f"missing functions: {', '.join(missing)}",
    }


def evaluate_required_outputs(
    *,
    outputs: dict[str, Any],
    artifact_refs: dict[str, Any],
    required_output_keys: tuple[str, ...] = (),
    required_artifact_refs: tuple[str, ...] = (),
) -> dict[str, Any]:
    missing_output_keys = [key for key in required_output_keys if key not in outputs]
    missing_artifact_refs = [key for key in required_artifact_refs if key not in artifact_refs]
    passed = not missing_output_keys and not missing_artifact_refs
    return {
        "passed": passed,
        "missing_output_keys": missing_output_keys,
        "missing_artifact_refs": missing_artifact_refs,
        "reason": "required outputs present" if passed else "missing required outputs",
    }
