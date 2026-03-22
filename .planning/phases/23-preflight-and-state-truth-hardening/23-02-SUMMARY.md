---
phase: 23-preflight-and-state-truth-hardening
plan: 02
subsystem: orchestration
tags: [rd-agent, preflight, routing, stage-entry, docs]
requires:
  - phase: 23-preflight-and-state-truth-hardening
    provides: canonical preflight contracts and service from 23-01
provides:
  - preflight-aware paused-run routing payloads
  - stage entrypoints that block before publishing state on preflight failure
  - seeded stage summaries and public docs aligned with blocked-vs-recommended truth
affects: [rd-agent, rd-propose, rd-code, rd-execute, rd-evaluate, README, skill-contracts]
tech-stack:
  added: []
  patterns: [blocked-vs-recommended routing contract, preflight gate before stage publish]
key-files:
  created: []
  modified:
    - v3/entry/rd_agent.py
    - v3/entry/rd_propose.py
    - v3/entry/rd_code.py
    - v3/entry/rd_execute.py
    - v3/entry/rd_evaluate.py
    - v3/orchestration/skill_loop_service.py
    - tests/test_phase22_intent_routing.py
    - tests/test_phase23_stage_preflight_integration.py
    - README.md
    - skills/rd-agent/SKILL.md
    - .importlinter
key-decisions:
  - "Paused-run routing keeps `recommended_next_skill` visible even when the current action is blocked, and pairs it with blocker and repair-action fields."
  - "Explicit stage-skill entrypoints assess canonical preflight with `require_branch_current_stage=false` so direct stage execution remains valid without lying about routing-time state."
  - "Seeded next-stage summaries and public docs must say 'prepared and requires preflight' instead of claiming ready-by-default execution."
patterns-established:
  - "Pattern 1: `preflight_blocked` is a first-class stage-entry outcome distinct from verification `blocked`."
  - "Pattern 2: Routing and docs separate the ideal next skill from the current executable action."
requirements-completed:
  - PREFLIGHT-01
  - PREFLIGHT-02
  - STATE-01
  - STATE-02
duration: 8 min
completed: 2026-03-22
---

# Phase 23 Plan 02: Preflight-Aware Routing and Stage Entry Summary

**Paused-run routing, stage entry, and seeded stage summaries now tell the truth about blockers before execution mutates state, while still preserving the ideal next skill after repair.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-22T12:29:53Z
- **Completed:** 2026-03-22T12:38:33Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Extended `rd-agent` intent routing so paused-run responses can expose `current_action_status`, blocker details, and `repair_action` alongside `recommended_next_skill`.
- Wired `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate` to return `preflight_blocked` before any publish call when canonical preflight fails.
- Replaced seeded READY-stage summaries with preflight-aware wording and aligned README / `skills/rd-agent` docs with the new blocked-vs-recommended contract.
- Added focused integration regressions plus cross-phase regression coverage that prove the new truth layer does not break existing Phase 14/16/22 contracts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add integration regressions for blocked routing and blocked stage entry** - `19cb2c5` (`test`)
2. **Task 2: Wire canonical preflight into routing, stage entry, and public wording** - `eee2d01` (`feat`)

## Files Created/Modified

- `tests/test_phase22_intent_routing.py` - locks executable paused-run payload fields
- `tests/test_phase23_stage_preflight_integration.py` - proves blocked routing, blocked stage entry, and preflight-aware seeded summaries
- `v3/entry/rd_agent.py` - adds blocked-vs-executable paused-run payload fields
- `v3/entry/rd_propose.py` - returns `preflight_blocked` before publish on framing preflight failure
- `v3/entry/rd_code.py` - returns `preflight_blocked` before publish on build preflight failure
- `v3/entry/rd_execute.py` - distinguishes `preflight_blocked` from verify-stage `blocked`
- `v3/entry/rd_evaluate.py` - returns `preflight_blocked` before publish on synthesize preflight failure
- `v3/orchestration/skill_loop_service.py` - downgrades seeded ready wording to preflight-aware wording
- `README.md` - documents blocked recommendations plus repair action
- `skills/rd-agent/SKILL.md` - documents blocked-vs-recommended routing contract
- `.importlinter` - restores expected forbidden-module coverage so regression tests pass

## Decisions Made

- Routing keeps `recommended_next_skill` visible even when preflight blocks so the operator sees the intended path after repair.
- Stage entrypoints run recovery assessment first, then canonical preflight, so persisted recovery truth can still exist before the preflight gate decides whether stage mutation may proceed.
- Explicit stage-skill entrypoints are allowed to assess a requested stage even when the branch’s current routing anchor is elsewhere, but routing-time recommendation checks remain stricter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Relaxed branch-current-stage enforcement for explicit stage skills**
- **Found during:** Task 2 full regression gate
- **Issue:** The initial preflight integration blocked `rd-code`, `rd-execute`, and `rd-evaluate` in Phase 14 regression tests because those tests intentionally invoke stage skills directly even when the branch's routing anchor is still earlier in the loop.
- **Fix:** Added `require_branch_current_stage` to canonical preflight and set it to `false` for explicit stage-skill entrypoints while keeping the stricter routing-time behavior intact.
- **Files modified:** `v3/orchestration/preflight_service.py`, `v3/entry/rd_propose.py`, `v3/entry/rd_code.py`, `v3/entry/rd_execute.py`, `v3/entry/rd_evaluate.py`
- **Verification:** Full regression gate passed after the change.
- **Committed in:** `eee2d01`

**2. [Rule 3 - Blocking] Restored expected forbidden-module coverage in `.importlinter`**
- **Found during:** Task 2 full regression gate
- **Issue:** `tests/test_phase14_stage_skills.py` still expected legacy forbidden-module names that were missing from `.importlinter`, so the phase gate could not pass even though runtime behavior was correct.
- **Fix:** Re-added the expected legacy module names to the relevant forbidden-module sections in `.importlinter`.
- **Files modified:** `.importlinter`
- **Verification:** `tests/test_phase14_stage_skills.py` passed inside the full regression gate.
- **Committed in:** `eee2d01`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both deviations were gate-clearing fixes, not scope creep. They preserved existing public stage-skill contracts and restored the expected regression baseline.

## Issues Encountered

None after the blocking regressions above were fixed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 23 now has both the core preflight service and the public routing/stage-entry integration layer. The phase is ready for verifier review and phase completion tracking.

---
*Phase: 23-preflight-and-state-truth-hardening*
*Completed: 2026-03-22*
