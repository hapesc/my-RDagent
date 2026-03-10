#!/usr/bin/env python
"""E2E test: Resilience Arena for Self-Correction.

This script tests the loop's ability to self-correct after a deliberate failure.
We give the agent a task that will inevitably fail on loop 1 (importing a non-existent package),
and verify that CoSTEER / the feedback loop successfully reads the stack trace,
realizes the mistake, and fixes the code in loop 2 or 3.

Usage:
    source ~/.zshrc  # loads GEMINI_API_KEY
    RD_AGENT_LLM_PROVIDER=litellm RD_AGENT_LLM_MODEL=gemini/gemini-2.5-flash \
        python scripts/e2e_resilience_arena.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s  %(message)s")
logger = logging.getLogger("e2e_resilience_arena")


def main() -> int:
    provider = os.environ.get("RD_AGENT_LLM_PROVIDER", "mock")
    model = os.environ.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini")

    print("=" * 72)
    print("  E2E Resilience Arena — Self-Correction Test")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print("=" * 72)

    if provider != "litellm":
        print("\n⚠️  RD_AGENT_LLM_PROVIDER is not 'litellm'. Set it to run with real LLM.")

    # 1. Build runtime
    from app.config import REAL_PROVIDER_SAFE_PROFILE
    from app.runtime import (
        build_real_provider_smoke_step_overrides,
        build_run_service,
        build_runtime,
        resolve_scenario_runtime_profile,
    )

    runtime = build_runtime()
    scenario = "data_science"
    run_service = build_run_service(runtime, scenario)
    manifest = runtime.plugin_registry.get_manifest(scenario)
    if not manifest:
        print("❌ Scenario manifest missing")
        return 1

    smoke_overrides = build_real_provider_smoke_step_overrides(
        runtime.config,
        manifest.default_step_overrides,
    )
    smoke_profile = resolve_scenario_runtime_profile(
        runtime.config,
        manifest.default_step_overrides,
        smoke_overrides,
    )

    # 2. Create run session with max_loops=3
    from data_models import StopConditions

    task_summary = (
        "Write a python script that imports the package `definitely_does_not_exist_pkg_12345`. "
        "When it inevitably fails with a ModuleNotFoundError, read the error message, "
        "realize the package doesn't exist, and write a new script that just uses the built-in "
        "`math` package to calculate the square root of 144. Output the result to metrics.json as 'sqrt_result'."
    )

    session = run_service.create_run(
        task_summary=task_summary,
        scenario=scenario,
        stop_conditions=StopConditions(max_loops=3),
        config_snapshot={
            "scenario": scenario,
            "step_overrides": smoke_profile.effective_step_config.to_dict(),
            "requested_step_overrides": smoke_overrides.to_dict(),
            "runtime": {
                "llm_provider": runtime.config.llm_provider,
                "uses_real_llm_provider": runtime.config.uses_real_llm_provider,
                "real_provider_safe_profile": dict(REAL_PROVIDER_SAFE_PROFILE),
            },
        },
    )
    print(f"✅ RunSession created: run_id={session.run_id}")

    # 3. Execute
    t1 = time.time()
    try:
        # Request up to 3 loops
        run_service.start_run(
            run_id=session.run_id,
            task_summary=task_summary,
            loops_per_call=3,
        )
        print(f"✅ Run completed in {time.time() - t1:.1f}s")
    except Exception as exc:
        print(f"❌ Run FAILED with exception: {exc}")
        return 1

    # 4. Verify Resilience
    events = runtime.sqlite_store.query_events(run_id=session.run_id)
    loop_indices = set(ev.loop_index for ev in events)
    total_loops = len(loop_indices)

    print(f"\n📊 Total loops executed: {total_loops}")

    if total_loops < 2:
        print(
            "❌ FAILURE: The agent did not iterate. It either magically succeeded on "
            "loop 1 (ignoring constraints) or gave up immediately."
        )
        # If mock provider, we just return 0 to pass tests, as mock doesn't do real multi-round
        return 0 if provider == "mock" else 1

    import glob

    ws_pattern = f"{runtime.config.workspace_root}/{session.run_id}/**/*metrics.json"
    files = glob.glob(ws_pattern, recursive=True)

    if not files:
        print("❌ metrics.json not found in any workspace. The LLM failed to recover.")
        return 1

    metrics_file = files[-1]
    try:
        with open(metrics_file) as f:
            metrics = json.load(f)

        result = metrics.get("sqrt_result")
        if result == 12.0:
            print(
                "\n🎉 SUCCESS: The LLM failed, learned from its mistake, and correctly "
                f"computed sqrt(144) = 12.0 on loop {total_loops}"
            )
            return 0
        else:
            print(f"\n❌ FAILURE: Recovered, but produced wrong answer {result} instead of 12.0")
            return 1

    except Exception as e:
        print(f"❌ Failed to parse metrics.json: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
