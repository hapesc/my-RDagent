---
phase: 20-stage-skill-execution-contracts
plan: 01
subsystem: testing
tags: [skills, rd-agent, pytest, operator-guidance, execution-policy]
requires:
  - phase: 19-tool-catalog-operator-guidance
    provides: skill-first routing guidance and tool-catalog escalation semantics
provides:
  - explicit rd-agent minimum start contract with literal required fields
  - plain-language default gated pause semantics for operators
  - regression coverage that locks the rd-agent skill contract surface
affects: [phase-21-public-surface, skill-contracts, operator-usability]
tech-stack:
  added: []
  patterns: [doc-surface regression tests, two-layer skill contracts]
key-files:
  created:
    - tests/test_phase20_rd_agent_skill_contract.py
  modified:
    - skills/rd-agent/SKILL.md
    - .planning/phases/20-stage-skill-execution-contracts/20-01-SUMMARY.md
key-decisions:
  - "Document the strict minimum rd-agent start contract separately from the recommended multi-branch path."
  - "Explain `gated + max_stage_iterations=1` in plain operator language first, then map it secondarily to `framing` and `awaiting_operator`."
patterns-established:
  - "Skill docs should name literal public field paths when the contract is part of the product surface."
  - "High-level skills should keep rd-tool-catalog as an agent-side escalation path, not the default operator workflow."
requirements-completed: [SKILL-01, SKILL-02]
duration: 8min
completed: 2026-03-22
---

# Phase 20 Plan 01: rd-agent Skill Contract Summary

**rd-agent minimum start fields, multi-branch recommendation, and gated one-step pause semantics locked into the skill surface**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-22T05:28:52Z
- **Completed:** 2026-03-22T05:36:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added a dedicated Phase 20 doc-surface regression file for the `rd-agent` skill package.
- Expanded `skills/rd-agent/SKILL.md` with explicit required and optional fields, a strict minimum start contract, and a separate recommended multi-branch contract.
- Translated the default `gated + max_stage_iterations=1` path into plain operator language and added agent-led missing-field recovery guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create a focused Phase 20 regression file for the `rd-agent` skill contract** - `44931b6` (test)
2. **Task 2: Harden `skills/rd-agent/SKILL.md` with an explicit start contract and default pause semantics** - `c66f3f2` (feat)

## Files Created/Modified

- `tests/test_phase20_rd_agent_skill_contract.py` - Reads `skills/rd-agent/SKILL.md` directly and locks the literal minimum fields, path separation, pause wording, and missing-field guidance.
- `skills/rd-agent/SKILL.md` - Documents the exact minimum start contract, recommended multi-branch path, default pause behavior, and agent-side recovery/escalation rules.

## Decisions Made

- Kept the `rd-agent` contract as two explicit layers so the richer multi-branch example does not hide the true minimum required fields.
- Explained the default stop behavior in operator language first and only then mapped it to public internal labels such as `framing` and `awaiting_operator`.
- Revised `rd-tool-catalog` routing language so common start/continue cases stay on the high-level skill path.

## Deviations from Plan

None - plan executed exactly as written for product behavior and verification scope.

## Issues Encountered

- Task 1 commit inherited one previously staged file, `tests/test_phase20_stage_skill_contracts.py`, from the concurrent 20-02 executor because it was already present in the shared git index. No 20-01 edits were made to that file, and later commits were restricted with path-limited `git commit --only` to avoid repeating the issue.
- A sandbox restriction blocked creation of `.git/index.lock` for the Task 2 commit. The commit succeeded after an escalated retry.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 20 now has an explicit `rd-agent` start and pause contract that Phase 21 can reuse in README-level public guidance.
- The remaining risk for this phase is coordination hygiene around the shared git index when multiple executors commit in parallel.

## Self-Check: PASSED

- Found `.planning/phases/20-stage-skill-execution-contracts/20-01-SUMMARY.md`
- Found commit `44931b6`
- Found commit `c66f3f2`

---
*Phase: 20-stage-skill-execution-contracts*
*Completed: 2026-03-22*
