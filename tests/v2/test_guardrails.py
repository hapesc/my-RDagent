from __future__ import annotations

import importlib

runtime = importlib.import_module("v2.runtime")
REAL_PROVIDER_SAFE_PROFILE = runtime.REAL_PROVIDER_SAFE_PROFILE
build_v2_runtime = runtime.build_v2_runtime


class TestGuardrails:
    def test_litellm_provider_applies_guardrails(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "litellm"})

        assert ctx.config["llm_provider"] == "litellm"
        assert ctx.config.get("costeer_max_rounds", 999) <= REAL_PROVIDER_SAFE_PROFILE["costeer_max_rounds"]

    def test_mock_provider_no_guardrails(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock"})

        assert ctx.config["llm_provider"] == "mock"
        assert (
            "costeer_max_rounds" not in ctx.config
            or ctx.config["costeer_max_rounds"] > REAL_PROVIDER_SAFE_PROFILE["costeer_max_rounds"]
        )

    def test_guardrails_exact_values(self) -> None:
        assert REAL_PROVIDER_SAFE_PROFILE == {
            "layer0_n_candidates": 1,
            "layer0_k_forward": 1,
            "costeer_max_rounds": 1,
            "sandbox_timeout_sec": 120,
            "max_retries": 1,
        }

        ctx = build_v2_runtime({"llm_provider": "litellm"})
        for key, expected_value in REAL_PROVIDER_SAFE_PROFILE.items():
            assert ctx.config[key] == expected_value

    def test_guardrails_cannot_be_overridden(self) -> None:
        ctx = build_v2_runtime(
            {
                "llm_provider": "litellm",
                "costeer_max_rounds": 999,
                "layer0_n_candidates": 999,
                "sandbox_timeout_sec": 999,
                "max_retries": 999,
            }
        )

        assert ctx.config["costeer_max_rounds"] <= 1
        assert ctx.config["costeer_max_rounds"] == REAL_PROVIDER_SAFE_PROFILE["costeer_max_rounds"]
        assert ctx.config["layer0_n_candidates"] == REAL_PROVIDER_SAFE_PROFILE["layer0_n_candidates"]
        assert ctx.config["sandbox_timeout_sec"] == REAL_PROVIDER_SAFE_PROFILE["sandbox_timeout_sec"]
        assert ctx.config["max_retries"] == REAL_PROVIDER_SAFE_PROFILE["max_retries"]
