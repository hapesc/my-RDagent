---
phase: 18-standalone-packaging-and-planning-autonomy
plan: 02
subsystem: docs
tags: [readme, planning, continuity, verification, standalone-v3]
requires:
  - phase: 18-standalone-packaging-and-planning-autonomy
    provides: repo-local skill installer commands and phase 18 installer regression coverage
provides:
  - Public README setup, CLI usage, and quick/full verification guidance
  - Canonical standalone continuity entrypoint in `.planning/STATE.md`
  - Historical handoff demotion and doc-surface regression coverage for the public/internal split
affects: [public-docs, onboarding, phase-verification, future-standalone-planning]
tech-stack:
  added: []
  patterns: [public-readme only, state-as-continuity-home, string-based doc regressions]
key-files:
  created: [tests/test_phase18_planning_continuity.py]
  modified: [README.md, .planning/STATE.md, .planning/V3-EXTRACTION-HANDOFF.md, tests/test_phase17_surface_convergence.py]
key-decisions:
  - "Keep README strictly public-user-facing and move internal continuity into `.planning/STATE.md`."
  - "Enforce the public/internal boundary with direct file-reading regressions rather than looser narrative conventions."
patterns-established:
  - "README documents repo-environment setup, agent skill exposure, and validation commands, but never internal planning recovery."
  - "Historical artifacts can remain in repo only if they point back to `.planning/STATE.md` and avoid acting like active startup guidance."
requirements-completed: [STANDALONE-01, STANDALONE-02]
duration: 7min
completed: 2026-03-21
---

# Phase 18 Plan 02: Public/internal continuity split summary

**Phase 18 now separates public repo setup from internal planning continuity, with README-based setup guidance, `.planning/STATE.md` as the canonical resume point, and doc regressions that keep stale upstream residue out of active docs**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T22:27:57+08:00
- **Completed:** 2026-03-21T22:34:19+08:00
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Rewrote `README.md` around repo-environment setup, repo-local skill exposure, `uv run rdagent-v3-tool ...` usage, and quick/full verification commands.
- Promoted `.planning/STATE.md` to the canonical continuity entrypoint for standalone work and demoted `.planning/V3-EXTRACTION-HANDOFF.md` to historical context only.
- Added direct doc regressions that lock the README/STATE/HANDOFF boundary and verified the full Phase 18 standalone gate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite README around public repo setup, agent skill exposure, repo-env CLI usage, and quick/full verification** - `2c612d2` (feat)
2. **Task 2: Promote STATE as the continuity truth and demote stale upstream handoff guidance** - `1285289` (feat)
3. **Task 3: Lock the public/internal boundary with Phase 18 doc regressions and the final phase gate** - `6af52ae` (test)

## Files Created/Modified

- `README.md` - public-facing standalone setup, skill install, CLI usage, and verification guide
- `.planning/STATE.md` - canonical continuity entrypoint for standalone planning work
- `.planning/V3-EXTRACTION-HANDOFF.md` - historical extraction record that now points back to `.planning/STATE.md`
- `tests/test_phase17_surface_convergence.py` - updated README boundary assertions for Phase 18
- `tests/test_phase18_planning_continuity.py` - direct regression coverage for README/STATE/HANDOFF continuity responsibilities

## Decisions Made

- Kept the public documentation centered on user-visible setup and validation so internal GSD recovery does not leak into the README.
- Used direct string assertions over README, STATE, and HANDOFF because the boundary is contractual text, not derived behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed the last stale upstream startup wording from the historical handoff**
- **Found during:** Task 3 (Lock the public/internal boundary with Phase 18 doc regressions and the final phase gate)
- **Issue:** `.planning/V3-EXTRACTION-HANDOFF.md` still contained the literal `docs/context/` substring in a warning sentence, which caused the new continuity regression to fail even though the file was already marked historical.
- **Fix:** Reworded the historical note to avoid the removed path literal while preserving the warning that those upstream startup steps are obsolete.
- **Files modified:** `.planning/V3-EXTRACTION-HANDOFF.md`
- **Verification:** `uv run python -m pytest tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py -q`, the full standalone pytest gate, and `uv run lint-imports` all passed after the wording fix.
- **Committed in:** `d6d3afd` (post-task fix)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was necessary to make the new continuity regression truthful and green. No scope expansion beyond the plan's doc-boundary goal.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 18 now has public setup instructions, internal continuity guidance, and regression coverage aligned to the same standalone boundary.
- Phase-level verification can now judge the phase goal directly against concrete README, STATE, HANDOFF, and regression evidence.

## Self-Check

PASSED.

---
*Phase: 18-standalone-packaging-and-planning-autonomy*
*Completed: 2026-03-21*
