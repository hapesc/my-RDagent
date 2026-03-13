from __future__ import annotations

import importlib

runtime = importlib.import_module("v2.runtime")
REAL_PROVIDER_SAFE_PROFILE = runtime.REAL_PROVIDER_SAFE_PROFILE
V2RuntimeContext = runtime.V2RuntimeContext
build_v2_runtime = runtime.build_v2_runtime


def test_build_v2_runtime_returns_context() -> None:
    ctx = build_v2_runtime({"llm_provider": "mock"})
    assert isinstance(ctx, V2RuntimeContext)


def test_build_v2_runtime_stores_config() -> None:
    cfg = {"llm_provider": "mock", "max_loops": 2}
    ctx = build_v2_runtime(cfg)
    assert ctx.config["max_loops"] == 2


def test_real_provider_guardrails_applied_for_litellm() -> None:
    ctx = build_v2_runtime({"llm_provider": "litellm"})
    for key, safe_val in REAL_PROVIDER_SAFE_PROFILE.items():
        assert ctx.config[key] == safe_val


def test_mock_provider_does_not_apply_guardrails() -> None:
    ctx = build_v2_runtime({"llm_provider": "mock", "costeer_max_rounds": 5})
    assert ctx.config["costeer_max_rounds"] == 5


def test_checkpoint_coordinator_created_when_artifact_root_provided(tmp_path) -> None:
    ctx = build_v2_runtime({"llm_provider": "mock", "artifact_root": str(tmp_path)})
    assert ctx.checkpoint_coordinator is not None


def test_build_v2_runtime_injects_checkpoint_coordinator_into_run_service(tmp_path) -> None:
    ctx = build_v2_runtime({"llm_provider": "mock", "artifact_root": str(tmp_path)})

    assert ctx.checkpoint_coordinator is not None
    assert getattr(ctx.run_service, "checkpoint_coordinator", None) is ctx.checkpoint_coordinator


def test_build_v2_runtime_exposes_no_tracing_config_when_disabled() -> None:
    ctx = build_v2_runtime({"llm_provider": "mock"})

    assert hasattr(ctx, "tracing_config")
    assert ctx.tracing_config is None


def test_build_v2_runtime_exposes_provider_metadata_for_mock() -> None:
    ctx = build_v2_runtime({"llm_provider": "mock", "llm_model": "mock-model"})

    assert ctx.llm_provider_name == "mock"
    assert ctx.llm_model_name == "mock-model"
    assert ctx.judge_model_name is None


def test_build_v2_runtime_exposes_provider_metadata_for_litellm() -> None:
    ctx = build_v2_runtime({"llm_provider": "litellm", "llm_model": "gpt-4.1-mini"})

    assert ctx.llm_provider_name == "litellm"
    assert ctx.llm_model_name == "gpt-4.1-mini"
    assert ctx.judge_model_name is None
