"""Configuration layer for Agentic R&D MVP."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


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
    llm_api_key: str | None
    llm_model: str
    llm_base_url: str | None
    costeer_max_rounds: int
    mcts_exploration_weight: float = 1.41
    mcts_c_puct: float = 1.41
    mcts_reward_mode: str = "score_based"
    layer0_n_candidates: int = 5
    layer0_k_forward: int = 2
    prune_threshold: float = 0.5
    debug_mode: bool = False
    debug_sample_fraction: float = 0.1
    debug_max_epochs: int = 5
    enable_hypothesis_storage: bool = False
    use_llm_planning: bool = False
    uses_real_llm_provider: bool = False
    real_provider_warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


REAL_PROVIDER_SAFE_PROFILE: dict[str, int] = {
    "layer0_n_candidates": 1,
    "layer0_k_forward": 1,
    "costeer_max_rounds": 1,
    "sandbox_timeout_sec": 120,
    "max_retries": 1,
}

_REAL_PROVIDER_WARNING_LIMITS: dict[str, int] = {
    "layer0_n_candidates": 2,
    "layer0_k_forward": 2,
    "costeer_max_rounds": 2,
    "sandbox_timeout_sec": 300,
    "max_retries": 1,
}


def uses_real_llm_provider(provider: str) -> bool:
    return provider.strip().lower() not in {"", "mock"}


def _validate_positive_config_fields(values: Mapping[str, int]) -> None:
    for field_name, value in values.items():
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0")


def _apply_real_provider_defaults(merged: dict[str, Any], sources: Mapping[str, str]) -> None:
    if not uses_real_llm_provider(str(merged["llm_provider"])):
        return
    for field_name, safe_value in REAL_PROVIDER_SAFE_PROFILE.items():
        if field_name == "max_retries":
            continue
        if sources.get(field_name, "default") == "default":
            merged[field_name] = safe_value


def _validate_real_provider_guardrails(
    config: AppConfig,
    *,
    step_max_retries: Sequence[tuple[str, int | None]] | None = None,
    running_timeout_sec: int | None = None,
) -> tuple[str, ...]:
    if not config.uses_real_llm_provider:
        return ()

    warnings = []
    for field_name in (
        "layer0_n_candidates",
        "layer0_k_forward",
        "costeer_max_rounds",
        "sandbox_timeout_sec",
    ):
        value = int(getattr(config, field_name))
        safe_limit = REAL_PROVIDER_SAFE_PROFILE[field_name]
        warning_limit = _REAL_PROVIDER_WARNING_LIMITS[field_name]
        if value > warning_limit:
            raise ValueError(
                f"real provider guardrail violation: {field_name}={value} exceeds hard limit {warning_limit}"
            )
        if value > safe_limit:
            warnings.append(f"real provider warning: {field_name}={value} exceeds conservative profile {safe_limit}")

    if config.layer0_k_forward > config.layer0_n_candidates:
        raise ValueError("real provider guardrail violation: layer0_k_forward must be <= layer0_n_candidates")

    for step_name, retries in step_max_retries or ():
        if retries is None:
            continue
        if retries > _REAL_PROVIDER_WARNING_LIMITS["max_retries"]:
            raise ValueError(
                f"real provider guardrail violation: {step_name}.max_retries={retries} exceeds hard limit 1"
            )

    if running_timeout_sec is not None:
        if running_timeout_sec > _REAL_PROVIDER_WARNING_LIMITS["sandbox_timeout_sec"]:
            raise ValueError(
                f"real provider guardrail violation: running.timeout_sec={running_timeout_sec} exceeds hard limit 300"
            )
        if running_timeout_sec > REAL_PROVIDER_SAFE_PROFILE["sandbox_timeout_sec"]:
            warnings.append(
                f"real provider warning: running.timeout_sec={running_timeout_sec} exceeds conservative profile 120"
            )

    return tuple(warnings)


def validate_runtime_guardrails(
    config: AppConfig,
    *,
    step_max_retries: Sequence[tuple[str, int | None]] | None = None,
    running_timeout_sec: int | None = None,
) -> tuple[str, ...]:
    return _validate_real_provider_guardrails(
        config,
        step_max_retries=step_max_retries,
        running_timeout_sec=running_timeout_sec,
    )


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_float(environ: Mapping[str, str], key: str, default: float) -> float:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return float(raw)


def _get_string(environ: Mapping[str, str], key: str, default: str) -> str:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return raw


def _get_optional_string(environ: Mapping[str, str], key: str, default: str | None) -> str | None:
    raw = environ.get(key)
    if raw is None or raw == "":
        return default
    return raw


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


def _parse_bool_value(raw: Any, key: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    return _project_root() / "config.yaml"


def _load_yaml_values(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"config file must be a YAML object: {config_path}")
    return dict(raw)


def _as_string(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw)


def _as_optional_string(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw)
    return text if text != "" else None


_DEFAULTS: dict[str, Any] = {
    "env": "dev",
    "default_scenario": "data_science",
    "artifact_root": "/tmp/rd_agent_artifacts",
    "workspace_root": "/tmp/rd_agent_workspace",
    "trace_storage_path": "/tmp/rd_agent_trace/events.jsonl",
    "sqlite_path": "/tmp/rd_agent.sqlite3",
    "sandbox_timeout_sec": 300,
    "allow_local_execution": False,
    "log_level": "INFO",
    "llm_provider": "mock",
    "llm_api_key": None,
    "llm_model": "gpt-4o-mini",
    "llm_base_url": None,
    "costeer_max_rounds": 1,
    "mcts_exploration_weight": 1.41,
    "mcts_c_puct": 1.41,
    "mcts_reward_mode": "score_based",
    "layer0_n_candidates": 5,
    "layer0_k_forward": 2,
    "prune_threshold": 0.5,
    "debug_mode": False,
    "debug_sample_fraction": 0.1,
    "debug_max_epochs": 5,
    "enable_hypothesis_storage": False,
    "use_llm_planning": False,
}

_YAML_CASTERS: dict[str, Callable[[Any], Any]] = {
    "env": _as_string,
    "default_scenario": _as_string,
    "artifact_root": _as_string,
    "workspace_root": _as_string,
    "trace_storage_path": _as_string,
    "sqlite_path": _as_string,
    "sandbox_timeout_sec": int,
    "allow_local_execution": lambda raw: _parse_bool_value(raw, "allow_local_execution"),
    "log_level": _as_string,
    "llm_provider": _as_string,
    "llm_api_key": _as_optional_string,
    "llm_model": _as_string,
    "llm_base_url": _as_optional_string,
    "costeer_max_rounds": int,
    "mcts_exploration_weight": float,
    "mcts_c_puct": float,
    "mcts_reward_mode": _as_string,
    "layer0_n_candidates": int,
    "layer0_k_forward": int,
    "prune_threshold": float,
    "debug_mode": lambda raw: _parse_bool_value(raw, "debug_mode"),
    "debug_sample_fraction": float,
    "debug_max_epochs": int,
    "enable_hypothesis_storage": lambda raw: _parse_bool_value(raw, "enable_hypothesis_storage"),
    "use_llm_planning": lambda raw: _parse_bool_value(raw, "use_llm_planning"),
}

_ENV_BINDINGS: dict[str, tuple[str, Callable[[Mapping[str, str], str, Any], Any]]] = {
    "env": ("AGENTRD_ENV", _get_string),
    "default_scenario": ("AGENTRD_DEFAULT_SCENARIO", _get_string),
    "artifact_root": ("AGENTRD_ARTIFACT_ROOT", _get_string),
    "workspace_root": ("AGENTRD_WORKSPACE_ROOT", _get_string),
    "trace_storage_path": ("AGENTRD_TRACE_STORAGE_PATH", _get_string),
    "sqlite_path": ("AGENTRD_SQLITE_PATH", _get_string),
    "sandbox_timeout_sec": ("AGENTRD_SANDBOX_TIMEOUT_SEC", _get_int),
    "allow_local_execution": ("AGENTRD_ALLOW_LOCAL_EXECUTION", _get_bool),
    "log_level": ("AGENTRD_LOG_LEVEL", _get_string),
    "llm_provider": ("RD_AGENT_LLM_PROVIDER", _get_string),
    "llm_api_key": ("RD_AGENT_LLM_API_KEY", _get_optional_string),
    "llm_model": ("RD_AGENT_LLM_MODEL", _get_string),
    "llm_base_url": ("RD_AGENT_LLM_BASE_URL", _get_optional_string),
    "costeer_max_rounds": ("RD_AGENT_COSTEER_MAX_ROUNDS", _get_int),
    "mcts_exploration_weight": ("RD_AGENT_MCTS_WEIGHT", _get_float),
    "mcts_c_puct": ("RD_AGENT_MCTS_C_PUCT", _get_float),
    "mcts_reward_mode": ("RD_AGENT_MCTS_REWARD_MODE", _get_string),
    "layer0_n_candidates": ("RD_AGENT_LAYER0_N_CANDIDATES", _get_int),
    "layer0_k_forward": ("RD_AGENT_LAYER0_K_FORWARD", _get_int),
    "prune_threshold": ("RD_AGENT_PRUNE_THRESHOLD", _get_float),
    "debug_mode": ("RD_AGENT_DEBUG_MODE", _get_bool),
    "debug_sample_fraction": ("RD_AGENT_DEBUG_SAMPLE_FRACTION", _get_float),
    "debug_max_epochs": ("RD_AGENT_DEBUG_MAX_EPOCHS", _get_int),
    "enable_hypothesis_storage": ("RD_AGENT_HYPOTHESIS_STORAGE", _get_bool),
    "use_llm_planning": ("RD_AGENT_LLM_PLANNING", _get_bool),
}


def _merge_yaml(merged: dict[str, Any], yaml_values: Mapping[str, Any], sources: dict[str, str]) -> None:
    unknown = [key for key in yaml_values if key not in _YAML_CASTERS]
    if unknown:
        raise ValueError(f"unknown config keys in yaml: {', '.join(sorted(unknown))}")
    for key, raw in yaml_values.items():
        caster = _YAML_CASTERS[key]
        merged[key] = caster(raw)
        sources[key] = "yaml"


def _apply_env_overrides(merged: dict[str, Any], env_map: Mapping[str, str], sources: dict[str, str]) -> None:
    for field_name, (env_name, reader) in _ENV_BINDINGS.items():
        if env_name in env_map:
            merged[field_name] = reader(env_map, env_name, merged[field_name])
            if env_map.get(env_name) not in (None, ""):
                sources[field_name] = "env"


def load_config(
    environ: Mapping[str, str] | None = None,
    config_path: str | None = None,
) -> AppConfig:
    env_map: Mapping[str, str] = environ or {}
    if environ is None:
        import os

        env_map = os.environ

    merged: dict[str, Any] = dict(_DEFAULTS)
    sources: dict[str, str] = {key: "default" for key in _DEFAULTS}

    resolved_path = Path(config_path) if config_path is not None else _default_config_path()
    if config_path is not None and not resolved_path.exists():
        raise FileNotFoundError(f"config file not found: {resolved_path}")

    _merge_yaml(merged, _load_yaml_values(resolved_path), sources)
    _apply_env_overrides(merged, env_map, sources)
    _apply_real_provider_defaults(merged, sources)

    _validate_positive_config_fields(
        {
            "sandbox_timeout_sec": int(merged["sandbox_timeout_sec"]),
            "costeer_max_rounds": int(merged["costeer_max_rounds"]),
            "layer0_n_candidates": int(merged["layer0_n_candidates"]),
            "layer0_k_forward": int(merged["layer0_k_forward"]),
        }
    )

    uses_real_provider = uses_real_llm_provider(str(merged["llm_provider"]))
    base_config = AppConfig(
        env=merged["env"],
        default_scenario=merged["default_scenario"],
        artifact_root=merged["artifact_root"],
        workspace_root=merged["workspace_root"],
        trace_storage_path=merged["trace_storage_path"],
        sqlite_path=merged["sqlite_path"],
        sandbox_timeout_sec=merged["sandbox_timeout_sec"],
        allow_local_execution=merged["allow_local_execution"],
        log_level=merged["log_level"],
        llm_provider=merged["llm_provider"],
        llm_api_key=merged["llm_api_key"],
        llm_model=merged["llm_model"],
        llm_base_url=merged["llm_base_url"],
        costeer_max_rounds=merged["costeer_max_rounds"],
        mcts_exploration_weight=merged["mcts_exploration_weight"],
        mcts_c_puct=merged["mcts_c_puct"],
        mcts_reward_mode=merged["mcts_reward_mode"],
        layer0_n_candidates=merged["layer0_n_candidates"],
        layer0_k_forward=merged["layer0_k_forward"],
        prune_threshold=merged["prune_threshold"],
        debug_mode=merged["debug_mode"],
        debug_sample_fraction=merged["debug_sample_fraction"],
        debug_max_epochs=merged["debug_max_epochs"],
        enable_hypothesis_storage=merged["enable_hypothesis_storage"],
        use_llm_planning=merged["use_llm_planning"],
        uses_real_llm_provider=uses_real_provider,
    )
    warnings = _validate_real_provider_guardrails(base_config)
    return AppConfig(**{**base_config.to_dict(), "real_provider_warnings": warnings})
