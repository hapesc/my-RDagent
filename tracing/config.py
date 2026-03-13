"""LangSmith tracing configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping


def _get_bool(environ: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be a boolean string")


@dataclass(frozen=True)
class TracingConfig:
    """Benchmark-aware tracing settings."""

    enabled: bool
    upload_enabled: bool
    project: str
    suite: str
    api_key: str | None = None
    endpoint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_tracing_metadata(*, project: str, suite: str, environ: Mapping[str, str]) -> dict[str, Any]:
    return {
        "project": project,
        "suite": suite,
        "env": environ.get("AGENTRD_ENV", "dev"),
    }


def load_tracing_config(environ: Mapping[str, str] | None = None) -> TracingConfig | None:
    resolved_environ = environ or os.environ
    enabled = _get_bool(resolved_environ, "LANGSMITH_TRACING", False)
    if not enabled:
        return None

    project = resolved_environ.get("LANGSMITH_PROJECT", "rdagent")
    suite = resolved_environ.get("RD_AGENT_BENCHMARK_SUITE", "runtime")
    api_key = resolved_environ.get("LANGSMITH_API_KEY")
    endpoint = resolved_environ.get("LANGSMITH_ENDPOINT")

    return TracingConfig(
        enabled=True,
        upload_enabled=bool(api_key),
        project=project,
        suite=suite,
        api_key=api_key,
        endpoint=endpoint,
        metadata=build_tracing_metadata(project=project, suite=suite, environ=resolved_environ),
    )
