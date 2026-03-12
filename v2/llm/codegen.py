from __future__ import annotations

import re

_PYTHON_FENCE_BLOCK_RE = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code_blocks(text: str) -> list[str]:
    return [match.strip() for match in _PYTHON_FENCE_BLOCK_RE.findall(text) if match.strip()]


def extract_first_code(text: str) -> str:
    blocks = extract_code_blocks(text)
    if not blocks:
        raise ValueError("No python code block found")
    return blocks[0]


def validate_code(code: str) -> bool:
    if not code.strip():
        return False
    try:
        compile(code, "<v2-llm-codegen>", "exec")
    except SyntaxError:
        return False
    return True
