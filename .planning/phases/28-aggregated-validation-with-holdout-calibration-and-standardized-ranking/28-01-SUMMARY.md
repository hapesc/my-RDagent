---
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
plan: 01
subsystem: contracts
tags: [holdout, pydantic, protocols, ranking]
requires:
  - phase: 27-cross-branch-communication-and-multi-trace-solution-merge
    provides: DAG node metrics, MERGED edge topology, and convergence regression coverage
provides:
  - holdout-ready exploration contracts
  - fold split and evaluation protocol surface
  - pure ranking, filtering, and candidate collection helpers
affects: [phase28-plan02, phase28-plan03, phase28-plan04]
tech-stack:
  added: []
  patterns: [immutable contract extension, ports-first holdout boundary, empty-safe pure algorithms]
key-files:
  created:
    - .planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-01-SUMMARY.md
    - v3/ports/holdout_port.py
    - v3/algorithms/holdout.py
  modified:
    - v3/contracts/exploration.py
    - tests/test_phase28_holdout_ports.py
    - tests/test_phase28_ranking.py
key-decisions:
  - "FoldSpec stays in v3/ports/holdout_port.py instead of contracts to avoid circular imports with the exploration contract surface."
  - "collect_candidate_ids remains the canonical exported helper, while a non-exported collect_candidates alias absorbs the plan-text naming mismatch without widening the public API."
patterns-established:
  - "Phase 28's typed surface is split cleanly: persistence contracts in contracts, protocol seams in ports, pure ranking logic in algorithms."
  - "Holdout helpers should be empty-safe at the function boundary instead of depending on downstream callers to guard every edge case."
requirements-completed: [P28-HOLDOUT, P28-RANK, P28-COLLECT, P28-SUBMIT]
duration: 41min
completed: 2026-03-24
---

# Phase 28 Plan 01: Holdout Contracts and Algorithms Summary

**Phase 28 now has the typed finalization surface: holdout-aware node metrics, final submission contracts, fold/evaluation ports, and pure ranking helpers that downstream services can import without circular dependencies**

## Performance

- **Duration:** 41 min
- **Started:** 2026-03-24T11:22:57+08:00
- **Completed:** 2026-03-24T12:03:36+08:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended `NodeMetrics` with backward-compatible `holdout_mean` and `holdout_std` fields, and added `CandidateRankEntry` plus `FinalSubmissionSnapshot` as the persisted finalization contracts.
- Added `v3/ports/holdout_port.py` with `FoldSpec`, `HoldoutSplitPort`, `EvaluationPort`, a default `StratifiedKFoldSplitter`, and deterministic stubs for tests.
- Added `v3/algorithms/holdout.py` with empty-safe ranking, quality-threshold filtering, and candidate collection helpers, then verified the new surface against dedicated Phase 28 tests plus Phase 16/27 regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend NodeMetrics and add final submission contracts** - `86bed9e`, `8db78dd` (test, feat)
2. **Task 2: Create holdout ports and pure algorithms** - `86bed9e`, `2e35657` (test, feat)

_Note: TDD tasks used a shared RED commit before the implementation commits._

## Files Created/Modified

- `v3/contracts/exploration.py` - Adds holdout-aware node metrics plus ranked final submission contracts.
- `v3/ports/holdout_port.py` - Defines fold split / evaluation protocols and deterministic test doubles.
- `v3/algorithms/holdout.py` - Implements ranking, median filtering, and candidate collection helpers.
- `tests/test_phase28_holdout_ports.py` - Covers fold contract construction, splitter behavior, and evaluation defaults.
- `tests/test_phase28_ranking.py` - Covers contract validation, ranking order, median filtering, and empty-input edge cases.
- `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-01-SUMMARY.md` - Captures execution evidence and downstream assumptions.

## Decisions Made

- Kept the new finalization persistence surface in `v3/contracts/exploration.py`, because downstream plans need those types independent of the holdout port module.
- Added a compatibility alias for `collect_candidates` while keeping `collect_candidate_ids` as the canonical exported helper, because the latest plan docs still contain both names.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bridged the collect_candidates vs collect_candidate_ids naming split**
- **Found during:** Task 2 (Create holdout ports and pure algorithms)
- **Issue:** Plan 01 frontmatter still referenced `collect_candidates`, while Task 2 acceptance criteria and Plan 02 integration text require `collect_candidate_ids`.
- **Fix:** Implemented `collect_candidate_ids` as the canonical exported helper and added a non-exported `collect_candidates` alias for compatibility.
- **Files modified:** `v3/algorithms/holdout.py`
- **Verification:** `uv run pytest tests/test_phase28_ranking.py tests/test_phase28_holdout_ports.py -x -q`
- **Committed in:** `2e35657`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Resolved a documentation/API mismatch without expanding scope, so downstream plans can rely on one canonical import path while older plan text still resolves.

## Issues Encountered

- A plain `python3 -c ...` import smoke check failed because the system interpreter lacked repo-managed dependencies; rerunning the same check via `uv run python -c ...` verified there is no circular import problem in the new Phase 28 modules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 28 Plan 02 can now build `HoldoutValidationService` on top of stable contracts, ports, and pure ranking helpers.
- The merge-path change in the updated Plan 02 is now clear: remove `validate_merge_holdout`, keep merge-time inline comparison, and reserve real holdout finalization for the dedicated service path.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase28_ranking.py tests/test_phase28_holdout_ports.py -x -q` exits 0.
- Verified `uv run pytest tests/test_phase16_convergence.py tests/test_phase27_integration.py -x -q` exits 0.
- Verified `uv run python -c "from v3.ports.holdout_port import FoldSpec, HoldoutSplitPort, EvaluationPort; from v3.contracts.exploration import FinalSubmissionSnapshot, CandidateRankEntry; from v3.algorithms.holdout import rank_candidates"` exits 0.
- Verified commits `86bed9e`, `8db78dd`, and `2e35657` exist in git history.
- Verified summary file exists at `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-01-SUMMARY.md`.

---
*Phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking*
*Completed: 2026-03-24*
