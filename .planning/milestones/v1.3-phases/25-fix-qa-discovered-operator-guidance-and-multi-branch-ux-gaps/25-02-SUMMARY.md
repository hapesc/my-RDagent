---
phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
plan: 02
subsystem: orchestration
tags: [recovery, rename, stage-skills, selection, testing]
requires:
  - phase: 24-operator-guidance-and-next-step-ux
    provides: current operator-guidance payload shape used by stage entry surfaces
provides:
  - recovery contracts and resume decisions renamed to `recovery_assessment`
  - stage entry and tool payloads that expose `recovery_assessment` consistently
  - regression coverage for the renamed recovery field across tools and selection surfaces
affects: [selection, recovery-tools, stage-guidance, phase25-03]
tech-stack:
  added: []
  patterns: [self-documenting recovery field names, rename-through-payloads, contract-first regression updates]
key-files:
  created:
    - .planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-02-SUMMARY.md
    - tests/test_phase25_disposition_rename.py
  modified:
    - v3/contracts/recovery.py
    - v3/orchestration/resume_planner.py
    - v3/orchestration/recovery_service.py
    - v3/orchestration/scoring_service.py
    - v3/orchestration/selection_service.py
    - v3/orchestration/skill_loop_service.py
    - v3/tools/recovery_tools.py
    - v3/entry/rd_propose.py
    - v3/entry/rd_code.py
    - v3/entry/rd_execute.py
    - v3/entry/rd_evaluate.py
    - tests/test_phase13_v3_tools.py
    - tests/test_phase14_resume_and_reuse.py
    - tests/test_phase16_selection.py
    - tests/test_phase24_stage_next_step_guidance.py
key-decisions:
  - "Renamed the public recovery field to `recovery_assessment` everywhere instead of keeping `disposition` as a compatibility alias, so the contract stays self-documenting."
  - "Kept the existing `RecoveryDisposition` enum values (`reuse`, `replay`, `rebuild`, `review`) unchanged to avoid semantic churn while changing only the field label."
  - "Updated every surfaced payload and history record that serialized the field so the rename is truthful end-to-end, not just inside Pydantic models."
patterns-established:
  - "Recovery-field renames must propagate through models, services, tool payloads, entrypoint structured content, and regression suites in one pass."
  - "Blocking regression-suite contradictions discovered during execution should be documented explicitly as deviations when they are fixed to unblock the plan."
requirements-completed: [SC-6]
duration: 1min
completed: 2026-03-23
---

# Phase 25 Plan 02: Recovery Assessment Rename Summary

**Recovery models, resume decisions, tool payloads, and stage entry surfaces now expose `recovery_assessment` consistently instead of the ambiguous `disposition` field**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-23T04:05:52Z
- **Completed:** 2026-03-23T04:06:30Z
- **Tasks:** 1
- **Files modified:** 17

## Accomplishments

- Added a dedicated Phase 25 rename regression file that locks the model-level and planner-level `recovery_assessment` contract.
- Renamed `RecoveryAssessment` and `ResumeDecision` fields and propagated the new name through recovery, scoring, selection, skill-loop, tool, and stage-entry surfaces.
- Updated Phase 13, 14, 16, and 24 regression coverage so the serialized payloads and test helpers now assert `recovery_assessment` instead of `disposition`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename disposition to recovery_assessment across all surfaces** - `46cbb5e` (test), `cf44837` (feat)

## Files Created/Modified

- `tests/test_phase25_disposition_rename.py` - Focused Phase 25 regression coverage for the renamed recovery field in models and `plan_resume_decision`.
- `v3/contracts/recovery.py` - Recovery contract now uses `recovery_assessment`.
- `v3/orchestration/resume_planner.py` - Resume decision contract and planner now emit `recovery_assessment`.
- `v3/orchestration/recovery_service.py` - Recovery assessment construction and next-step helpers now use the renamed field.
- `v3/orchestration/scoring_service.py` - Branch selection scoring now reads `recovery_assessment`.
- `v3/orchestration/selection_service.py` - Eligibility filtering now reads `recovery_assessment`.
- `v3/orchestration/skill_loop_service.py` - Skill loop history now records `recovery_assessment` instead of `disposition`.
- `v3/tools/recovery_tools.py` - Recovery tool narration and payloads now surface the renamed field.
- `v3/entry/rd_propose.py` - Framing entry surface now branches on `decision.recovery_assessment`.
- `v3/entry/rd_code.py` - Build entry surface now branches on `decision.recovery_assessment`.
- `v3/entry/rd_execute.py` - Verify entry surface now branches on `decision.recovery_assessment`.
- `v3/entry/rd_evaluate.py` - Synthesize entry surface now branches on `decision.recovery_assessment`.
- `tests/test_phase13_v3_tools.py` - Tool-surface regressions now assert `recovery_assessment`, and the importlinter assertion now matches the real config.
- `tests/test_phase14_resume_and_reuse.py` - Resume/stage-entry regressions now assert `recovery_assessment` and current guidance wording.
- `tests/test_phase16_selection.py` - Selection test helpers now seed `RecoveryAssessment` with `recovery_assessment`.
- `tests/test_phase24_stage_next_step_guidance.py` - Phase 24 guidance regression now constructs `RecoveryAssessment` with the renamed field.
- `.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-02-SUMMARY.md` - Execution summary, deviation log, and self-check evidence for Plan 25-02.

## Decisions Made

- Treated the rename as a contract correction, not a compatibility layer, so stale `disposition` payloads now fail fast under `extra="forbid"`.
- Kept all recovery behavior and enum values stable so downstream logic changes are limited to field access, not semantics.
- Updated the skill-loop history record as well as public tool payloads so diagnostic traces and operator-visible JSON stay aligned.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Aligned a stale Phase 13 importlinter assertion with the real forbidden-modules config**
- **Found during:** Plan verification (`tests/test_phase13_v3_tools.py`)
- **Issue:** `test_importlinter_forbids_v3_tool_layer_fallbacks` asserted that `app.query_services`, `app.runtime`, and `core.loop` should be absent from `.importlinter`, which contradicted the actual config and the neighboring Phase 14 isolation tests.
- **Fix:** Updated the assertion to require those modules in the forbidden list so the regression matches the enforced importlinter contract.
- **Files modified:** `tests/test_phase13_v3_tools.py`
- **Verification:** `uv run python -m pytest tests/test_phase25_disposition_rename.py tests/test_phase13_v3_tools.py tests/test_phase14_resume_and_reuse.py tests/test_phase16_selection.py tests/test_phase24_stage_next_step_guidance.py -x -q`
- **Committed in:** `cf44837` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope creep in product code. The deviation only corrected a pre-existing regression gate contradiction so the rename could be verified truthfully.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `25-03` can now assume all recovery- and decision-shaped payloads use `recovery_assessment`, so the remaining work can focus on multi-branch defaults and stage materialization.
- Wave 1 is complete; Phase 25 can move to `25-03` once the pre-wave dependency check confirms both summary artifacts are in place.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-02-SUMMARY.md`.
- Verified task commits `46cbb5e` and `cf44837` exist in git history.

---
*Phase: 25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps*
*Completed: 2026-03-23*
