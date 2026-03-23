---
status: investigating
trigger: "UAT Test 4: auto_prune=False should skip pruning even when a prune service is present"
created: 2026-03-23T10:02:22Z
updated: 2026-03-23T10:02:22Z
---

## Current Focus

hypothesis: The runtime short-circuit is correct, but the only current test covers `prune_service=None`, not "prune service present + auto_prune=False".
test: Inspect the prune gate in `multi_branch_service.py`, the current integration test wiring, and the rd_agent entrypoint.
expecting: If true, the core code path is fine but the proof of the invariant is missing and the entrypoint does not expose the flag.
next_action: Hand off a spy-backed regression test and entrypoint decision to gap-closure planning.

## Symptoms

expected: With `auto_prune=False`, exploration still dispatches and increments the round, returns empty `pruned_branch_ids`, and never calls the prune service.
actual: The short-circuit exists, but the test uses `prune_service=None`, so it does not prove that a real prune service is skipped; `rd_agent()` also never exposes `auto_prune`.
errors: None reported as runtime exceptions.
reproduction: `UAT Test 4` / inspect `auto_prune=False` integration path.
started: Discovered during Phase 26 UAT.

## Eliminated

## Evidence

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:135-139`
  found: Pruning is gated behind `self._prune_service is not None and request.auto_prune`.
  implication: The runtime short-circuit is correct.

- timestamp: 2026-03-23T10:02:22Z
  checked: `tests/test_phase26_integration.py:227-245`
  found: The `auto_prune=False` test calls `_build_service(tmp_path)` with no prune service injected.
  implication: The test cannot prove that an existing prune service is skipped.

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/entry/rd_agent.py:309-314`
  found: `rd_agent()` constructs `ExploreRoundRequest(...)` without an `auto_prune` argument, so the entrypoint always uses the default `True`.
  implication: The service-level flag is not currently exposed to rd_agent callers.

## Resolution

root_cause: The auto-prune gate is implemented correctly, but verification only covers the no-prune-service path, not the "service present but auto_prune disabled" path. In addition, `rd_agent()` does not expose `auto_prune`, so the flag cannot be controlled from the main entrypoint.
fix: ""
verification: ""
files_changed: []
