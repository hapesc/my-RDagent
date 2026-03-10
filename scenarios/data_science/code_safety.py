from __future__ import annotations

import ast
from dataclasses import dataclass

_BLOCKED_IMPORTS: frozenset[str] = frozenset({"os", "subprocess", "shutil", "sys", "socket", "ctypes"})

_SAFE_IMPORTS: frozenset[str] = frozenset(
    {
        "pandas",
        "numpy",
        "sklearn",
        "scipy",
        "json",
        "csv",
        "pathlib",
        "math",
        "statistics",
        "collections",
        "itertools",
        "functools",
    }
)

_DANGEROUS_CALLS: frozenset[str] = frozenset({"eval", "exec", "compile", "__import__"})

_DANGEROUS_ATTRIBUTES: frozenset[str] = frozenset({"os.system", "os.popen", "subprocess.run", "subprocess.Popen"})


@dataclass(frozen=True)
class SafetyResult:
    safe: bool
    violations: list[str]


def validate_code_safety(code: str) -> SafetyResult:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SafetyResult(safe=False, violations=[f"SyntaxError: {exc}"])

    violations: list[str] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _append_violation(violations, seen, _check_import_node(node))

        if isinstance(node, ast.Call):
            _append_violation(violations, seen, _check_call_node(node))

    return SafetyResult(safe=not violations, violations=violations)


def _append_violation(violations: list[str], seen: set[str], reason: str | None) -> None:
    if reason and reason not in seen:
        seen.add(reason)
        violations.append(reason)


def _check_import_node(node: ast.Import | ast.ImportFrom) -> str | None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            reason = _check_import_name(top, alias.name)
            if reason:
                return reason
    else:
        module = node.module or ""
        top = module.split(".")[0]
        if top:
            return _check_import_name(top, module)
    return None


def _check_import_name(top: str, full_name: str) -> str | None:
    if top in _BLOCKED_IMPORTS:
        return f"Blocked import: '{full_name}'"
    if top not in _SAFE_IMPORTS:
        return f"Import not in allowlist: '{full_name}'"
    return None


def _check_call_node(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        if node.func.id in _DANGEROUS_CALLS:
            return f"Dangerous builtin call: '{node.func.id}()'"
        if node.func.id == "open" and _is_write_mode_open_call(node):
            return "Dangerous file write call: 'open()'"

    dotted_name = _dotted_name(node.func)
    if dotted_name in _DANGEROUS_ATTRIBUTES:
        return f"Dangerous attribute call: '{dotted_name}()'"

    return None


def _is_write_mode_open_call(node: ast.Call) -> bool:
    mode_value: str | None = None

    if len(node.args) >= 2:
        mode_value = _constant_str(node.args[1])

    if mode_value is None:
        for keyword in node.keywords:
            if keyword.arg == "mode":
                mode_value = _constant_str(keyword.value)
                break

    if mode_value is None:
        return False

    return any(flag in mode_value for flag in ("w", "a", "x", "+"))


def _constant_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None
