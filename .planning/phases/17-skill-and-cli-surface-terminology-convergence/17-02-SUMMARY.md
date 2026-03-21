---
phase: 17-skill-and-cli-surface-terminology-convergence
plan: 02
subsystem: cli
tags: [python, pytest, pydantic, cli-catalog, surface-terminology]
requires:
  - phase: 16-multi-branch-orchestration-and-tool-surface-completion
    provides: existing CLI catalog, describe/list entrypoint, and phase 16 surface tests
provides:
  - Phase 17 regression scaffold for skill/CLI terminology drift
  - Stable catalog category, primitive subcategory, and routing metadata
  - CLI and phase-surface tests that lock the public payload shape
affects: [17-03-PLAN.md, README.md, skill-packages, phase-18-packaging]
tech-stack:
  added: []
  patterns: [catalog-owned surface metadata, thin CLI passthrough verification]
key-files:
  created: [tests/test_phase17_surface_convergence.py]
  modified: [v3/entry/tool_catalog.py, tests/test_v3_tool_cli.py, tests/test_phase16_tool_surface.py]
key-decisions:
  - "Keep classification metadata in _ToolSpec so list_cli_tools() and get_cli_tool() emit one stable payload shape."
  - "Route only orchestration tools to rd-agent; keep inspection and primitive tools on rd-tool-catalog."
patterns-established:
  - "Catalog metadata is the source of truth for category, subcategory, and recommended entrypoint."
  - "Phase-level surface tests read planning docs and README directly to catch terminology drift early."
requirements-completed: [SURFACE-01, SURFACE-02, SURFACE-03]
duration: 7min
completed: 2026-03-21
---

# Phase 17 Plan 02: Catalog classification metadata and phase-surface regression summary

**Phase 17 now ships an early surface-regression scaffold plus structured CLI catalog metadata for category, primitive subcategory, and recommended entrypoint routing**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T09:40:10Z
- **Completed:** 2026-03-21T09:46:45Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added `tests/test_phase17_surface_convergence.py` to lock the initial Phase 17 skill/CLI terminology and README surface before later README rewrites.
- Extended `v3/entry/tool_catalog.py` so every public tool now exposes `category`, `subcategory`, and `recommended_entrypoint` from a single source of truth.
- Updated CLI and phase-level tests to verify structured payload fields and representative primitive subcategory assignments.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the Phase 17 regression scaffold before later waves run** - `f3d953d` (test)
2. **Task 2: Add stable category and routing metadata to the catalog source of truth** - `751bc7e` (feat)
3. **Task 3: Retarget CLI surface tests to the new structured metadata** - `93636a3` (test)

## Files Created/Modified
- `tests/test_phase17_surface_convergence.py` - early regression scaffold for `SURFACE-*` requirements and current README skill/CLI names
- `v3/entry/tool_catalog.py` - source-of-truth metadata for catalog classification and recommended routing
- `tests/test_v3_tool_cli.py` - CLI payload assertions for `list` and `describe`
- `tests/test_phase16_tool_surface.py` - representative category and primitive subcategory coverage

## Decisions Made

- Stored category, primitive subcategory, and routing guidance on `_ToolSpec` so catalog payloads stay stable without adding behavior to `v3/entry/tool_cli.py`.
- Used `rd-agent` only for orchestration tools and `rd-tool-catalog` for inspection and primitive tools so routing guidance is machine-readable and consistent with Phase 17 terminology goals.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan `17-03` can extend the existing Phase 17 regression scaffold with stronger README convergence checks instead of creating new test scaffolding.
- README and skill-package work can consume catalog metadata directly without inferring classification from prose.

## Self-Check

PASSED.

---
*Phase: 17-skill-and-cli-surface-terminology-convergence*
*Completed: 2026-03-21*
