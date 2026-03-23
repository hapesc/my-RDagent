---
status: investigating
trigger: "UAT Test 3: exploration-round DAG recording should preserve meaningful diversity semantics"
created: 2026-03-23T10:02:22Z
updated: 2026-03-23T10:02:22Z
---

## Current Focus

hypothesis: `diversity_score` currently encodes round-level entropy and is copied onto every node, which makes the field semantically ambiguous and blocks later layered-DAG use cases.
test: Inspect diversity-score computation and DAG node creation in `multi_branch_service.py`, then compare against test assertions.
expecting: If true, the code will attach one shared entropy value to every node, use `0.0` for both "unknown" and "true zero diversity," and always create root nodes.
next_action: Hand off a model clarification and test-hardening plan.

## Symptoms

expected: Exploration-round DAG recording returns node IDs and prune results while preserving coherent diversity semantics for the created topology.
actual: The current implementation returns the expected fields, but all nodes receive the same round-level entropy value, `0.0` conflates unknown vs zero diversity when no `HypothesisSpec` is present, and parent links remain empty across rounds.
errors: None reported as runtime exceptions.
reproduction: `UAT Test 3` / inspect DAG node creation with and without `hypothesis_specs`.
started: Discovered during Phase 26 UAT.

## Eliminated

## Evidence

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:109-122`
  found: One Shannon entropy value is computed from the round's category distribution and copied into every created node as `NodeMetrics(diversity_score=diversity_score)` with `parent_node_ids=[]`.
  implication: `node_metrics.diversity_score` is currently round-scoped data stored as if it were node-scoped, and later rounds cannot form layered DAG topology.

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:111-114`
  found: When `hypothesis_specs` is absent, `diversity_score` remains the default `0.0`.
  implication: The code cannot distinguish "unknown because no structured categories were provided" from "real zero diversity."

- timestamp: 2026-03-23T10:02:22Z
  checked: `tests/test_phase26_integration.py:192-201`
  found: The test only asserts the shared entropy value and does not assert default metric fields or DAG-node-to-branch correspondence.
  implication: Metric semantics and topology invariants are weakly verified.

## Resolution

root_cause: Exploration-round DAG creation overloads `node_metrics.diversity_score` with a round-level entropy value, uses `0.0` for both missing and meaningful diversity states, and hard-codes every created node as a root (`parent_node_ids=[]`). Tests only verify the copied entropy number, not the underlying semantics.
fix: ""
verification: ""
files_changed: []
