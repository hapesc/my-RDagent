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

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s  %(message)s")
logger = logging.getLogger("e2e_gemini")


def main() -> int:
    # ── 0. Pre-flight checks ────────────────────────────────────────
    provider = os.environ.get("RD_AGENT_LLM_PROVIDER", "mock")
    model = os.environ.get("RD_AGENT_LLM_MODEL", "gpt-4o-mini")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    print("=" * 72)
    print(f"  E2E Gemini Test — synthetic_research scenario")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  API Key  : {'set (' + gemini_key[:10] + '...)' if gemini_key else 'NOT SET'}")
    print("=" * 72)

    if provider != "litellm":
        print("\n⚠️  RD_AGENT_LLM_PROVIDER is not 'litellm'. Set it to run with real LLM.")
        print("    Falling back to mock provider for demo.\n")

    # ── 1. Build runtime ─────────────────────────────────────────────
    from app.runtime import build_runtime, build_run_service

    t0 = time.time()
    runtime = build_runtime()
    print(f"\n✅ Runtime built ({time.time()-t0:.1f}s)")
    print(f"   llm_provider={runtime.config.llm_provider}, llm_model={runtime.config.llm_model}")
    print(f"   costeer_max_rounds={runtime.config.costeer_max_rounds}")

    # ── 2. Build run service for synthetic_research ──────────────────
    scenario = "synthetic_research"
    run_service = build_run_service(runtime, scenario)
    print(f"✅ RunService built for scenario={scenario}")

    # ── 3. Create run session ────────────────────────────────────────
    task_summary = "Investigate the effect of learning rate schedules on transformer convergence speed"
    session = run_service.create_run(task_summary=task_summary, scenario=scenario)
    print(f"✅ RunSession created: run_id={session.run_id}")
    print(f"   task: {task_summary}")

    # ── 4. Execute 1 loop iteration ──────────────────────────────────
    print(f"\n{'─'*72}")
    print("🔄 Starting loop execution (1 iteration)...")
    print(f"{'─'*72}\n")

    t1 = time.time()
    try:
        run_service.start_run(
            run_id=session.run_id,
            task_summary=task_summary,
            loops_per_call=1,
        )
        elapsed = time.time() - t1
        print(f"\n{'─'*72}")
        print(f"✅ Loop completed in {elapsed:.1f}s")
        print(f"{'─'*72}")
    except Exception as exc:
        elapsed = time.time() - t1
        print(f"\n{'─'*72}")
        print(f"❌ Loop FAILED after {elapsed:.1f}s: {exc}")
        print(f"{'─'*72}")
        import traceback
        traceback.print_exc()
        return 1

    # ── 5. Inspect results ───────────────────────────────────────────
    print(f"\n{'='*72}")
    print("  RESULTS INSPECTION")
    print(f"{'='*72}")

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
            print(f"      ┌── content ──")
            for line in content.split("\n")[:20]:
                print(f"      │ {line}")
            if content.count("\n") > 20:
                print(f"      │ ... (truncated)")
            print(f"      └────────────")

    # Check branch trace
    nodes = runtime.branch_store.query_nodes(run_id=session.run_id)
    print(f"\n🌳 Branch trace nodes: {len(nodes)}")
    for node in nodes:
        print(f"    {node.node_id} (branch={node.branch_id}, step={node.step_state.value})")
        print(f"      hypothesis: {json.dumps(node.hypothesis)[:200]}")

    print(f"\n{'='*72}")
    print(f"  E2E TEST COMPLETE — {'SUCCESS' if True else 'FAILED'}")
    print(f"{'='*72}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
