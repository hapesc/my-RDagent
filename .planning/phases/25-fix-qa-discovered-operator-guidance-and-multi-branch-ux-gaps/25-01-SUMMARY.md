---
phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
plan: 01
subsystem: orchestration
tags: [operator-guidance, next-step, stage-skills, testing, tdd]
requires:
  - phase: 24-operator-guidance-and-next-step-ux
    provides: shared operator guidance surface and stage next-step guidance contracts
provides:
  - consistent outcome fields across all four stage entry surfaces
  - copy-pasteable continuation skeletons on every operator guidance path
  - removal of the obsolete detail_hint expansion pattern
affects: [stage-guidance, public-surface, phase25-02, phase25-03]
tech-stack:
  added: []
  patterns: [top-level outcome contract, always-present continuation detail, shared guidance renderer]
key-files:
  created:
    - .planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-01-SUMMARY.md
    - tests/test_phase25_outcome_consistency.py
    - tests/test_phase25_guidance_completeness.py
  modified:
    - v3/contracts/operator_guidance.py
    - v3/orchestration/operator_guidance.py
    - v3/entry/rd_propose.py
    - v3/entry/rd_code.py
    - v3/entry/rd_execute.py
    - v3/entry/rd_evaluate.py
    - tests/test_phase24_operator_guidance.py
key-decisions:
  - "Stage entry surfaces now treat `outcome` as mandatory public truth on every return path instead of only the preflight-blocked path."
  - "Operator guidance no longer exposes `detail_hint`; executable and blocked continuations now surface the exact continuation skeleton directly through `next_step_detail`."
  - "The shared builder owns the continuation skeleton shape so all four stage entries stay aligned without duplicating formatting logic."
patterns-established:
  - "Every stage entry response should expose both top-level `outcome` and nested `operator_guidance.next_step_detail`."
  - "Paused or blocked continuation UX should surface copy-pasteable commands directly instead of offering an optional expansion hint."
requirements-completed: [SC-3, SC-5]
duration: 6min
completed: 2026-03-23
---

# Phase 25 Plan 01: Outcome Consistency and Guidance Completeness Summary

**Stage entry responses now expose one consistent `outcome` contract and always include copy-pasteable continuation detail, with the old `detail_hint` branch removed from the shared guidance surface**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T03:48:38Z
- **Completed:** 2026-03-23T03:54:18Z
- **Tasks:** 1
- **Files modified:** 10

## Accomplishments

- Added focused Phase 25 regression suites that lock `outcome` coverage and `next_step_detail` completeness across all four stage entry surfaces.
- Removed `detail_hint` from the shared `OperatorGuidance` contract and from the renderer, so guidance now carries executable continuation detail directly.
- Updated `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate` so every operator-facing path returns a stable `outcome` plus the minimum continuation skeleton.
- Updated the existing Phase 24 paused-route regression to assert the new continuation-detail contract instead of the old hint-only behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove detail_hint, add outcome + next_step_detail to all guidance paths** - `8ec470e` (test), `0d927f9` (feat)

## Files Created/Modified

- `tests/test_phase25_outcome_consistency.py` - Phase 25 regression coverage for `outcome` across preflight, reuse, review, replay, blocked, and completed paths.
- `tests/test_phase25_guidance_completeness.py` - Phase 25 regression coverage for `next_step_detail`, `detail_hint` removal, paused guidance, and shared renderer behavior.
- `v3/contracts/operator_guidance.py` - Shared operator-guidance contract with `detail_hint` removed.
- `v3/orchestration/operator_guidance.py` - Shared builder and renderer now emit continuation detail directly on every path.
- `v3/entry/rd_propose.py` - Framing entry surface now returns `outcome` and continuation detail on every response path.
- `v3/entry/rd_code.py` - Build entry surface now returns `outcome` and continuation detail on every response path.
- `v3/entry/rd_execute.py` - Verify entry surface now keeps its existing outcomes while adding continuation detail everywhere.
- `v3/entry/rd_evaluate.py` - Synthesize entry surface now returns `outcome` and continuation detail on every response path.
- `tests/test_phase24_operator_guidance.py` - Existing paused-route regression updated to assert direct continuation detail instead of `detail_hint`.
- `.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-01-SUMMARY.md` - Execution summary, decisions, and self-check evidence for Plan 25-01.

## Decisions Made

- Kept the continuation skeleton centralized in `v3.orchestration.operator_guidance` so the four stage entry files only choose when to render it, not how to format it.
- Standardized on the existing outcome vocabulary (`completed`, `blocked`, `preflight_blocked`, `reused`, `replay`, `review`) instead of introducing plan-specific synonyms.
- Treated the old `detail_hint` expansion pattern as dead contract surface rather than preserving it as an optional compatibility field.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The initial `gsd-executor` subagent for `25-01` never produced a completion signal, summary file, commit, or worktree progress. Execution fell back to inline plan execution per the `execute-phase` bounded-wait rule.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `25-02` can rename `disposition` to `recovery_assessment` on top of a now-stable stage-guidance payload contract.
- `25-03` can assume every stage entry already exposes `outcome` and `next_step_detail`, so the remaining work is limited to multi-branch defaults and stage materialization.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-01-SUMMARY.md`.
- Verified task commits `8ec470e` and `0d927f9` exist in git history.

---
*Phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps*
*Completed: 2026-03-23*
