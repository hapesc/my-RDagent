---
phase: 23-preflight-and-state-truth-hardening
plan: 01
subsystem: infra
tags: [preflight, runtime, recovery, state-store, testing]
requires:
  - phase: 22-intent-routing-and-continuation-control
    provides: intent-first routing with recommended_next_skill and paused-run continuation semantics
provides:
  - canonical Phase 23 preflight contracts
  - deterministic preflight service over runtime, dependency, artifact, state, and recovery truth
  - focused unit regressions for blocker-category preflight behavior
affects: [rd-agent, rd-code, rd-execute, resume-planner, phase-23-integration]
tech-stack:
  added: []
  patterns: [canonical preflight service, injected environment providers for deterministic testing]
key-files:
  created:
    - tests/test_phase23_preflight_service.py
    - v3/contracts/preflight.py
    - v3/orchestration/preflight_service.py
  modified:
    - v3/orchestration/resume_planner.py
key-decisions:
  - "Preflight stays read-only and does not persist a second truth source; it only reads repo declarations and StateStorePort snapshots."
  - "Runtime truth uses `requires-python` plus mandatory `uv`; dependency truth uses project-declared modules with verify-stage extras."
  - "Completed-stage reuse is blocked when recovery truth is missing, but replay/rebuild decisions remain the responsibility of existing recovery logic."
patterns-established:
  - "Pattern 1: Category-grouped blocker results with one ranked primary blocker and one repair action"
  - "Pattern 2: Deterministic preflight tests use injected command/module/python providers instead of machine-dependent environment state"
requirements-completed:
  - PREFLIGHT-01
  - PREFLIGHT-02
  - STATE-02
duration: 4 min
completed: 2026-03-22
---

# Phase 23 Plan 01: Canonical Preflight Truth Summary

**Canonical preflight contracts and service now decide executable-vs-blocked stage truth from repo-declared runtime requirements and persisted V3 snapshots.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-22T12:06:07Z
- **Completed:** 2026-03-22T12:10:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a typed preflight contract with grouped blocker categories, ranked primary blocker output, and repair actions.
- Implemented a deterministic `PreflightService` that checks runtime, dependency, artifact, state, and recovery truth without creating a second persistence layer.
- Added focused unit regressions that lock all five blocker categories plus the executable happy path.
- Removed the false-positive `ready to run` wording from `resume_planner` so downstream surfaces stop implying readiness before canonical preflight exists.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add focused unit regressions for canonical preflight truth** - `7d7c97e` (`test`)
2. **Task 2: Implement the canonical preflight contract and service** - `a6a1c66` (`feat`)

## Files Created/Modified

- `tests/test_phase23_preflight_service.py` - deterministic blocker-category regression suite for Phase 23 preflight truth
- `v3/contracts/preflight.py` - typed preflight readiness and blocker contract models
- `v3/orchestration/preflight_service.py` - canonical read-only preflight evaluator over runtime and persisted state
- `v3/orchestration/resume_planner.py` - removes false `ready to run` wording pending Phase 23 integration

## Decisions Made

- Preflight uses repo-owned declarations from `pyproject.toml` and `scripts/setup_env.sh` instead of hidden environment heuristics.
- Verify-stage dependency truth explicitly checks `pytest` and `import_linter`, while all stages always require `pydantic`.
- Missing recovery truth for a completed stage is treated as a first-class `recovery` blocker instead of soft success.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing STATE.md plan fields for GSD continuity commands**
- **Found during:** Plan metadata/tracking updates after Task 2
- **Issue:** `state advance-plan` could not parse `Current Plan` or `Total Plans in Phase` from the repo's older STATE.md shape
- **Fix:** Added the missing machine-readable STATE fields with the current Phase 23 values so GSD continuity commands could proceed
- **Files modified:** `.planning/STATE.md`
- **Verification:** `node ... state advance-plan` succeeded immediately after the field patch
- **Committed in:** metadata commit for this plan

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope creep in runtime code. The deviation only repaired execution tracking so the plan could complete with valid GSD metadata.

## Issues Encountered

`state record-metric` still reports `Performance Metrics section not found in STATE.md` because this repo's STATE body format remains partially out of sync with the current GSD template. This did not block `23-01`, but the mismatch remains a continuity/tooling debt to clean up later.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`23-02` can now wire the canonical preflight result into routing, stage entry, seeded stage summaries, and public docs. No blockers remain for the integration plan.

---
*Phase: 23-preflight-and-state-truth-hardening*
*Completed: 2026-03-22*
