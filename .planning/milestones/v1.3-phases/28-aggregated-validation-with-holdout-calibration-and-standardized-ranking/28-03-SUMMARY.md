---
phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
plan: 03
subsystem: orchestration
tags: [activation, guidance, finalization, multi-branch]
requires:
  - phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking
    provides: holdout finalization service, final submission persistence, and proxy-free merge gating
provides:
  - auto-finalization at budget exhaustion
  - operator-triggered early finalization
  - finalization guidance rendering
affects: [phase28-plan04, verify-phase28]
tech-stack:
  added: []
  patterns: [result-carried finalization, budget-gated orchestration trigger, guidance detail rendering]
key-files:
  created:
    - .planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-03-SUMMARY.md
  modified:
    - v3/contracts/tool_io.py
    - v3/orchestration/multi_branch_service.py
    - v3/orchestration/operator_guidance.py
    - tests/test_phase28_activation.py
key-decisions:
  - "ExploreRoundResult now carries finalization_submission directly so the caller can observe auto-finalization without scraping persisted state."
  - "Finalization guidance reuses the shared OperatorGuidance contract and renderer, with ranking details emitted through next_step_detail."
patterns-established:
  - "Budget-exhaustion triggers should attach their result to the primary response object instead of forcing a second lookup step."
  - "Operator-facing summaries should keep the winner and metric table in renderable text, not in side-channel metadata only."
requirements-completed: [P28-ACTIVATE, P28-PRESENT]
duration: 8min
completed: 2026-03-24
---

# Phase 28 Plan 03: Finalization Activation and Guidance Summary

**Exploration rounds now auto-finalize at the iteration ceiling, operators can trigger early finalization explicitly, and the winning submission renders through the shared guidance surface with holdout metrics and ranking details**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-24T12:22:56+08:00
- **Completed:** 2026-03-24T12:31:09+08:00
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `finalization_submission` to `ExploreRoundResult` and wired `MultiBranchService` to trigger `HoldoutValidationService.finalize()` automatically when `current_round + 1 >= max_rounds`.
- Added explicit `finalize_early()` to `MultiBranchService`, so operators can request finalization before the budget ceiling without abusing merge logic.
- Added `build_finalization_guidance()` to the shared operator-guidance layer and verified the rendered text includes the winner node and `holdout_mean`/`holdout_std` leaderboard details.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add auto-finalization trigger and explicit early-finalization to MultiBranchService** - `1ca68e3`, `81a5b61` (test, feat)
2. **Task 2: Add finalization guidance builder** - `1ca68e3`, `d38821a` (test, feat)

_Note: The RED activation/guidance expansion landed first in `tests/test_phase28_activation.py`, then the orchestration and guidance code followed in separate commits._

## Files Created/Modified

- `v3/contracts/tool_io.py` - Extends `ExploreRoundResult` with optional `finalization_submission`.
- `v3/orchestration/multi_branch_service.py` - Triggers holdout finalization at budget exhaustion and exposes `finalize_early`.
- `v3/orchestration/operator_guidance.py` - Renders finalization summary text through the shared guidance contract.
- `tests/test_phase28_activation.py` - Covers auto-finalize, early finalize, `finalization_submission`, and finalization guidance rendering.
- `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-03-SUMMARY.md` - Records execution evidence and the activation/guidance design split.

## Decisions Made

- Kept auto-finalization inside `run_exploration_round()` after the round counter advances, so budget truth and finalization truth stay in one place.
- Used the shared guidance renderer instead of inventing a Phase 28-only presentation surface, which keeps operator output consistent across stages.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 can now verify the full lifecycle end-to-end using `finalization_submission`, `finalize_early()`, and rendered guidance from real services.
- The final verification pass can treat finalization as a first-class exploration outcome instead of a side effect hidden in persistence only.

## Self-Check: PASSED

- Verified `uv run pytest tests/test_phase28_activation.py tests/test_phase27_integration.py -x -q` exits 0.
- Verified commits `1ca68e3`, `81a5b61`, and `d38821a` exist in git history.
- Verified summary file exists at `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-03-SUMMARY.md`.

---
*Phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking*
*Completed: 2026-03-24*
