---
status: investigating
trigger: "UAT Test 5: legacy string hypotheses should remain usable without HypothesisSpec and without ambiguous precedence or unintended side effects"
created: 2026-03-23T10:02:22Z
updated: 2026-03-23T10:02:22Z
---

## Current Focus

hypothesis: The legacy string-hypothesis path still runs, but Phase 26 introduced unconditional DAG/prune side effects and conflicting precedence rules between `rd_agent()` and `MultiBranchService`.
test: Compare legacy multi-branch wiring in `rd_agent.py` with effective label selection in `multi_branch_service.py`, and inspect legacy test coverage.
expecting: If true, legacy runs will still work functionally, but side effects and mixed-input precedence will be undefined.
next_action: Hand off compatibility and input-validation decisions to gap-closure planning.

## Symptoms

expected: Legacy string-hypothesis exploration remains usable without needing `HypothesisSpec`, with one unambiguous precedence rule and no silent no-op rounds.
actual: Legacy string paths still run, but `rd_agent()` now always injects DAG/prune services into multi-branch calls, mixed `branch_hypotheses` + `hypothesis_specs` input follows conflicting precedence rules, and empty effective hypothesis lists succeed as a silent no-op exploration round.
errors: None reported as runtime exceptions.
reproduction: `UAT Test 5` / inspect legacy rd_agent multi-branch path and mixed-input behavior.
started: Discovered during Phase 26 UAT.

## Eliminated

## Evidence

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/entry/rd_agent.py:249-314`
  found: `rd_agent()` prefers `branch_hypotheses` when deriving `derived_hypotheses`, but always forwards both `hypotheses=derived_hypotheses or []` and `hypothesis_specs=hypothesis_specs`, while unconditionally wiring `DAGService` and `BranchPruneService`.
  implication: Legacy runs now inherit Phase 26 side effects, and mixed-input precedence is ambiguous.

- timestamp: 2026-03-23T10:02:22Z
  checked: `v3/orchestration/multi_branch_service.py:73-80`
  found: `run_exploration_round()` always prefers `hypothesis_specs` over `hypotheses` when specs are present, and it does not reject an empty effective hypothesis list.
  implication: Entrypoint and service precedence can diverge, and empty rounds can silently succeed.

- timestamp: 2026-03-23T10:02:22Z
  checked: `tests/test_phase16_rd_agent.py:66-165`
  found: Legacy tests cover dispatch side effects and some return fields, but they do not assert the returned `dispatches` structure together with the intended side-effect contract.
  implication: Compatibility drift can slip through without a clear test failure.

## Resolution

root_cause: Legacy string-hypothesis calls still work, but the compatibility contract is no longer explicit. `rd_agent()` now unconditionally enables Phase 26 DAG/prune side effects for all multi-branch runs, mixed `branch_hypotheses` + `hypothesis_specs` input follows different precedence rules in the entrypoint and service layers, and empty hypothesis sets are treated as a successful no-op round.
fix: ""
verification: ""
files_changed: []
