---
status: diagnosed
phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning
source:
  - 26-01-SUMMARY.md
  - 26-02-SUMMARY.md
  - 26-03-SUMMARY.md
  - 26-04-SUMMARY.md
started: 2026-03-23T09:06:05Z
updated: 2026-03-23T10:02:22Z
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
  root_cause: "`rd_agent()` returns the pre-exploration `run_snapshot` object in `structuredContent.run`, even though `run_exploration_round()` increments the persisted run. The integration test masks this by reading state directly and omitting return-value assertions for `current_round`, `selected_branch_id`, and `merge_summary`."
  artifacts:
    - path: "v3/entry/rd_agent.py"
      issue: "Builds the multi-branch response from a stale run snapshot captured before exploration mutates persisted state."
    - path: "tests/test_phase26_integration.py"
      issue: "HypothesisSpec rd_agent test reads persisted state instead of asserting the returned payload contract."
  missing:
    - "Reload the run snapshot from state_store before building the multi-branch response payload."
    - "Assert `structuredContent.run.current_round == 1` in the rd_agent HypothesisSpec integration test."
    - "Assert `selected_branch_id` and `merge_summary` in the same integration test."
  debug_session: ".planning/debug/phase26-rd-agent-stale-run-payload.md"
- truth: "Duplicate first-layer `HypothesisSpec` categories fail before any extra dispatch, fork, DAG node creation, or round increment, and the duplicate-category error is explicitly asserted."
  status: failed
  reason: "User reported: validation order is correct, but the integration test only checks `dispatches == []` and misses `fork == 0`, `DAG == 0`, `current_round == 0`, and error-message assertions."
  severity: major
  test: 2
  root_cause: "The duplicate-category guard runs before side effects, but the integration test only asserts `dispatches == []`. The zero-side-effect invariant is therefore under-specified: forks, DAG nodes, round increments, and the error message are not locked by tests."
  artifacts:
    - path: "v3/orchestration/multi_branch_service.py"
      issue: "Duplicate-category validation is first-layer-only and intentionally runs before side effects."
    - path: "tests/test_phase26_integration.py"
      issue: "Duplicate-category integration test only asserts zero dispatches after the ValueError."
  missing:
    - "Assert the ValueError message contains `Duplicate approach_category`."
    - "Assert `run.branch_ids` remains unchanged after duplicate-category failure."
    - "Assert `state_store.list_dag_nodes(run_id)` stays empty after failure."
    - "Assert `current_round` remains `0` after failure."
    - "Add reverse coverage or documentation for duplicate-category behavior after round 0."
  debug_session: ".planning/debug/phase26-duplicate-category-zero-side-effects.md"
- truth: "Exploration-round DAG recording preserves meaningful diversity semantics: returned `dag_node_ids` and `pruned_branch_ids` match created nodes, node metrics remain internally consistent, and diversity data is not conflated between round-level metadata and node-level state."
  status: failed
  reason: "User reported: current behavior matches the narrow spec, but `diversity_score` is modeled as a round-level entropy value copied onto every node, `hypothesis_specs=None` with DAG enabled silently writes `0.0`, parent links stay hard-coded empty across rounds, and integration tests miss several invariants."
  severity: major
  test: 3
  root_cause: "`run_exploration_round()` computes one round-level Shannon entropy value and copies it into every created node as `node_metrics.diversity_score`, while also using `0.0` for both 'unknown because no HypothesisSpec' and 'true zero diversity'. The same code path hard-codes `parent_node_ids=[]`, so later rounds cannot form layered DAG topology."
  artifacts:
    - path: "v3/orchestration/multi_branch_service.py"
      issue: "Stores shared round-level entropy on every node and always creates root nodes with empty parent lists."
    - path: "tests/test_phase26_integration.py"
      issue: "Only asserts the copied entropy number, not node metric defaults or DAG-node-to-branch correspondence."
  missing:
    - "Separate round-level diversity metadata from node-scoped metrics, or explicitly define node-scoped diversity semantics."
    - "Differentiate 'unknown diversity because no HypothesisSpec was provided' from true zero-entropy cases."
    - "Wire `parent_node_ids` from selected parents for non-root rounds instead of hard-coding `[]`."
    - "Assert default node metrics and DAG node-to-dispatched-branch correspondence in integration tests."
  debug_session: ".planning/debug/phase26-diversity-metric-modeling.md"
