#!/usr/bin/env python
"""E2E test: run synthetic_research scenario with real Gemini LLM.

Usage:
    source ~/.zshrc  # loads GEMINI_API_KEY
    RD_AGENT_LLM_PROVIDER=litellm RD_AGENT_LLM_MODEL=gemini/gemini-2.5-flash \
        python scripts/e2e_gemini_test.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Iterable

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s  %(message)s")
logger = logging.getLogger("e2e_gemini")


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


def evaluate_smoke_success(events: Iterable[object], run_status: str | None = None) -> tuple[bool, str]:
    """Evaluate smoke success based on usefulness and feedback gates.

    In single-loop smoke execution, we validate that:
    1. execution.finished event was recorded with usefulness_status=ELIGIBLE
    2. feedback.generated event was recorded with acceptable=True

    Run status is not checked because single-loop runs may still be in RUNNING state
    after completing one iteration (max_loops only affects loop condition, not run state transition).
    The acceptance criteria is purely based on validator gates, not completion status.
    """
    execution_event = _select_event(events, "execution.finished", "running")
    if execution_event is None:
        return False, "missing execution.finished event"

    execution_payload = getattr(execution_event, "payload", {}) or {}
    usefulness_status = execution_payload.get("usefulness_status")
    if usefulness_status != "ELIGIBLE":
        reason = execution_payload.get("usefulness_gate_reason", "unknown")
        return False, f"usefulness validator rejected output: {reason}"

    feedback_event = _select_event(events, "feedback.generated", "feedback")
    if feedback_event is None:
        return False, "missing feedback.generated event"

    feedback_payload = getattr(feedback_event, "payload", {}) or {}
    if not feedback_payload.get("acceptable"):
        reason = feedback_payload.get("reason", "feedback unacceptable")
        return False, f"feedback rejected smoke result: {reason}"

    return True, "usefulness validators passed"


def main() -> int:
    # ── 0. Pre-flight checks ────────────────────────────────────────
    provider = os.environ.get("RD_AGENT_LLM_PROVIDER", "mock")
    model = os.environ.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    print("=" * 72)
    print("  E2E Gemini Test — synthetic_research scenario")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  API Key  : {'set (' + gemini_key[:10] + '...)' if gemini_key else 'NOT SET'}")
    print("=" * 72)

    if provider != "litellm":
        print("\n⚠️  RD_AGENT_LLM_PROVIDER is not 'litellm'. Set it to run with real LLM.")
        print("    Falling back to mock provider for demo.\n")

    # ── 1. Build runtime ─────────────────────────────────────────────
    from app.config import REAL_PROVIDER_SAFE_PROFILE
    from app.runtime import (
        build_real_provider_smoke_step_overrides,
        build_run_service,
        build_runtime,
        resolve_scenario_runtime_profile,
    )

    t0 = time.time()
    runtime = build_runtime()
    print(f"\n✅ Runtime built ({time.time() - t0:.1f}s)")
    print(f"   llm_provider={runtime.config.llm_provider}, llm_model={runtime.config.llm_model}")
    print(f"   costeer_max_rounds={runtime.config.costeer_max_rounds}")

    # ── 2. Build run service for synthetic_research ──────────────────
    scenario = "synthetic_research"
    run_service = build_run_service(runtime, scenario)
    print(f"✅ RunService built for scenario={scenario}")
    manifest = runtime.plugin_registry.get_manifest(scenario)
    if manifest is None:
        print("❌ Scenario manifest missing for smoke run")
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
    print("   smoke preset: layer0=1/1, retries<=1, timeout=120s")
    print(
        "   effective step config: "
        f"proposal.max_retries={smoke_profile.effective_step_config.proposal.max_retries}, "
        f"coding.max_retries={smoke_profile.effective_step_config.coding.max_retries}, "
        f"feedback.max_retries={smoke_profile.effective_step_config.feedback.max_retries}, "
        f"running.timeout_sec={smoke_profile.effective_step_config.running.timeout_sec}"
    )
    if smoke_profile.guardrail_warnings:
        print("   guardrail warnings:")
        for warning in smoke_profile.guardrail_warnings:
            print(f"     - {warning}")

    # ── 3. Create run session ────────────────────────────────────────
    from data_models import StopConditions

    task_summary = "Investigate the effect of learning rate schedules on transformer convergence speed"
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
                "llm_model": runtime.config.llm_model,
                "uses_real_llm_provider": runtime.config.uses_real_llm_provider,
                "real_provider_safe_profile": dict(REAL_PROVIDER_SAFE_PROFILE),
                "guardrail_warnings": list(smoke_profile.guardrail_warnings),
            },
        },
    )
    print(f"✅ RunSession created: run_id={session.run_id}")
    print(f"   task: {task_summary}")

    # ── 4. Execute 1 loop iteration ──────────────────────────────────
    print(f"\n{'─' * 72}")
    print("🔄 Starting loop execution (1 iteration)...")
    print(f"{'─' * 72}\n")

    t1 = time.time()
    try:
        run_service.start_run(
            run_id=session.run_id,
            task_summary=task_summary,
            loops_per_call=1,
        )
        elapsed = time.time() - t1
        print(f"\n{'─' * 72}")
        print(f"✅ Loop completed in {elapsed:.1f}s")
        print(f"{'─' * 72}")
    except Exception as exc:
        elapsed = time.time() - t1
        print(f"\n{'─' * 72}")
        print(f"❌ Loop FAILED after {elapsed:.1f}s: {exc}")
        print(f"{'─' * 72}")
        import traceback

        traceback.print_exc()
        return 1

    # ── 5. Inspect results ───────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("  RESULTS INSPECTION")
    print(f"{'=' * 72}")

    # Read events from sqlite
    events = runtime.sqlite_store.query_events(run_id=session.run_id)
    print(f"\n📊 Total events recorded: {len(events)}")
    for ev in events:
        payload_str = json.dumps(ev.payload, indent=2) if ev.payload else "{}"
        print(f"\n  [{ev.step_name}] {ev.event_type.value}")
        if len(payload_str) > 500:
            payload_str = payload_str[:500] + "\n  ... (truncated)"
        for line in payload_str.split("\n"):
            print(f"    {line}")

    # Check workspace artifacts
    import glob as glob_mod

    ws_pattern = f"{runtime.config.workspace_root}/{session.run_id}/**/*"
    artifacts = glob_mod.glob(ws_pattern, recursive=True)
    artifacts = [a for a in artifacts if os.path.isfile(a)]
    print(f"\n📁 Workspace artifacts ({len(artifacts)} files):")
    for a in sorted(artifacts):
        rel = a.replace(f"{runtime.config.workspace_root}/{session.run_id}/", "")
        size = os.path.getsize(a)
        print(f"    {rel} ({size}B)")
        # Print content of small files
        if size < 2000 and (a.endswith(".txt") or a.endswith(".json") or a.endswith(".md")):
            with open(a) as f:
                content = f.read()
            print("      ┌── content ──")
            for line in content.split("\n")[:20]:
                print(f"      │ {line}")
            if content.count("\n") > 20:
                print("      │ ... (truncated)")
            print("      └────────────")

    # Check branch trace
    nodes = runtime.branch_store.query_nodes(run_id=session.run_id)
    print(f"\n🌳 Branch trace nodes: {len(nodes)}")
    for node in nodes:
        print(f"    {node.node_id} (branch={node.branch_id}, step={node.step_state.value})")
        print(f"      hypothesis: {json.dumps(node.hypothesis)[:200]}")

    runtime.sqlite_store.get_run(session.run_id)
    smoke_success, smoke_reason = evaluate_smoke_success(events)

    print(f"\n{'=' * 72}")
    print(f"  E2E TEST COMPLETE — {'SUCCESS' if smoke_success else 'FAILED'}")
    print(f"  Reason: {smoke_reason}")
    print(f"{'=' * 72}\n")
    return 0 if smoke_success else 1


if __name__ == "__main__":
    sys.exit(main())
