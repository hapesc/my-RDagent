#!/usr/bin/env python
"""E2E test: Micro-Arena for Data Science Accuracy.

This script tests the deterministic accuracy of the data_science scenario.
It generates a dataset with a known mathematical relationship (y = 2.0x + 1.0)
and explicit outliers. It then asks the LLM to fit a linear regression on the
normal data and output the slope to metrics.json.

Usage:
    source ~/.zshrc  # loads GEMINI_API_KEY
    RD_AGENT_LLM_PROVIDER=litellm RD_AGENT_LLM_MODEL=gemini/gemini-2.5-flash \
        python scripts/e2e_data_science_arena.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import tempfile
import time
from collections.abc import Iterable

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s  %(message)s")
logger = logging.getLogger("e2e_ds_arena")


def _select_event(events: Iterable[object], event_type: str, step_name: str | None = None):
    matched = []
    for event in events:
        current_type = getattr(getattr(event, "event_type", None), "value", None)
        if current_type != event_type:
            continue
        if step_name is not None and getattr(event, "step_name", None) != step_name:
            continue
        matched.append(event)
    return matched[-1] if matched else None


def main() -> int:
    provider = os.environ.get("RD_AGENT_LLM_PROVIDER", "mock")
    model = os.environ.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini")

    print("=" * 72)
    print("  E2E Data Science Arena — Micro-Accuracy Test")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print("=" * 72)

    if provider != "litellm":
        print("\n⚠️  RD_AGENT_LLM_PROVIDER is not 'litellm'. Set it to run with real LLM.")
        print("    This arena expects a real LLM to perform actual math.\n")

    # 1. Generate deterministic dataset
    temp_dir = tempfile.mkdtemp(prefix="rd_arena_")
    csv_path = os.path.join(temp_dir, "data.csv")

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y"])
        # Normal data: y = 2.0 * x + 1.0
        for i in range(10):
            writer.writerow([i, 2.0 * i + 1.0])
        # Outliers
        writer.writerow([100, 5000])
        writer.writerow([101, -5000])

    print(f"✅ Generated dataset with outliers at {csv_path}")

    # 2. Build runtime
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

    # 3. Create run session
    from data_models import StopConditions

    task_summary = (
        f"Read the dataset at {csv_path}. Find the two obvious outliers. "
        f"Fit a linear regression on the normal data. Write the fitted slope (as a float key 'slope') "
        f"and outlier indices to metrics.json. Explain your findings."
    )

    session = run_service.create_run(
        task_summary=task_summary,
        scenario=scenario,
        stop_conditions=StopConditions(max_loops=1),
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

    # 4. Execute
    t1 = time.time()
    try:
        run_service.start_run(
            run_id=session.run_id,
            task_summary=task_summary,
            loops_per_call=1,
        )
        print(f"✅ Loop completed in {time.time() - t1:.1f}s")
    except Exception as exc:
        print(f"❌ Loop FAILED: {exc}")
        return 1

    # 5. Verify Artifacts & Math Accuracy
    import glob

    ws_pattern = f"{runtime.config.workspace_root}/{session.run_id}/**/*metrics.json"
    files = glob.glob(ws_pattern, recursive=True)

    if not files:
        print("❌ metrics.json not found. The LLM failed to produce the required artifact.")
        return 1

    metrics_file = files[-1]
    try:
        with open(metrics_file) as f:
            metrics = json.load(f)

        print(f"\n📊 Extracted Metrics: {json.dumps(metrics, indent=2)}")

        slope = metrics.get("slope")
        if slope is None:
            # Maybe they named it differently
            print("❌ 'slope' key missing from metrics.json")
            return 1

        slope_val = float(slope)
        if 1.9 <= slope_val <= 2.1:
            print(
                "\n🎉 SUCCESS: The LLM correctly filtered outliers and computed "
                f"slope = {slope_val:.2f} (Expected ~2.0)"
            )
            return 0
        else:
            print(
                f"\n❌ FAILURE: Slope is {slope_val:.2f}, which is far from 2.0. The math or outlier filtering failed."
            )
            return 1

    except Exception as e:
        print(f"❌ Failed to parse metrics.json: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
