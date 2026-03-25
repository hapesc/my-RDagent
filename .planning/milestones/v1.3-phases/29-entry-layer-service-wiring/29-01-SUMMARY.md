---
phase: 29-entry-layer-service-wiring
plan: 01
subsystem: orchestration
tags: [holdout-validation, branch-sharing, memory-state-store, finalization-guidance, entry-wiring]

# Dependency graph
requires:
  - phase: 27-sharing-kernel-and-merge-synthesis
    provides: BranchShareService, MemoryService, MemoryStateStore, interaction kernel
  - phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
    provides: HoldoutValidationService, EvaluationPort, HoldoutSplitPort, build_finalization_guidance
provides:
  - BranchShareService wired into rd_agent public entrypoint
  - HoldoutValidationService wired into rd_agent public entrypoint
  - Finalization guidance and submission in rd_agent response payload
  - Dedicated MemoryStateStore injection for MemoryService (not ArtifactStateStore)
  - holdout_evaluation_port required-parameter guard (ValueError)
  - memory_store explicit DI parameter on rd_agent
affects: [milestone-v1.3-closeout, future-embedding-port-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Unified guard condition for optional services (hypothesis_specs is not None and dag_service is not None)
    - Dedicated MemoryStorePort fallback construction from state_store._root
    - Required-port validation with descriptive ValueError

key-files:
  created:
    - tests/test_phase29_entry_wiring.py
  modified:
    - v3/entry/rd_agent.py
    - tests/test_phase26_integration.py

key-decisions:
  - "MemoryStateStore constructed as fallback from state_store._root when memory_store param is None"
  - "holdout_evaluation_port is required when hypothesis_specs is provided (raises ValueError)"
  - "Both BranchShareService and HoldoutValidationService use unified guard: hypothesis_specs is not None and dag_service is not None"
  - "BranchShareService inert without EmbeddingPort accepted; SHARED DAG edges deferred to future phase"

patterns-established:
  - "Required-port guard: validate port availability early with descriptive ValueError instead of letting downstream services crash with AttributeError"
  - "Dedicated store construction: when a service needs a different port interface, construct the correct implementation rather than passing the wrong store type"

requirements-completed: [P28-HOLDOUT, P28-ACTIVATE, P28-SUBMIT, P28-PRESENT, P27-KERNEL, P27-INJECT, GUIDE-05]

# Metrics
duration: 15min
completed: 2026-03-24
---

# Phase 29 Plan 01: Entry Layer Service Wiring Summary

**Wire HoldoutValidationService, BranchShareService, and finalization guidance into rd_agent with dedicated MemoryStateStore and 8 integration tests proving full E2E flow**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-24T11:12:38Z
- **Completed:** 2026-03-24T11:27:17Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Wired BranchShareService and HoldoutValidationService into rd_agent public entrypoint with unified guard condition
- Added finalization_guidance and finalization_submission to multi-branch response payload
- Constructed dedicated MemoryStateStore for MemoryService (not ArtifactStateStore, which does not implement MemoryStorePort)
- Added holdout_evaluation_port required-parameter guard (ValueError) preventing AttributeError propagation through _try_finalize
- Created 8 integration tests proving: service injection, finalization trigger, no-finalization guard, E2E winner flow, P27-INJECT paths, and MemoryStateStore DI

## Post-review closeout

After Phase 29 review, we applied one follow-up hardening pass before closing
the phase:

- Fixed the public response semantics so finalization is authoritative: when
  `explore_round.finalization_submission` exists, `rd_agent()` now returns the
  holdout winner as `selected_branch_id`, sets
  `recommended_next_step="review final submission"`, and skips convergence
  fallback in the public payload.
- Strengthened the entry-level regression by replacing the placeholder
  equal-score E2E case with a deterministic label-scored holdout evaluator that
  proves the winner branch is surfaced truthfully.
- Added the narrow contract regression asserting `hypothesis_specs` requires
  `holdout_evaluation_port`.
- Documented the structured multi-branch contract in `README.md`,
  `skills/rd-agent/SKILL.md`, and
  `skills/rd-agent/workflows/start-contract.md`, including the hard dependency
  on `holdout_evaluation_port`.
- Restored the rd-agent skill contract test surface by adding the missing
  skill-local `skills/rd-agent/references/failure-routing.md` reference.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire BranchShareService + HoldoutValidationService + finalization guidance into rd_agent.py**
   - `6aa33b9` (test: RED phase failing tests)
   - `f11d74e` (feat: GREEN phase implementation)
   - `6dd4040` (chore: remove temporary RED phase scaffold)

2. **Task 2: Integration test proving E2E flow** - `ad00f1a` (feat: 8 integration tests + Phase 26 regression fix)

## Files Created/Modified
- `v3/entry/rd_agent.py` - Added imports for BranchShareService, HoldoutValidationService, MemoryService, MemoryStateStore; added memory_store, holdout_split_port, holdout_evaluation_port params; wired services with unified guard; added finalization guidance to response
- `tests/test_phase29_entry_wiring.py` - Integration tests proving full E2E flow through public entrypoint, finalization-first response semantics, and the required holdout-evaluation-port guard
- `tests/test_phase26_integration.py` - Added holdout_evaluation_port to rd_agent call (regression fix from new required-param guard)
- `README.md` - Documented the structured multi-branch contract and finalization-first public response semantics
- `skills/rd-agent/SKILL.md` - Declared the structured multi-branch optional fields and preserved the Phase 20 public-skill contract headings
- `skills/rd-agent/workflows/start-contract.md` - Documented `hypothesis_specs`, `holdout_evaluation_port`, and `holdout_split_port` in the recommended multi-branch contract
- `skills/rd-agent/references/failure-routing.md` - Added the missing skill-local failure-routing reference used by the rd-agent contract tests

## Decisions Made
- MemoryStateStore constructed as fallback from `state_store._root` when `memory_store` param is None -- keeps backward compatibility while ensuring correct MemoryStorePort implementation
- holdout_evaluation_port is required when hypothesis_specs is provided -- prevents destructive AttributeError propagation through _try_finalize's narrow except clause
- Unified guard condition (`hypothesis_specs is not None and dag_service is not None`) for both services -- prevents fragile coupling to the assumption that dag_service is only constructed when hypothesis_specs is not None
- BranchShareService is inert without EmbeddingPort (compute_sharing_candidates returns []) -- accepted as known limitation, documented with TODO comments

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Phase 26 regression from new required-parameter guard**
- **Found during:** Task 2 (integration tests)
- **Issue:** `test_rd_agent_accepts_hypothesis_specs_and_wires_phase26_services` called rd_agent with hypothesis_specs but without holdout_evaluation_port, triggering the new ValueError guard
- **Fix:** Added `holdout_evaluation_port=StubEvaluationPort()` and `holdout_split_port=StubHoldoutSplitPort()` to the Phase 26 test
- **Files modified:** tests/test_phase26_integration.py
- **Verification:** Full test suite passes (353/353 excluding 2 pre-existing Phase 20 failures)
- **Committed in:** ad00f1a (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Regression fix was necessary for correctness. No scope creep.

## Issues Encountered
- Finalization not triggering in tests because RunBoardSnapshot.max_rounds defaults to 20 -- resolved by monkeypatching write_run_snapshot to set max_rounds=1 in tests that need finalization
- Pre-existing test failures in test_phase20_rd_agent_skill_contract.py and test_phase20_stage_skill_contracts.py (checking for "## Required fields" in skill markdown) -- unrelated to Phase 29 changes, not addressed

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 27/28 services are now reachable through the public rd_agent entrypoint
- Phase 29 closes the 3 integration gaps and 2 broken E2E flows identified in v1.3 milestone audit
- The public entry response is now unambiguous at finalization time: callers no longer need to reconcile a convergence fallback branch with a distinct holdout winner
- Full EmbeddingPort wiring for SHARED DAG edge creation deferred to future phase (documented with TODO comments)
- v1.3 milestone is ready for verification and closeout

---
*Phase: 29-entry-layer-service-wiring*
*Completed: 2026-03-24*
