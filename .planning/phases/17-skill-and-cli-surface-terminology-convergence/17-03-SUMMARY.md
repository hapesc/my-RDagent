---
phase: 17-skill-and-cli-surface-terminology-convergence
plan: 03
subsystem: docs
tags: [readme, tests, surface-terminology, standalone-v3]
requires:
  - phase: 17-01
    provides: repo-local public skill packages and routing boundaries
  - phase: 17-02
    provides: catalog metadata and the initial Phase 17 regression scaffold
provides:
  - README aligned to the actual skill-first and CLI-downshift surface
  - Final doc-surface regression coverage for README and planning artifacts
  - Removal of the last stale MCP-era wording that blocked the Phase 17 doc gate
affects: [phase-18-packaging, public-docs, onboarding]
tech-stack:
  added: []
  patterns: [README-first public surface narrative, string-based doc-surface regression]
key-files:
  created: []
  modified: [README.md, tests/test_phase17_surface_convergence.py, .planning/REQUIREMENTS.md, tests/test_phase13_v3_tools.py]
key-decisions:
  - "Describe the public surface in the order rd-agent -> stage skills -> rd-tool-catalog so the README matches how the product should be used."
  - "Keep the regression string-based and repo-local so terminology drift fails fast without indirect parsing."
patterns-established:
  - "README treats high-level skills as the default path and rd-tool-catalog as the selective downshift layer."
  - "Phase-level surface tests check README and planning docs directly for product-language drift."
requirements-completed: [SURFACE-01, SURFACE-02, SURFACE-03]
duration: 5min
completed: 2026-03-21
---

# Phase 17 Plan 03: README and doc-surface convergence summary

**The standalone V3 README now leads with rd-agent, stages the skill surface explicitly, and locks the final skills-plus-CLI narrative with a direct doc-surface regression**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T18:00:55+08:00
- **Completed:** 2026-03-21T18:06:12+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Rewrote `README.md` around the actual public flow: `rd-agent` first, stage skills second, `rd-tool-catalog` and `rdagent-v3-tool` as the selective downshift layer.
- Extended `tests/test_phase17_surface_convergence.py` so it now locks the final README strings for `rd-agent`, `rd-tool-catalog`, `rdagent-v3-tool`, and `$skill-architect`.
- Removed the last stale requirement phrase that still triggered the Phase 17 doc-surface grep gate.
- Aligned the stale Phase 13 importlinter regression with the standalone forbidden-module set so the full regression gate passes again.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite README around the actual skills-first and CLI-downshift surface** - `f1ef5a4` (docs)
2. **Task 2: Extend the Phase 17 doc-surface regression with the final README assertions** - `d999a10` (test)

## Files Created/Modified
- `README.md` - public product narrative for skills first and CLI tools second
- `tests/test_phase17_surface_convergence.py` - final string-based regression for README and planning docs
- `.planning/REQUIREMENTS.md` - small wording cleanup needed for the final doc gate
- `tests/test_phase13_v3_tools.py` - prior-phase regression aligned with the standalone importlinter contract

## Decisions Made

- Ordered the README around the actual operator path so the public narrative matches the shipped skill packages and catalog metadata.
- Kept the doc-surface regression concrete and string-based rather than inferring product language from secondary structures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale requirement wording that failed the final doc gate**
- **Found during:** Task 1 (Rewrite README around the actual skills-first and CLI-downshift surface)
- **Issue:** `.planning/REQUIREMENTS.md` still contained the exact phrase `registry language`, which caused the plan's final grep verification to fail even after the README rewrite was correct.
- **Fix:** Reworded `SURFACE-01` to say `MCP-framed catalog wording` instead of `MCP-framed registry language`.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** `rg -n "MCP server|registry language" README.md .planning/PROJECT.md .planning/ROADMAP.md .planning/REQUIREMENTS.md -S || true` returned no matches.
- **Committed in:** `f1ef5a4` (part of Task 1 commit)

---

**2. [Rule 3 - Blocking] Updated a stale prior-phase regression to match the standalone import boundary contract**
- **Found during:** Regression gate after all Phase 17 plans completed
- **Issue:** `tests/test_phase13_v3_tools.py` still expected upstream-shell fallback names in `.importlinter`, so the full standalone regression suite failed even though the current import boundary contract was correct.
- **Fix:** Updated the test to assert the standalone forbidden-module set and to confirm the removed upstream-shell names are absent.
- **Files modified:** `tests/test_phase13_v3_tools.py`
- **Verification:** `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py tests/test_phase17_surface_convergence.py -q` exited 0.
- **Committed in:** `08f9932` (post-plan regression gate fix)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required to satisfy the final phase verification gates. No scope creep beyond standalone surface-language and regression-convergence work.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 17 now has concrete skill packages, catalog metadata, README language, and regression coverage aligned to the same public surface.
- The next step is phase-level verification and then Phase 18 planning and execution.

## Self-Check

PASSED.

---
*Phase: 17-skill-and-cli-surface-terminology-convergence*
*Completed: 2026-03-21*
