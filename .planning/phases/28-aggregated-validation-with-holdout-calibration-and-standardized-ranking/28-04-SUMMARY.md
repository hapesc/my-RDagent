---
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
plan: 04
subsystem: testing
tags: [integration, finalization, merged-nodes, guidance]
requires:
  - phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
    provides: holdout contracts, finalization service, activation wiring, and guidance rendering
provides:
  - real-service lifecycle validation
  - merged-node candidate coverage
  - final submission persistence verification
affects: [verify-phase28, milestone-v1.3]
tech-stack:
  added: []
  patterns: [service-level finalization fixture, parent-linked round lineage, merged-candidate integration assertions]
key-files:
  created:
    - .planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-04-SUMMARY.md
    - tests/test_phase28_integration.py
  modified: []
key-decisions:
  - "The integration fixture uses a parent-selector stub so round-two DAG nodes inherit round-one ancestry and finalization can assert lineage truth."
  - "The same real service graph covers auto-finalization, early finalization, merged-node inclusion, guidance rendering, and final submission persistence."
patterns-established:
  - "Finalization lifecycle tests should exercise the real persistence and orchestration stack instead of mock-only call assertions."
  - "Merged candidates should be asserted by node identity in the ranked submission list, not only by branch-level summaries."
requirements-completed: [P28-HOLDOUT, P28-RANK, P28-COLLECT, P28-ACTIVATE, P28-REPLACE, P28-SUBMIT, P28-PRESENT]
duration: 3min
completed: 2026-03-24
---

# Phase 28 Plan 04: Full Lifecycle Integration Summary

**A real-service Phase 28 fixture now proves the full lifecycle from exploration rounds to auto-finalization, including merged candidates, ancestry tracing, persisted final submissions, early finalization, and rendered operator guidance**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T12:31:09+08:00
- **Completed:** 2026-03-24T12:34:07+08:00
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added a full lifecycle fixture that wires `ArtifactStateStore`, `DAGService`, `HoldoutValidationService`, `MultiBranchService`, `BranchMergeService`, and the finalization guidance layer together without mocks on the critical path.
- Proved auto-finalization at `max_rounds`, explicit early finalization, winner persistence, ancestry-chain capture, and guidance rendering all operate on the same `FinalSubmissionSnapshot`.
- Verified MERGED nodes created through the real merge service can enter the final candidate pool and appear in the ranked submission list by node ID.

## Task Commits

Each task was committed atomically:

1. **Task 1: Full Phase 28 lifecycle integration test** - `d5cd896` (test)

## Files Created/Modified

- `tests/test_phase28_integration.py` - Real-service lifecycle coverage for auto-finalize, early finalize, merged candidates, ancestry, persistence, and guidance.
- `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-04-SUMMARY.md` - Captures the integration-test evidence and the final verification scope.

## Decisions Made

- Kept the integration fixture deterministic by scoring candidates by branch ID through a real state-store lookup, rather than stubbing out the orchestration path.
- Added a lightweight parent-selector stub so round-two DAG nodes carry real ancestry, which lets the integration test verify `ancestry_chain` honestly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first integration-test draft had a test-side unpacking error in `test_early_finalization`; fixing the fixture call resolved it without requiring any production-code changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 28 execution is now fully represented on disk with plan summaries 01-04 and a passing real-service integration harness.
- The next honest step is verification / milestone closure, not more Phase 28 implementation churn.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase28_ranking.py tests/test_phase28_holdout_ports.py tests/test_phase28_holdout_service.py tests/test_phase28_activation.py tests/test_phase28_integration.py tests/test_phase27_merge_synthesis.py tests/test_phase27_integration.py tests/test_phase16_convergence.py -x -q` exits 0.
- Verified commit `d5cd896` exists in git history.
- Verified summary file exists at `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-04-SUMMARY.md`.

---
*Phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking*
*Completed: 2026-03-24*
