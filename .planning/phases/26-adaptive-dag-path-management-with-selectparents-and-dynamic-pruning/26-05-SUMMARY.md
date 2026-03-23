---
phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning
plan: 05
subsystem: orchestration
tags: [gap-closure, rd-agent, validation, compatibility, testing]
requires:
  - phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning
    provides: diagnosed UAT gaps, debug sessions, and baseline phase 26 implementation
provides:
  - corrected rd_agent multi-branch return contract
  - explicit mixed-input validation and auto_prune entrypoint control
  - hardened duplicate/empty/prune-skip regression invariants
affects: [26-06, verify-phase26, phase16-compat]
tech-stack:
  added: []
  patterns: [entry-boundary compatibility gating, explicit invalid-input rejection, stronger invariant-driven integration tests]
key-files:
  created:
    - .planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-05-SUMMARY.md
  modified:
    - v3/entry/rd_agent.py
    - v3/orchestration/multi_branch_service.py
    - tests/test_phase26_integration.py
    - tests/test_phase16_rd_agent.py
key-decisions:
  - "Mixed branch_hypotheses + hypothesis_specs input is now a hard error instead of relying on conflicting implicit precedence."
  - "Legacy string-only multi-branch runs keep functioning without inheriting Phase 26 DAG/prune side effects."
  - "Validation tests now prove invariants with concrete state assertions instead of inferring them from one symptom like dispatch count."
patterns-established:
  - "When a new structured input path coexists with a legacy path, make the authority rule explicit or reject mixed input."
  - "Human-reviewed invariants should be codified as state assertions, not left implicit in broad integration success."
requirements-completed: [P26-ROUND, P26-SELECT, P26-PRUNE]
duration: 8min
completed: 2026-03-23
---

# Phase 26 Plan 05: Gap Closure for rd_agent Contract and Validation Invariants

**Phase 26’s outward contract is now tightened: rd_agent returns fresh run state, mixed structured/legacy inputs fail explicitly, auto_prune can be controlled from the entrypoint, legacy string-only callers avoid new DAG/prune side effects, and the fragile validation gaps from UAT are locked by regression tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T10:06:20Z
- **Completed:** 2026-03-23T10:14:52Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Fixed the stale multi-branch rd_agent payload by reloading persisted run state before returning it.
- Added explicit mixed-input rejection and `auto_prune` forwarding at the rd_agent entry boundary.
- Preserved legacy string-only multi-branch compatibility by not wiring DAG/prune services unless structured hypotheses are actually in use.
- Hardened `MultiBranchService` tests around empty hypothesis input, duplicate-category zero side effects, and prune-skip behavior with a present spy prune service.

## Task Commits

Each task was committed atomically:

1. **Task 1: Repair rd_agent multi-branch contract and compatibility boundary** - `8596cf3` (fix)
2. **Task 2: Lock validation and prune-skip invariants in MultiBranchService tests** - `be2d93c` (test)

## Files Created/Modified

- `v3/entry/rd_agent.py` - Reloads persisted run state before return, exposes `auto_prune`, rejects mixed structured/legacy input, and gates DAG/prune wiring behind structured hypotheses.
- `v3/orchestration/multi_branch_service.py` - Rejects empty effective hypothesis lists early and uses a direct `BranchForkRequest` import.
- `tests/test_phase26_integration.py` - Adds regression coverage for returned run state, mixed-input failure, empty-hypothesis rejection, duplicate-category zero-side-effects, and prune-skip with a present spy service.
- `tests/test_phase16_rd_agent.py` - Adds legacy return-structure assertion for `structuredContent.dispatches`.
- `.planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-05-SUMMARY.md` - Captures gap-closure evidence and compatibility choices.

## Decisions Made

- Treated mixed legacy/structured hypotheses as invalid input instead of choosing a silent precedence winner.
- Kept Phase 26 structured features opt-in at the entry boundary, because retrofitting DAG/prune side effects onto legacy callers would be an undeclared compatibility break.
- Strengthened tests to assert the actual state invariants under review rather than assuming one symptom implies the rest.

## Deviations from Plan

None - plan executed as written. The only implementation detail adjustment was keeping the service-level cleanup (`BranchForkRequest` direct import) within the same task because the file was already being touched for validation behavior.

## Issues Encountered

- `tests/test_phase26_integration.py` spans both entrypoint and service invariants, so task-level commits required temporarily separating Task 2 assertions and then restoring them after Task 1 committed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `26-06` can now focus on diversity / DAG semantics without the blocker and compatibility bugs obscuring later verification.
- After `26-06`, Phase 26 should be re-run through `$gsd:verify-work 26` instead of assumed verified.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase26_integration.py tests/test_phase16_rd_agent.py -x -q` exits 0.
- Verified `uv run pytest tests/test_phase26_*.py tests/test_phase16_rd_agent.py tests/test_phase16_convergence.py -x -q` exits 0.
- Verified task commits `8596cf3` and `be2d93c` exist in git history.
- Verified summary file exists at `.planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-05-SUMMARY.md`.

---
*Phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning*
*Completed: 2026-03-23*
