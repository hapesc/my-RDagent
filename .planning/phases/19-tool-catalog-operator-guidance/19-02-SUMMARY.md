---
phase: 19-tool-catalog-operator-guidance
plan: 02
subsystem: tool-catalog
tags: [cli, tool-catalog, follow-up, regression, pytest]
requires:
  - phase: 19-tool-catalog-operator-guidance
    provides: examples/routing payload contract and Wave 0 regression scaffold
provides:
  - structured follow_up semantics for every direct V3 tool
  - representative surface assertions in the phase16 regression suite
  - Phase 19 full-suite compatibility with schema and category tests
affects: [phase-19, phase-20, cli-surface, operator-flow]
tech-stack:
  added: []
  patterns: [operator-visible next-step guidance, representative-plus-exhaustive regression layering]
key-files:
  created: []
  modified: [v3/entry/tool_catalog.py, tests/test_phase16_tool_surface.py, tests/test_phase19_tool_guidance.py]
key-decisions:
  - "Follow-up semantics are outcome-oriented and point to the next entrypoint instead of internal service details."
  - "rd_branch_shortlist leads back to rd-agent by default and only mentions rd_converge_round as an explicit downshift."
patterns-established:
  - "Every direct tool entry can now answer what success means and what to do next."
  - "Representative legacy tests and focused phase tests both guard the same public contract."
requirements-completed: [GUIDE-03]
duration: 12min
completed: 2026-03-22
---

# Phase 19: Tool Catalog Operator Guidance Summary

**Direct V3 tools now tell the operator what a successful call means and which entrypoint to use next.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-22T04:43:00Z
- **Completed:** 2026-03-22T04:54:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `follow_up.when_successful`, `follow_up.next_entrypoint`, and `follow_up.next_action` to every direct tool entry in [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py).
- Expanded [test_phase19_tool_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase19_tool_guidance.py) to cover full-surface follow-up semantics.
- Extended [test_phase16_tool_surface.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase16_tool_surface.py) with representative follow-up assertions and kept the full suite green.

## Task Commits

1. **Task 1 + Task 2: follow-up semantics and full-surface regression lock** - `2e2dc74` (`feat`)

## Files Created/Modified
- `v3/entry/tool_catalog.py` - now emits structured next-step semantics for every direct tool
- `tests/test_phase19_tool_guidance.py` - now validates follow-up coverage across the full registry
- `tests/test_phase16_tool_surface.py` - now checks representative follow-up behavior on legacy surface tests

## Decisions Made
- Follow-up guidance must stay operator-visible and outcome-oriented.
- Selection, recovery, and orchestration tools need the most explicit next-action language because that is where agents most often stall.

## Deviations from Plan

None - plan executed exactly as written after the planning revision aligned Wave 0 and Wave 2 verification gates.

## Issues Encountered

The planning checker initially flagged a routing ambiguity in `rd_branch_shortlist`. The final implementation resolved it by making `rd-agent` the default next path and treating `rd_converge_round` as an intentional downshift.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 19 is complete and regression-locked.
- Phase 20 can now focus entirely on stage-skill input contracts and pause/continue semantics without reopening the direct-tool layer.

---
*Phase: 19-tool-catalog-operator-guidance*
*Completed: 2026-03-22*
