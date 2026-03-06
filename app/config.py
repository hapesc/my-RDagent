"""Configuration layer for Agentic R&D MVP."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    env: str
    default_scenario: str
    artifact_root: str
    workspace_root: str
    trace_storage_path: str
    sqlite_path: str
    sandbox_timeout_sec: int
    log_level: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def load_config(environ: Optional[Mapping[str, str]] = None) -> AppConfig:
    """Load app config from environment variables with defaults."""

    env_map: Mapping[str, str] = environ or {}
    if environ is None:
        import os

        env_map = os.environ

    return AppConfig(
        env=env_map.get("AGENTRD_ENV", "dev"),
        default_scenario=env_map.get("AGENTRD_DEFAULT_SCENARIO", "data_science"),
        artifact_root=env_map.get("AGENTRD_ARTIFACT_ROOT", "/tmp/rd_agent_artifacts"),
        workspace_root=env_map.get("AGENTRD_WORKSPACE_ROOT", "/tmp/rd_agent_workspace"),
        trace_storage_path=env_map.get("AGENTRD_TRACE_STORAGE_PATH", "/tmp/rd_agent_trace/events.jsonl"),
        sqlite_path=env_map.get("AGENTRD_SQLITE_PATH", "/tmp/rd_agent.sqlite3"),
        sandbox_timeout_sec=_get_int(env_map, "AGENTRD_SANDBOX_TIMEOUT_SEC", 300),
        log_level=env_map.get("AGENTRD_LOG_LEVEL", "INFO"),
    )
