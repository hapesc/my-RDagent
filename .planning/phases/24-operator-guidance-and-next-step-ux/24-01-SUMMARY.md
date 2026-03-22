---
phase: 24-operator-guidance-and-next-step-ux
plan: 01
subsystem: orchestration
tags: [operator-guidance, routing, preflight, next-step, testing]
requires:
  - phase: 22-intent-routing-and-continuation-control
    provides: concise route fields and paused-run continuation semantics
  - phase: 23-preflight-and-state-truth-hardening
    provides: canonical blocked-vs-executable truth and repair-action guidance
provides:
  - shared Phase 24 operator-guidance contract
  - canonical stage-to-next-skill mapping and text renderer for next-step UX
  - human-first route guidance with minimum start detail and selective expansion
affects: [rd-agent, stage-guidance, tool-catalog, docs]
tech-stack:
  added: []
  patterns: [shared operator guidance source, formatting-only guidance helper, selective detail expansion]
key-files:
  created:
    - tests/test_phase24_operator_guidance.py
    - v3/contracts/operator_guidance.py
    - v3/orchestration/operator_guidance.py
  modified:
    - v3/entry/rd_agent.py
key-decisions:
  - "One shared runtime source now owns overlapping guidance fields and the stage-to-next-skill mapping; `rd_agent` projects it instead of hand-assembling duplicates."
  - "The guidance helper remains formatting-only and does not read `StateStorePort` or any snapshot-loading helpers."
  - "New-run answers emit a minimum start skeleton, while healthy paused runs stay terse and expose only a detail hint."
patterns-established:
  - "Pattern 1: shared `OperatorGuidance` contract plus `project_operator_guidance()` projection into existing route payloads"
  - "Pattern 2: shared `render_operator_guidance_text()` renderer keeps the three-part operator answer shape stable across surfaces"
requirements-completed:
  - GUIDE-05
duration: 4 min
completed: 2026-03-22
---

# Phase 24 Plan 01: Operator Guidance Routing Summary

**Shared operator-guidance contracts and route formatting now turn top-level “what next?” answers into human-first, minimally executable guidance without weakening Phase 22/23 truth.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-22T14:40:28Z
- **Completed:** 2026-03-22T14:44:40Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a typed `OperatorGuidance` contract for shared next-step payloads.
- Added a formatting-only guidance helper with one canonical stage-to-next-skill mapping, one shared renderer, and one projection helper.
- Updated `route_user_intent()` to use the shared guidance source while preserving existing Phase 22 route fields.
- Added focused Phase 24 regressions that lock human-first summaries, repair-first ordering, minimum start detail, and the shared helper surface.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add focused Phase 24 route-guidance regressions** - `86ac39e` (`test`)
2. **Task 2: Implement the shared operator-guidance contract and wire it into `rd-agent` routing** - `ebb82ef` (`feat`)

## Files Created/Modified

- `tests/test_phase24_operator_guidance.py` - focused Phase 24 route-surface and shared-helper regression suite
- `v3/contracts/operator_guidance.py` - typed shared operator-guidance contract for next-step payloads
- `v3/orchestration/operator_guidance.py` - canonical stage mapping, minimum-detail generation, projection helper, and shared text renderer
- `v3/entry/rd_agent.py` - route-level integration that now projects shared operator guidance instead of hand-assembling duplicate fields

## Decisions Made

- Reused the existing Phase 22 route field family and projected new detail fields into it, instead of replacing the public payload shape.
- Moved the canonical stage-to-next-skill mapping out of `rd_agent.py` and into the shared guidance helper.
- Kept the renderer tolerant of both full guidance models and minimal three-field dicts so later stage surfaces can reuse it without over-coupling.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first `gsd-executor` subagent for `24-01` never returned a completion signal and produced no on-disk progress markers. Execution fell back to inline plan execution per the `execute-phase` bounded-wait rule. No code or artifact divergence resulted from the fallback.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`24-02` can now reuse the shared operator-guidance contract, canonical stage mapping, and shared renderer across stage outcomes, tool catalog follow-up semantics, and docs. No runtime blockers remain for the next plan.

---
*Phase: 24-operator-guidance-and-next-step-ux*
*Completed: 2026-03-22*
