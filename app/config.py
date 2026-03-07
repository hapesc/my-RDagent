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
    allow_local_execution: bool
    log_level: str
    llm_provider: str
    llm_api_key: Optional[str]
    llm_model: str
    llm_base_url: Optional[str]
    costeer_max_rounds: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_bool(environ: Mapping[str, str], key: str, default: bool) -> bool:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be a boolean string")


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
        allow_local_execution=_get_bool(env_map, "AGENTRD_ALLOW_LOCAL_EXECUTION", False),
        log_level=env_map.get("AGENTRD_LOG_LEVEL", "INFO"),
        llm_provider=env_map.get("RD_AGENT_LLM_PROVIDER", "mock"),
        llm_api_key=env_map.get("RD_AGENT_LLM_API_KEY") or None,
        llm_model=env_map.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini"),
        llm_base_url=env_map.get("RD_AGENT_LLM_BASE_URL") or None,
        costeer_max_rounds=_get_int(env_map, "RD_AGENT_COSTEER_MAX_ROUNDS", 1),
    )
