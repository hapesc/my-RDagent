"""Redaction helpers for logs and traces."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "token",
    "password",
    "secret",
    "authorization",
    "access_key",
    "private_key",
)


def _is_sensitive_key(key: str, sensitive_keywords: Iterable[str]) -> bool:
    lowered = key.lower()
    return any(keyword in lowered for keyword in sensitive_keywords)


def sanitize_payload(
    payload: Any,
    sensitive_keywords: Iterable[str] = SENSITIVE_KEYWORDS,
    redacted_value: str = "***",
) -> Any:
    """Recursively redact sensitive fields in nested payloads."""

    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if _is_sensitive_key(str(key), sensitive_keywords):
                sanitized[key] = redacted_value
            else:
                sanitized[key] = sanitize_payload(value, sensitive_keywords, redacted_value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_payload(item, sensitive_keywords, redacted_value) for item in payload]
    return payload
