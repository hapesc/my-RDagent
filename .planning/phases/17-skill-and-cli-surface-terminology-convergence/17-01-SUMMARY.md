---
phase: 17-skill-and-cli-surface-terminology-convergence
plan: 01
subsystem: skills
tags: [skills, orchestration, routing, standalone-v3]
requires:
  - phase: 17-02
    provides: phase surface regression scaffold and catalog routing metadata used by the public skill surface
provides:
  - Repo-local public skill packages for rd-agent, rd-propose, rd-code, rd-execute, rd-evaluate, and rd-tool-catalog
  - Explicit routing boundaries that keep high-level skills above direct CLI primitives
  - Stable entrypoint-to-skill mapping for the standalone V3 public surface
affects: [17-03-PLAN.md, README.md, phase-18-packaging]
tech-stack:
  added: []
  patterns: [repo-local skill packages, high-level skill to tool-catalog downshift routing]
key-files:
  created: [skills/rd-agent/SKILL.md, skills/rd-propose/SKILL.md, skills/rd-code/SKILL.md, skills/rd-execute/SKILL.md, skills/rd-evaluate/SKILL.md, skills/rd-tool-catalog/SKILL.md]
  modified: []
key-decisions:
  - "Keep the skill packages repo-local and minimal: one SKILL.md per public surface entrypoint."
  - "Use rd-tool-catalog as the only documented downshift path from high-level skills to direct CLI tools."
patterns-established:
  - "Every public skill declares when to use it, when to route to rd-tool-catalog, and when not to use it."
  - "Skill names mirror the public standalone entrypoint names instead of introducing alternate product vocabulary."
requirements-completed: [SURFACE-02, SURFACE-03]
duration: 1min
completed: 2026-03-21
---

# Phase 17 Plan 01: Public skill package summary

**Standalone V3 now ships six repo-local skill packages that mirror the public entrypoints and make rd-tool-catalog the explicit downshift path for direct CLI tools**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-21T17:54:52+08:00
- **Completed:** 2026-03-21T17:55:40+08:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added the top-level `rd-agent` and `rd-tool-catalog` skill packages for orchestration and CLI tool selection.
- Added the stage-specific `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate` skill packages.
- Standardized the public routing contract so every skill says when to use it, when to downshift to `rd-tool-catalog`, and when not to use it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the default orchestration and catalog skill packages** - `81ba30e` (feat)
2. **Task 2: Create the stage-specific skill packages for propose, code, execute, and evaluate** - `2d30ddd` (feat)

## Files Created/Modified
- `skills/rd-agent/SKILL.md` - default orchestration skill mapped to `v3.entry.rd_agent.rd_agent`
- `skills/rd-propose/SKILL.md` - framing-stage skill mapped to `v3.entry.rd_propose.rd_propose`
- `skills/rd-code/SKILL.md` - build-stage skill mapped to `v3.entry.rd_code.rd_code`
- `skills/rd-execute/SKILL.md` - verify-stage skill mapped to `v3.entry.rd_execute.rd_execute`
- `skills/rd-evaluate/SKILL.md` - synthesize-stage skill mapped to `v3.entry.rd_evaluate.rd_evaluate`
- `skills/rd-tool-catalog/SKILL.md` - decision-oriented catalog skill mapped to the CLI tool catalog surface

## Decisions Made

- Used a minimal skill-package structure with one `SKILL.md` per public surface entrypoint because Phase 17 only needs truthful public packaging, not a discovery runtime.
- Kept `rd-tool-catalog` as the only documented route from high-level skills to direct CLI tools so the downshift guidance stays explicit and consistent.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan `17-03` can now rewrite `README.md` against concrete repo-local skill packages instead of describing a hypothetical skill surface.
- The existing Phase 17 regression test can be extended to assert the final README narrative once the docs converge.

## Self-Check

PASSED.

---
*Phase: 17-skill-and-cli-surface-terminology-convergence*
*Completed: 2026-03-21*
