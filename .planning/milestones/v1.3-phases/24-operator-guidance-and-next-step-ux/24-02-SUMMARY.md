---
phase: 24-operator-guidance-and-next-step-ux
plan: 02
subsystem: orchestration
tags: [operator-guidance, stage-outcomes, tool-catalog, docs, testing]
requires:
  - phase: 24-operator-guidance-and-next-step-ux
    provides: shared operator guidance contract, canonical stage mapping, and route-level next-step detail behavior
provides:
  - shared operator guidance across stage outcomes and resume messages
  - direct tool follow-up semantics aligned with the Phase 24 next-step vocabulary
  - public docs aligned with selective next-step detail expansion
affects: [rd-propose, rd-code, rd-execute, rd-evaluate, rd-tool-catalog, README, skill-contracts]
tech-stack:
  added: []
  patterns: [shared guidance renderer across route and stage outcomes, direct-tool follow-up aligned with stage-skill vocabulary]
key-files:
  created:
    - tests/test_phase24_stage_next_step_guidance.py
  modified:
    - v3/orchestration/resume_planner.py
    - v3/entry/rd_propose.py
    - v3/entry/rd_code.py
    - v3/entry/rd_execute.py
    - v3/entry/rd_evaluate.py
    - v3/entry/tool_catalog.py
    - README.md
    - skills/rd-agent/SKILL.md
    - tests/test_phase19_tool_guidance.py
    - tests/test_v3_tool_cli.py
key-decisions:
  - "Stage entrypoints now emit nested `operator_guidance` payloads and render text through the shared Phase 24 renderer instead of hand-assembling strings."
  - "Blocked verification stays on `rd-execute` instead of pretending it should hand off to `rd-evaluate`."
  - "Direct tool-catalog follow-up semantics remain in the existing `follow_up` field family but now use the same stage-skill vocabulary as the high-level surfaces."
patterns-established:
  - "Pattern 1: route, resume, stage, and tool surfaces share the same current-state / reason / next-action operator phrasing"
  - "Pattern 2: healthy paths can stay terse while docs explicitly describe one-line minimum detail only for blocked or fresh-start replies"
requirements-completed:
  - GUIDE-05
duration: 12 min
completed: 2026-03-22
---

# Phase 24 Plan 02: Cross-Surface Next-Step Alignment Summary

**Stage outcomes, tool follow-up semantics, and public docs now all describe the next step with one shared Phase 24 operator-guidance vocabulary.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-22T14:52:17Z
- **Completed:** 2026-03-22T15:04:41Z
- **Tasks:** 4
- **Files modified:** 11

## Accomplishments

- Added a full Phase 24 stage-guidance matrix test suite covering propose, code, execute, evaluate, blocked verification, and synthesize stop/continue outcomes.
- Routed `resume_planner` plus the four stage entrypoints through the shared operator-guidance renderer and nested payload shape.
- Aligned direct tool-catalog `follow_up` semantics with the same stage-skill vocabulary used by the high-level route and stage surfaces.
- Updated README and `skills/rd-agent/SKILL.md` so selective next-step detail expansion is documented exactly where operators look for it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add focused integration regressions for the full stage outcome guidance matrix** - `0eefd82` (`test`)
2. **Task 2: Reuse shared operator guidance across resume logic and stage runtime outcomes** - `95dbab4` (`feat`)
3. **Task 3: Align direct tool-catalog follow-up semantics with the shared next-step vocabulary** - `39110dd` (`feat`)
4. **Task 4: Align README and `rd-agent` public contract with the new selective-detail behavior** - `1b928bb` (`docs`)

## Files Created/Modified

- `tests/test_phase24_stage_next_step_guidance.py` - focused integration coverage for the full stage outcome guidance matrix
- `v3/orchestration/resume_planner.py` - shared resume messages now use the three-part operator guidance shape
- `v3/entry/rd_propose.py` - framing-stage outcomes expose nested `operator_guidance`
- `v3/entry/rd_code.py` - build-stage outcomes expose nested `operator_guidance`
- `v3/entry/rd_execute.py` - verify-stage outcomes distinguish blocked verification from the normal `rd-evaluate` handoff while exposing shared guidance
- `v3/entry/rd_evaluate.py` - synthesize continue/stop outcomes expose shared guidance and explicit no-next-skill stop behavior
- `v3/entry/tool_catalog.py` - direct tool `follow_up` semantics now use the shared stage-skill vocabulary
- `tests/test_phase19_tool_guidance.py` - locks shared-skill wording in tool follow-up actions
- `tests/test_v3_tool_cli.py` - locks `follow_up` fields on `describe`
- `README.md` - documents one-line minimum command or skeleton expansion for blocked and fresh-start replies
- `skills/rd-agent/SKILL.md` - documents `next_step_detail` and `detail_hint`

## Decisions Made

- Kept the existing tool-catalog `follow_up` field family instead of inventing a second CLI follow-up schema.
- Made blocked verification keep `rd-execute` as the active next skill rather than falsely handing off to `rd-evaluate`.
- Preserved Phase 20/21 wording guarantees while adding selective-detail behavior as additive public guidance.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv run lint-imports` still fails because `.importlinter` references `app.runtime` as an invalid forbidden external submodule. This appears to be a pre-existing configuration debt rather than a Phase 24 regression; all Phase 14/19/20/21/22/23/24 pytest gates passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 24 now has both plan summaries on disk and is ready for phase-level verification. The only remaining non-code concern is the pre-existing `.importlinter` configuration debt noted above.

---
*Phase: 24-operator-guidance-and-next-step-ux*
*Completed: 2026-03-22*
