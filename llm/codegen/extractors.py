from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from llm.adapter import _CODE_BLOCK_RE, _JSON_BLOCK_RE, _JSON_BLOCK_UNCLOSED_RE

_UNCLOSED_CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n?(.*)$", re.DOTALL)
_ARTIFACT_FIELD_RE = re.compile(r'"artifact"\s*:\s*"(?P<artifact>.*)', re.DOTALL)

# Keys that LLMs commonly use when wrapping code in JSON instead of fenced blocks
_CODE_JSON_KEYS = (
    "artifact",
    "code",
    "python_code",
    "python",
    "implementation",
    "source_code",
    "python_function",
    "factor_implementation",
)

# Pre-compiled patterns for each code JSON key — matches `"key" : "` (value start)
_TRUNCATED_JSON_KEY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf'"{k}"\s*:\s*"', re.IGNORECASE) for k in _CODE_JSON_KEYS
)


_FENCED_BLOCK_WRAPPER_RE = re.compile(r"^\s*```(?:python|py)?\s*\n(.*?)(?:\n\s*```\s*)?$", re.DOTALL)


@dataclass(frozen=True)
class ExtractedCode:
    code: str
    metadata: dict[str, object] = field(default_factory=dict)
    source: str = "raw_fallback"


def extract_code_block(raw: str) -> str | None:
    if not raw or not raw.strip():
        return None

    match = _CODE_BLOCK_RE.search(raw)
    if match is not None:
        code = match.group(2).strip()
        return code or None

    truncated = _UNCLOSED_CODE_BLOCK_RE.search(raw)
    if truncated is not None:
        code = truncated.group(1).strip()
        return code or None

    return None


def extract_code_and_metadata(raw: str) -> ExtractedCode:
    metadata = _extract_metadata(raw)
    code = _extract_code_from_metadata(metadata)
    if not code:
        code = (
            _extract_code_from_truncated_json(raw)
            or _extract_artifact_field_fallback(raw)
            or extract_code_block(raw)
            or ""
        )
    if metadata and code:
        source = "json_plus_block"
    elif code:
        source = "fenced_block"
    else:
        source = "raw_fallback"
    return ExtractedCode(code=code, metadata=metadata, source=source)


def _strip_fenced_wrapper(text: str) -> str:
    match = _FENCED_BLOCK_WRAPPER_RE.match(text)
    return match.group(1).strip() if match else text


def _extract_code_from_metadata(metadata: dict[str, object]) -> str:
    """Try common JSON keys that LLMs use to wrap code."""
    for key in _CODE_JSON_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _strip_fenced_wrapper(value.strip())
    return ""


def _extract_code_from_truncated_json(raw: str) -> str | None:
    """Extract code value from truncated JSON where json.loads() fails.

    When max_tokens truncates the response mid-JSON, the standard JSON parser
    can't handle it. This scans for known code key patterns and manually
    extracts the string value by walking escape sequences.
    """
    best: str | None = None
    best_len = 0
    for pat in _TRUNCATED_JSON_KEY_PATTERNS:
        match = pat.search(raw)
        if match is None:
            continue
        value = _unescape_json_string_value(raw, match.end())
        if value and len(value) > best_len:
            best = value
            best_len = len(value)
    if best is not None:
        best = _strip_fenced_wrapper(best.strip())
    return best or None


def _unescape_json_string_value(raw: str, start: int) -> str:
    """Read a JSON string value starting at *start* (just past the opening quote).

    Handles \\n, \\t, \\", \\\\. Stops at unescaped '"' or end-of-string.
    """
    parts: list[str] = []
    i = start
    length = len(raw)
    _ESCAPE_MAP = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}
    while i < length:
        ch = raw[i]
        if ch == '"':
            break
        if ch == "\\" and i + 1 < length:
            nxt = raw[i + 1]
            parts.append(_ESCAPE_MAP.get(nxt, f"\\{nxt}"))
            i += 2
            continue
        parts.append(ch)
        i += 1
    return "".join(parts)


def _extract_metadata(raw: str) -> dict[str, object]:
    stripped = raw.strip()
    if not stripped:
        return {}

    decoder = json.JSONDecoder()
    if stripped.startswith("{"):
        try:
            payload, _ = decoder.raw_decode(stripped)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items()}

    for pattern in (_JSON_BLOCK_RE, _JSON_BLOCK_UNCLOSED_RE):
        match = pattern.search(raw)
        if match is None:
            continue
        candidate = match.group(1).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items()}

    return {}


def _extract_artifact_field_fallback(raw: str) -> str | None:
    match = _ARTIFACT_FIELD_RE.search(raw)
    if match is None:
        return None
    artifact = match.group("artifact")
    artifact = artifact.replace("\\n", "\n").replace('\\"', '"').replace("\\t", "\t").replace("\\\\", "\\")
    artifact = artifact.strip()
    return artifact or None
