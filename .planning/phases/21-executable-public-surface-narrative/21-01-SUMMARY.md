---
phase: 21-executable-public-surface-narrative
plan: 01
subsystem: docs
tags: [readme, pytest, public-surface, rd-agent, rd-tool-catalog]
requires:
  - phase: 20-stage-skill-execution-contracts
    provides: stage-skill continuation contracts and rd-agent start guidance
provides:
  - executable README mainline for start, inspect, and continue
  - Phase 21 regression coverage for public narrative ordering and wording
affects: [operator-guidance, public-surface, regression-suite]
tech-stack:
  added: []
  patterns: [readme-as-playbook, exact-string-doc-regressions]
key-files:
  created:
    - .planning/phases/21-executable-public-surface-narrative/21-01-SUMMARY.md
    - tests/test_phase21_public_surface_narrative.py
  modified:
    - README.md
key-decisions:
  - "Kept README at the decision layer and linked to skill packages for exact field contracts instead of duplicating schema inventories."
  - "Positioned rd-tool-catalog only under the Inspect downshift path so rd-agent remains the public first-class start surface."
patterns-established:
  - "Public README guidance should read as one executable Start -> Inspect -> Continue flow."
  - "README regressions should assert exact guidance phrases and anchor ordering rather than only section presence."
requirements-completed: [SURFACE-01, SURFACE-02]
duration: 2min
completed: 2026-03-22
---

# Phase 21 Plan 01: Executable Public Surface Narrative Summary

**README now opens with an rd-agent-first Start -> Inspect -> Continue playbook backed by focused Phase 21 narrative regressions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T06:57:17Z
- **Completed:** 2026-03-22T06:58:46Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added a dedicated README narrative regression file that locks the new Start -> Inspect -> Continue public flow.
- Rewrote the README mainline to make `rd-agent` the default start, `Inspect` a first-class agent-led step, and stage skills the continue path.
- Preserved the Phase 17/18 public anchors and kept `rd-tool-catalog` subordinate to the inspect/downshift story.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create a focused Phase 21 regression file for the README narrative** - `de704cf` (test)
2. **Task 2: Rewrite the README as an executable `Start -> Inspect -> Continue` playbook** - `d5c9082` (feat)

## Files Created/Modified

- `tests/test_phase21_public_surface_narrative.py` - Focused README narrative regression suite reading `README.md` directly.
- `README.md` - Public operator playbook centered on start, inspect, and continue decisions.
- `.planning/phases/21-executable-public-surface-narrative/21-01-SUMMARY.md` - Execution summary, decisions, and verification record for Plan 21-01.

## Decisions Made

- Kept README at the decision layer and linked to `skills/*/SKILL.md` for exact field-level contracts instead of duplicating field inventories.
- Made `Inspect` explicit and agent-led so the README tells the agent to determine the next valid surface for the user.
- Kept `rd-tool-catalog` as the selective inspect/downshift path rather than a coequal public start path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Existing unrelated worktree changes were present in `README.md`; the Phase 21 README rewrite was applied on top of the user-added `scripts/setup_env.sh` guidance without reverting it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 21 public README narrative and regression coverage are in place and verified against Phase 17, 18, 19, and 20 contract surfaces.
- The milestone is ready for final state and roadmap closure updates.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/21-executable-public-surface-narrative/21-01-SUMMARY.md`.
- Verified task commits `de704cf` and `d5c9082` exist in git history.
