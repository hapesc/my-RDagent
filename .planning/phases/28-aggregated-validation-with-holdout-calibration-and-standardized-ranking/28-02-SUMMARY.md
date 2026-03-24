---
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
plan: 02
subsystem: orchestration
tags: [holdout, finalization, persistence, merge]
requires:
  - phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
    provides: holdout-ready contracts, ports, and pure ranking helpers
provides:
  - holdout finalization orchestration
  - final submission persistence
  - proxy-free merge gating
affects: [phase28-plan03, phase28-plan04, verify-phase28]
tech-stack:
  added: []
  patterns: [service-over-port finalization, explicit final submission persistence, inline merge gate]
key-files:
  created:
    - .planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-02-SUMMARY.md
    - v3/orchestration/holdout_validation_service.py
  modified:
    - v3/ports/state_store.py
    - v3/orchestration/artifact_state_store.py
    - v3/algorithms/merge.py
    - v3/orchestration/branch_merge_service.py
    - tests/test_phase28_holdout_service.py
    - tests/test_phase28_activation.py
    - tests/test_phase27_merge_synthesis.py
key-decisions:
  - "HoldoutValidationService owns the real K-fold finalization path and persists FinalSubmissionSnapshot through StateStorePort."
  - "Merge-time gating no longer imports a proxy helper; it keeps the same inline score comparison while true holdout evaluation stays reserved for finalization."
patterns-established:
  - "Final submission persistence is a first-class state-store capability, not an overloaded run snapshot field."
  - "When a transitional proxy is retired, keep the behavior inline at the call site until the true orchestration path is ready, instead of introducing another indirection."
requirements-completed: [P28-HOLDOUT, P28-REPLACE, P28-COLLECT]
duration: 10min
completed: 2026-03-24
---

# Phase 28 Plan 02: Holdout Finalization Service Summary

**Phase 28 now has a real holdout finalization service that collects frontier plus MERGED candidates, ranks them across K folds, persists the winning submission, and removes the old merge holdout proxy without changing merge-time behavior**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-24T12:08:09+08:00
- **Completed:** 2026-03-24T12:18:37+08:00
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added `HoldoutValidationService` to collect eligible DAG candidates, filter by median validation score, evaluate across injected folds, rank by mean/std, persist holdout metrics onto DAG nodes, and write a `FinalSubmissionSnapshot`.
- Extended `StateStorePort` and `ArtifactStateStore` with explicit final submission persistence methods so later plans can load the finalized winner without scraping other artifacts.
- Removed `validate_merge_holdout` from `v3/algorithms/merge.py` and switched `BranchMergeService` back to a direct inline `holdout_score >= best_single_score` gate, matching the updated plan that reserves real holdout evaluation for budget-exhaustion finalization.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build HoldoutValidationService and extend StateStorePort** - `78df5db`, `4ff14b4` (test, feat)
2. **Task 2: Replace validate_merge_holdout proxy in BranchMergeService** - `78df5db`, `d334529` (test, fix)

_Note: The RED commit seeded both Wave 2 test files before the implementation and proxy-removal commits._

## Files Created/Modified

- `v3/orchestration/holdout_validation_service.py` - Implements the Phase 28 finalization pipeline over injected split/evaluation ports.
- `v3/ports/state_store.py` - Adds `write_final_submission` and `load_final_submission` to the persistence boundary.
- `v3/orchestration/artifact_state_store.py` - Persists final submission snapshots on disk and supports round-trip loading.
- `v3/algorithms/merge.py` - Removes the obsolete `validate_merge_holdout` proxy.
- `v3/orchestration/branch_merge_service.py` - Keeps merge gating as an inline comparison after proxy removal.
- `tests/test_phase28_holdout_service.py` - Verifies holdout finalization, ancestry tracking, merged-node collection, and submission persistence.
- `tests/test_phase28_activation.py` - Verifies proxy removal and merge gate behavior under the updated Phase 28 plan.
- `tests/test_phase27_merge_synthesis.py` - Stops importing the removed proxy and keeps Phase 27 merge behavior covered through service tests.
- `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-02-SUMMARY.md` - Captures execution evidence and latest plan interpretation.

## Decisions Made

- Persisted `FinalSubmissionSnapshot` as its own artifact under the state-store boundary rather than burying it inside existing run metadata.
- Followed the updated plan split strictly: real holdout evaluation happens only in `HoldoutValidationService.finalize`, while merge-time gating stays lightweight and inline.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03 can now wire `HoldoutValidationService` into `MultiBranchService` for automatic and operator-triggered finalization.
- Plan 04 can build the end-to-end lifecycle test on top of a real persisted `FinalSubmissionSnapshot` path instead of mocks or proxy gates.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase28_holdout_service.py tests/test_phase28_activation.py tests/test_phase27_merge_synthesis.py tests/test_phase27_integration.py -x -q` exits 0.
- Verified commits `78df5db`, `4ff14b4`, and `d334529` exist in git history.
- Verified summary file exists at `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-02-SUMMARY.md`.

---
*Phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking*
*Completed: 2026-03-24*
