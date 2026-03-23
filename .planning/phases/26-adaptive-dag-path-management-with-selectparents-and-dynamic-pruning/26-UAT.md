---
status: complete
phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning
source:
  - 26-01-SUMMARY.md
  - 26-02-SUMMARY.md
  - 26-03-SUMMARY.md
  - 26-04-SUMMARY.md
started: 2026-03-23T09:06:05Z
updated: 2026-03-23T09:55:50Z
---

## Current Test

[testing complete]

## Tests

### 1. Start Multi-Branch Run from HypothesisSpec
expected: Calling `rd_agent(..., hypothesis_specs=[...])` with 2+ distinct approach categories completes the multi-branch path without schema or wiring errors, returns `dispatches`, `selected_branch_id`, and `merge_summary`, advances the run round from 0 to 1, and creates DAG nodes for the dispatched branches.
result: issue
reported: "CRITICAL: `rd_agent.py:323` returns the stale `run_snapshot`, so `structuredContent.run.current_round` is 0 instead of 1. The test also misses assertions for `selected_branch_id`, `merge_summary`, and the returned `current_round`, which hides the bug."
severity: blocker

### 2. Reject Duplicate First-Layer Categories
expected: If two first-layer `HypothesisSpec` entries share the same `approach_category`, exploration stops immediately with a duplicate-category error before extra dispatches, forks, or DAG nodes are created.
result: issue
reported: "Validation 时序本身是对的，但当前测试只断言了 `dispatches == []`，没有锁住 `fork == 0`、`DAG == 0`、`current_round == 0`，也没有断言错误消息内容。这样如果将来有人把 validation 挪到 fork 之后，测试未必会 break。"
severity: major

### 3. Exploration Round Records DAG and Diversity
expected: Running `MultiBranchService.run_exploration_round(...)` with `hypothesis_specs` returns `dag_node_ids` and `pruned_branch_ids`, and the created DAG nodes carry the same Shannon-entropy diversity score for that first-layer seed set.
result: issue
reported: "Returned `dag_node_ids` and entropy values match the current spec, but the review identifies a design flaw: round-level entropy is copied into every node as `node_metrics.diversity_score`, so the field is not truly node-scoped. It also points out ambiguous `0.0` diversity when `hypothesis_specs=None` with DAG enabled, hard-coded `parent_node_ids=[]` across rounds, and missing assertions for node metric defaults and DAG-to-branch correspondence."
severity: major

### 4. Optional Auto-Prune Skip
expected: Running exploration with `auto_prune=False` still dispatches branches and increments `current_round`, but `pruned_branch_ids` stays empty and no prune step runs.
result: issue
reported: "Core short-circuit logic is correct, but the only `auto_prune=False` test uses `prune_service=None`, so it never proves that an existing prune service is actually skipped. Review also notes that `rd_agent()` does not expose `auto_prune`, and board differences between prune-on and prune-off paths are untested."
severity: major

### 5. Legacy String Hypotheses Still Work
expected: Existing `branch_hypotheses=["primary", "alt-a", ...]` and `ExploreRoundRequest(hypotheses=[...])` flows still complete without needing `HypothesisSpec`, and the older multi-branch rd_agent path remains usable.
result: issue
reported: "Legacy string hypotheses path still functions, but `rd_agent()` now unconditionally injects DAG/prune side effects into legacy multi-branch calls, and there is a precedence conflict if callers provide both `branch_hypotheses` and `hypothesis_specs`. Review also notes that empty hypothesis lists can silently produce a no-op exploration round."
severity: major

## Summary

total: 5
passed: 0
issues: 5
pending: 0
skipped: 0

## Gaps

- truth: "Calling `rd_agent(..., hypothesis_specs=[...])` returns structured output with `dispatches`, `selected_branch_id`, `merge_summary`, and `run.current_round == 1` after the exploration round."
  status: failed
  reason: "User reported: CRITICAL bug — `rd_agent.py:323` returns stale `run_snapshot`, so `structuredContent.run.current_round` is 0 instead of 1. Review also notes missing assertions for `selected_branch_id`, `merge_summary`, and returned `current_round`."
  severity: blocker
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Duplicate first-layer `HypothesisSpec` categories fail before any extra dispatch, fork, DAG node creation, or round increment, and the duplicate-category error is explicitly asserted."
  status: failed
  reason: "User reported: validation order is correct, but the integration test only checks `dispatches == []` and misses `fork == 0`, `DAG == 0`, `current_round == 0`, and error-message assertions."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Exploration-round DAG recording preserves meaningful diversity semantics: returned `dag_node_ids` and `pruned_branch_ids` match created nodes, node metrics remain internally consistent, and diversity data is not conflated between round-level metadata and node-level state."
  status: failed
  reason: "User reported: current behavior matches the narrow spec, but `diversity_score` is modeled as a round-level entropy value copied onto every node, `hypothesis_specs=None` with DAG enabled silently writes `0.0`, parent links stay hard-coded empty across rounds, and integration tests miss several invariants."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "When `auto_prune=False`, exploration still dispatches and increments `current_round`, returns empty `pruned_branch_ids`, and skips prune execution even if a prune service is present."
  status: failed
  reason: "User reported: short-circuit logic is correct, but the existing test only covers the case where `prune_service=None`, so it does not prove that a real prune service is skipped. Review also notes that `rd_agent()` does not expose `auto_prune` and board semantics are untested across prune-on/off paths."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Legacy string-hypothesis exploration remains usable without `HypothesisSpec`, with one unambiguous input-precedence rule and without unintended Phase 26 side effects or silent no-op rounds."
  status: failed
  reason: "User reported: legacy string paths still run, but `rd_agent()` now unconditionally creates DAG/prune side effects for legacy calls, there is a precedence conflict when both `branch_hypotheses` and `hypothesis_specs` are provided, and empty hypothesis lists can complete as a silent no-op."
  severity: major
  test: 5
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
