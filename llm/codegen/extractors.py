from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from llm.adapter import _CODE_BLOCK_RE, _JSON_BLOCK_RE, _JSON_BLOCK_UNCLOSED_RE

_UNCLOSED_CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n?(.*)$", re.DOTALL)
_ARTIFACT_FIELD_RE = re.compile(r'"artifact"\s*:\s*"(?P<artifact>.*)', re.DOTALL)


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
    artifact_from_metadata = metadata.get("artifact")
    if isinstance(artifact_from_metadata, str) and artifact_from_metadata.strip():
        code = artifact_from_metadata.strip()
    else:
        code = _extract_artifact_field_fallback(raw) or extract_code_block(raw) or ""
    if metadata and code:
        source = "json_plus_block"
    elif code:
        source = "fenced_block"
    else:
        source = "raw_fallback"
    return ExtractedCode(code=code, metadata=metadata, source=source)


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
