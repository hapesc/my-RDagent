---
phase: 19-tool-catalog-operator-guidance
plan: 01
subsystem: tool-catalog
tags: [cli, tool-catalog, examples, routing, pytest]
requires:
  - phase: 17-skill-and-cli-surface-terminology-convergence
    provides: stable category, subcategory, and recommended_entrypoint metadata
provides:
  - structured examples for every direct V3 tool
  - explicit when_to_use/when_not_to_use routing guidance on the public tool payload
  - Phase 19 Wave 0 regression coverage for examples and routing
affects: [phase-19, phase-20, cli-surface, tool-guidance]
tech-stack:
  added: []
  patterns: [single-source tool metadata, field-based public-surface regressions]
key-files:
  created: [tests/test_phase19_tool_guidance.py]
  modified: [v3/entry/tool_catalog.py, tests/test_v3_tool_cli.py]
key-decisions:
  - "Examples and routing guidance live directly on the catalog payload rather than in prose-only docs."
  - "Every direct tool gets one common_path example using stable repo-consistent placeholders."
patterns-established:
  - "Catalog-first operator guidance: list/describe share one payload family."
  - "Wave 0 uses collect-only scaffolding before implementation, then closes with the full suite."
requirements-completed: [GUIDE-01, GUIDE-02]
duration: 25min
completed: 2026-03-22
---

# Phase 19: Tool Catalog Operator Guidance Summary

**Direct V3 tools now expose actionable examples and routing boundaries from the catalog payload itself.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-22T04:20:00Z
- **Completed:** 2026-03-22T04:43:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added one `common_path` example to every direct tool entry in [tool_catalog.py](/Users/michael-liang/Code/my-RDagent-V3/v3/entry/tool_catalog.py).
- Added explicit `when_to_use` and `when_not_to_use` routing guidance while preserving existing schema/category metadata.
- Created [test_phase19_tool_guidance.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_phase19_tool_guidance.py) and extended [test_v3_tool_cli.py](/Users/michael-liang/Code/my-RDagent-V3/tests/test_v3_tool_cli.py) to lock the Wave 0 contract.

## Task Commits

1. **Task 1 + Task 2: examples, routing guidance, and Wave 0 regressions** - `dd67ac7` (`feat`)

## Files Created/Modified
- `v3/entry/tool_catalog.py` - now emits examples and routing guidance on every direct tool payload
- `tests/test_v3_tool_cli.py` - now asserts public list/describe payloads expose examples and routing fields
- `tests/test_phase19_tool_guidance.py` - Wave 0 focused regression coverage for examples and routing guidance

## Decisions Made
- Examples and routing semantics belong on the direct tool payload, not in README-only prose.
- Stable placeholders such as `run-001`, `branch-001`, `primary`, and `memory-001` are the canonical example IDs for this phase.

## Deviations from Plan

Wave 0 verification was tightened during planning revision:
- the test scaffold uses `--collect-only` before implementation
- the wave still closes with the full suite including `tests/test_phase13_v3_tools.py`

## Issues Encountered

Initial plan verification exposed a mismatch between the Nyquist Wave 0 contract and the task ordering. The fix was to separate the scaffold gate from the passing implementation gate instead of weakening the validation bar.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The catalog payload shape is ready for Phase 19 follow-up semantics.
- Existing CLI and schema regressions stayed green, so follow-up work can focus on next-step guidance only.

---
*Phase: 19-tool-catalog-operator-guidance*
*Completed: 2026-03-22*
