---
status: investigating
trigger: "UAT Test 1: returned structuredContent.run.current_round stays 0 even though exploration round increments persisted state to 1"
created: 2026-03-23T10:02:22Z
updated: 2026-03-23T10:02:22Z
---

## Current Focus

hypothesis: `rd_agent()` returns a stale run snapshot captured before `run_exploration_round()` mutates persisted run state.
test: Compare the multi-branch return payload construction in `v3/entry/rd_agent.py` with the persisted run update inside `v3/orchestration/multi_branch_service.py`.
expecting: If true, the response payload will serialize an out-of-date `run_snapshot` while the state store contains `current_round == 1`.
next_action: Hand off a targeted fix and regression assertions to gap-closure planning.

## Symptoms

expected: The returned `structuredContent.run.current_round` is `1` after the first exploration round, and the same payload visibly includes `selected_branch_id` and `merge_summary`.
actual: `structuredContent.run.current_round` remains `0`; tests only verified persisted state and omitted the required response-field assertions.
errors: None reported beyond incorrect returned state.
reproduction: `UAT Test 1` / inspect `rd_agent(..., hypothesis_specs=[...])` multi-branch path.
started: Discovered during Phase 26 UAT.

## Eliminated

## Evidence

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/entry/rd_agent.py:267-323`
  found: `run_snapshot` is loaded and persisted before exploration, then returned directly at line 323 without reloading after `run_exploration_round()`.
  implication: Returned payload can diverge from canonical persisted run state.

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:141-144`
  found: `run_exploration_round()` reloads the persisted run and increments `current_round` before returning.
  implication: The state store is correct; the response object is stale.

- timestamp: 2026-03-23T10:02:22Z
  checked: `tests/test_phase26_integration.py:248-293`
  found: The HypothesisSpec rd_agent test reads `state_store.load_run_snapshot("run-001")` and does not assert the returned payload's `current_round`, `selected_branch_id`, or `merge_summary`.
  implication: Regression coverage misses the exact outward-facing contract that broke.

## Resolution

root_cause: `rd_agent()` builds the multi-branch response from a pre-exploration `run_snapshot`, so `structuredContent.run` becomes stale even though the persisted run is incremented. The integration test masks this by reading state directly and omitting key return-value assertions.
fix: ""
verification: ""
files_changed: []
