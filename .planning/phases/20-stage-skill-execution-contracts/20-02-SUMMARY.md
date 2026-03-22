---
phase: 20-stage-skill-execution-contracts
plan: 02
subsystem: documentation
tags: [skills, continuation, stage-contracts, pytest]
requires:
  - phase: 19-tool-catalog-operator-guidance
    provides: explicit routing and follow-up semantics for the standalone public surface
provides:
  - shared continuation contract sections for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`
  - regression coverage for shared continuation fields, stage-specific extras, and agent-led recovery wording
affects: [phase-20, skill-guidance, operator-continuity]
tech-stack:
  added: []
  patterns: [file-reading skill contract regressions, shared continuation skeleton across stage skills]
key-files:
  created: [tests/test_phase20_stage_skill_contracts.py, .planning/phases/20-stage-skill-execution-contracts/20-02-SUMMARY.md]
  modified: [skills/rd-propose/SKILL.md, skills/rd-code/SKILL.md, skills/rd-execute/SKILL.md, skills/rd-evaluate/SKILL.md]
key-decisions:
  - "The four stage skills now share the same continuation section layout and the same core field vocabulary."
  - "Missing continuation data is recovered agent-first by inspecting run or branch state before asking the operator."
  - "`rd-tool-catalog` remains available only as an agent-side escalation path, not the default operator recovery path."
patterns-established:
  - "Stage skill packages expose continuation contracts with explicit next-step outcomes."
  - "Phase-specific doc regressions read SKILL.md files directly instead of inferring contract text from runtime code."
requirements-completed: [SKILL-03]
duration: 5min
completed: 2026-03-22
---

# Phase 20 Plan 02: Stage continuation contracts summary

**Shared paused-run continuation contracts for all four stage skills, including exact payload fields, blocked/recommendation deltas, and agent-led missing-field recovery**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-22T05:28:00Z
- **Completed:** 2026-03-22T05:33:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added a focused Phase 20 regression file that reads the four stage `SKILL.md` packages directly and locks the shared continuation skeleton.
- Hardened `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate` with `Continue contract`, `Required fields`, `If information is missing`, and `Outcome guide` sections.
- Documented the exact stage-specific extras: `blocking_reasons` for blocked verify continuations and `recommendation` with `continue` or `stop` for synthesize continuations.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create a focused Phase 20 regression file for the four continuation skill packages** - `12baa77` (test)
2. **Task 2: Harden the four stage-skill packages with exact continuation contracts and next-step guidance** - `3db2251` (feat)

## Files Created/Modified

- `tests/test_phase20_stage_skill_contracts.py` - Phase 20 doc-surface regression coverage for shared continuation fields and next-step guidance.
- `skills/rd-propose/SKILL.md` - Continuation contract for paused framing-stage execution with `rd-code` handoff guidance.
- `skills/rd-code/SKILL.md` - Continuation contract for paused build-stage execution with `rd-execute` handoff guidance.
- `skills/rd-execute/SKILL.md` - Continuation contract for paused verify-stage execution, including blocked-path `blocking_reasons`.
- `skills/rd-evaluate/SKILL.md` - Continuation contract for paused synthesize-stage execution, including `recommendation` values `continue` and `stop`.

## Decisions Made

- Standardized the four stage skills on one section layout so the operator sees one continuation pattern instead of four unrelated descriptions.
- Wrote the missing-field flow in agent-first terms so the agent inspects run or branch state and only asks for unresolved values.
- Kept runtime Python untouched; this plan only hardened public skill-package guidance and its regression lock.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase20_stage_skill_contracts.py -q` reported one unrelated pre-existing failure: `tests/test_phase14_stage_skills.py::test_importlinter_extends_forbidden_imports_to_stage_write_tools` expects `.importlinter` to contain `app.control_plane`, but the current `.importlinter` only lists legacy forbidden modules. This plan did not own `.importlinter` or Phase 14 test infrastructure, so the failure was left as out-of-scope and did not block the Phase 20 contract changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The stage skill surface now states the exact continuation identifiers and payload fields needed to continue a paused run.
- Phase 20 can now rely on doc-surface regressions to catch drift in stage-skill continuation guidance.

## Self-Check

PASSED

- FOUND: `.planning/phases/20-stage-skill-execution-contracts/20-02-SUMMARY.md`
- FOUND: `12baa77`
- FOUND: `3db2251`

---
*Phase: 20-stage-skill-execution-contracts*
*Completed: 2026-03-22*
