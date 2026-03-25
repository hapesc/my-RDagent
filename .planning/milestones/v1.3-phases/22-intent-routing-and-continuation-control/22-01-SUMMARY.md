---
phase: 22-intent-routing-and-continuation-control
plan: 01
subsystem: routing
tags: [rd-agent, routing, continuation, readme, pytest]
requires:
  - phase: 21-executable-public-surface-narrative
    provides: public start-inspect-continue narrative and regression anchors
  - phase: 20-stage-skill-execution-contracts
    provides: stage-skill continuation contracts and stage-to-skill mapping
provides:
  - intent-aware rd-agent routing surface for plain-language entry
  - paused-run-first continuation recommendation payload
  - Phase 22 routing regression coverage
affects: [operator-guidance, routing, continuation, regression-suite]
tech-stack:
  added: []
  patterns: [intent-first-routing, paused-run-preference, exact-string-doc-regressions]
key-files:
  created:
    - .planning/phases/22-intent-routing-and-continuation-control/22-01-SUMMARY.md
    - tests/test_phase22_intent_routing.py
  modified:
    - README.md
    - skills/rd-agent/SKILL.md
    - v3/entry/rd_agent.py
key-decisions:
  - "Kept rd-agent as the public high-level entrypoint and exposed rd-tool-catalog only after the high-level boundary is proven insufficient."
  - "Made paused-run continuation the dominant routing anchor when persisted state exposes a current run, branch, and stage."
patterns-established:
  - "Intent-first routing replies should expose current_state, routing_reason, exact_next_action, and recommended_next_skill explicitly."
  - "Continuation routing should map persisted stage keys directly to stage skills instead of forcing the operator to infer the next surface from prose."
requirements-completed: [ROUTE-01, ROUTE-02]
duration: 10min
completed: 2026-03-22
---

# Phase 22 Plan 01: Intent Routing and Continuation Control Summary

**rd-agent now routes plain-language intent through persisted state, prefers paused-run continuation, and returns an explicit next-skill recommendation**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-22T16:47:31+08:00
- **Completed:** 2026-03-22T16:57:31+08:00
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added a dedicated Phase 22 regression file that locks plain-language entry, paused-run-first routing, explicit `recommended_next_skill`, and controlled downshift behavior.
- Extended `v3/entry/rd_agent.py` with an intent-aware routing layer that inspects persisted state and maps paused runs to the correct continuation skill.
- Updated `skills/rd-agent/SKILL.md` and `README.md` so the public guidance matches the runtime routing surface without promoting `rd-tool-catalog` to a coequal entrypoint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add focused Phase 22 regressions for intent-first and paused-run-first routing** - `d885829` (test)
2. **Task 2: Implement intent-aware routing and state-aware next-step recommendations** - `7a09739` (feat)

## Files Created/Modified

- `tests/test_phase22_intent_routing.py` - Focused Phase 22 routing regression suite covering plain-language entry, paused-run continuation, explicit next-skill output, and controlled downshift.
- `v3/entry/rd_agent.py` - Adds `route_user_intent`, paused-run extraction, stage-to-skill routing, and concise operator-facing recommendation fields.
- `skills/rd-agent/SKILL.md` - Documents intent-first entry behavior and paused-run continuation preference.
- `README.md` - Aligns the public Start/Inspect/Continue story with the new routing payload and continuation-first behavior.
- `.planning/phases/22-intent-routing-and-continuation-control/22-01-SUMMARY.md` - Execution summary, decisions, and verification record for Plan 22-01.

## Decisions Made

- Preserved `rd-agent` as the public first-class start surface even when the user speaks in plain language instead of naming a skill.
- Made paused-run continuation the default routing choice only when persisted state clearly exposes the active run, branch, and stage.
- Kept `rd-tool-catalog` subordinate to the high-level route by using it only when the high-level boundary is explicitly insufficient.

## Deviations from Plan

None in product scope. The plan executed as written.

## Issues Encountered

- The initial executor runtime returned incomplete completion signals, so execution was spot-checked through git history and on-disk artifacts before continuing. This affected orchestration only, not the Phase 22 code path.
- The Python test environment initially lacked `pytest`; `uv sync --extra test` resolved that execution prerequisite before the red/green test cycle continued.

## User Setup Required

None.

## Verification

- `uv run python -m pytest tests/test_phase22_intent_routing.py -q`
- `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q`
- `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py -q`
- `uv run lint-imports`
- `rg -n "recommended_next_skill|paused run|rd-code|rd-execute|rd-tool-catalog" v3/entry/rd_agent.py tests/test_phase22_intent_routing.py`

## Next Phase Readiness

- Phase 22 now supplies the intent-routing layer that Phase 23 can harden with preflight and state-truth checks.
- The public docs and regression suite are aligned around the same continuation-first routing story, so later phases can refine blockers and operator UX without reopening route ownership.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/22-intent-routing-and-continuation-control/22-01-SUMMARY.md`.
- Verified task commits `d885829` and `7a09739` exist in git history.