- truth: "When `auto_prune=False`, exploration still dispatches and increments `current_round`, returns empty `pruned_branch_ids`, and skips prune execution even if a prune service is present."
  status: failed
  reason: "User reported: short-circuit logic is correct, but the existing test only covers the case where `prune_service=None`, so it does not prove that a real prune service is skipped. Review also notes that `rd_agent()` does not expose `auto_prune` and board semantics are untested across prune-on/off paths."
  severity: major
  test: 4
  root_cause: "The runtime gate is correct, but verification only covers the no-prune-service path. There is no spy-backed proof that an existing prune service is skipped when `auto_prune=False`, and `rd_agent()` does not expose the flag to entrypoint callers."
  artifacts:
    - path: "v3/orchestration/multi_branch_service.py"
      issue: "Prune is correctly gated, but returned board semantics differ between prune-on and prune-off paths."
    - path: "tests/test_phase26_integration.py"
      issue: "The only `auto_prune=False` test injects no prune service, so it cannot prove skip behavior."
    - path: "v3/entry/rd_agent.py"
      issue: "Does not accept or forward an `auto_prune` parameter."
  missing:
    - "Add a spy-backed integration test where `prune_service` exists and `auto_prune=False` yields zero prune calls."
    - "Decide whether `auto_prune` is part of the public rd_agent contract; if yes, add and forward the parameter."
    - "Assert returned board semantics for prune-enabled vs prune-skipped paths."
  debug_session: ".planning/debug/phase26-auto-prune-skip-coverage.md"
- truth: "Legacy string-hypothesis exploration remains usable without `HypothesisSpec`, with one unambiguous input-precedence rule and without unintended Phase 26 side effects or silent no-op rounds."
  status: failed
  reason: "User reported: legacy string paths still run, but `rd_agent()` now unconditionally creates DAG/prune side effects for legacy calls, there is a precedence conflict when both `branch_hypotheses` and `hypothesis_specs` are provided, and empty hypothesis lists can complete as a silent no-op."
  severity: major
  test: 5
  root_cause: "Legacy string-hypothesis calls still execute, but the compatibility contract is no longer explicit. `rd_agent()` now always wires DAG/prune services into multi-branch runs, mixed `branch_hypotheses` + `hypothesis_specs` input follows different precedence rules in the entrypoint and service layers, and empty effective hypothesis lists are treated as a successful no-op round."
  artifacts:
    - path: "v3/entry/rd_agent.py"
      issue: "Always injects Phase 26 DAG/prune services and forwards mixed hypothesis inputs without a single precedence rule."
    - path: "v3/orchestration/multi_branch_service.py"
      issue: "Always prefers `hypothesis_specs` when present and accepts empty effective hypothesis lists."
    - path: "tests/test_phase16_rd_agent.py"
      issue: "Legacy tests do not assert returned dispatch structure together with the intended compatibility semantics."
  missing:
    - "Define one precedence rule for `branch_hypotheses` vs `hypothesis_specs`, or reject mixed input explicitly."
    - "Decide whether legacy string-hypothesis runs should remain side-effect neutral; if yes, gate DAG/prune wiring, otherwise update the contract and tests to make the new side effects explicit."
    - "Reject empty effective hypothesis lists before exploration starts."
    - "Strengthen legacy rd_agent tests to assert returned dispatch structure and chosen compatibility behavior."
  debug_session: ".planning/debug/phase26-legacy-hypothesis-precedence.md"
