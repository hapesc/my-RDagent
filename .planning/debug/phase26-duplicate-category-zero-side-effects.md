---
status: investigating
trigger: "UAT Test 2: duplicate first-layer categories should fail before any extra dispatch, fork, DAG node creation, or round increment"
created: 2026-03-23T10:02:22Z
updated: 2026-03-23T10:02:22Z
---

## Current Focus

hypothesis: The code enforces duplicate-category rejection early enough, but the integration test does not lock the zero-side-effect invariant.
test: Compare the validation ordering in `multi_branch_service.py` with the assertions in the duplicate-category integration test.
expecting: If true, the bug is primarily a verification gap rather than a runtime ordering bug.
next_action: Hand off assertion hardening to gap-closure planning.

## Symptoms

expected: Duplicate first-layer categories raise a duplicate-category error before any extra fork, dispatch, DAG node creation, or round increment.
actual: Runtime ordering is correct, but the test only asserts `dispatches == []` and misses the other zero-side-effect guarantees.
errors: ValueError is raised, but the message is not asserted.
reproduction: `UAT Test 2` / inspect duplicate-category path in `run_exploration_round()`.
started: Discovered during Phase 26 UAT.

## Eliminated

## Evidence

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:66-71`
  found: Duplicate-category validation runs before label derivation, fork, dispatch, DAG creation, prune, or round increment.
  implication: Current runtime ordering is correct.

- timestamp: 2026-03-23T10:02:22Z
  checked: `tests/test_phase26_integration.py:204-224`
  found: The test only asserts `dispatches == []` after the ValueError.
  implication: A regression that leaks forks, DAG nodes, or round increments could slip through without failing this test.

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:66`
  found: The duplicate check is gated on `run.current_round == 0`.
  implication: Later-round behavior is intentional-but-implicit and needs explicit documentation or reverse coverage.

## Resolution

root_cause: Duplicate-category rejection is implemented in the right place, but the test contract is too weak: it does not assert zero forks, zero DAG nodes, zero round increment, or the duplicate-category error message, so the intended invariant is under-specified.
fix: ""
verification: ""
files_changed: []
