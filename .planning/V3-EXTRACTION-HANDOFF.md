---
artifact: v3-extraction-handoff
created: 2026-03-21T15:30:00+08:00
status: historical
related_milestone: v1.0
related_phase: 16
---

# V3 Extraction Handoff

## Historical Status

This document is historical extraction evidence from the original standalone
split. It is not the canonical continuity entrypoint for current standalone
work.

For active planning continuity, start from `.planning/STATE.md` and the current
`.planning/` phase artifacts.

## Extracted State At Handoff Time

The original worktree had a V3 surface that no longer used the in-process
`mcp_tools` compatibility layer. The extracted V3 surface at that time was:

- `v3.entry.tool_catalog`
- `v3.entry.tool_cli`
- `v3.entry.rd_agent`
- skill entrypoints under `v3.entry`

Historical extraction commit:

- commit: `5bbb35f`
- message: `init standalone V3 surface`

## Completed Work

- Removed `v3/entry/mcp_tools.py` from the V3 surface in the source worktree.
- Added a CLI-oriented tool catalog:
  - `v3/entry/tool_catalog.py`
  - `v3/entry/tool_cli.py`
- Rewired `v3/entry/rd_agent.py` to call `call_cli_tool(...)` instead of `call_mcp_tool(...)`.
- Internalized the remaining Phase 16 algorithm helpers into V3:
  - `v3/algorithms/puct.py`
  - `v3/algorithms/prune.py`
  - `v3/algorithms/merge.py`
- Updated packaging so the V3 CLI entrypoint exists:
  - script: `rdagent-v3-tool`
- Extracted a minimal standalone V3 repository with:
  - `v3/`
  - `tests/`
  - `pyproject.toml`
  - `.importlinter`
  - `README.md`
  - `.gitignore`

## Verification Evidence

### Source worktree

- `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase13_v3_tools.py tests/test_phase16_tool_surface.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py -q`
  - Result: `29 passed`
- `uv run python -m pytest tests/test_phase15_memory_contracts.py tests/test_phase15_memory_retrieval.py tests/test_phase15_branch_isolation.py tests/test_phase16_branch_lifecycle.py tests/test_phase16_convergence.py tests/test_phase16_selection.py tests/test_phase16_sharing.py -q`
  - Result: `37 passed`
- `uv run lint-imports`
  - Result: `13 kept, 0 broken`

### Standalone extracted repo

- `uv run python -m pytest tests/test_v3_tool_cli.py tests/test_phase14_skill_agent.py tests/test_phase16_rd_agent.py tests/test_phase16_tool_surface.py -q`
  - Result: `9 passed`
- `uv run lint-imports`
  - Result: `8 kept, 0 broken`

## Decisions Made

- Do not preserve a fake MCP surface when no real MCP transport/server exists.
- Prefer a transport-free skill + CLI tool catalog as the V3 product surface.
- Extract only the minimum self-contained V3 package instead of dragging the
  legacy `app/`, `core/`, control-plane, or `exploration_manager` packages into
  the new repository.
- Internalize the Phase 16 algorithm helpers into `v3/algorithms` so the new
  repository remains self-contained.

## Remaining Work

### In the original worktree

- The refactor changes in the current worktree are not yet committed.
- The current milestone audit still reflects the old wording around `MCP-02`;
  if desired, planning artifacts should be updated to describe the new
  skill/CLI surface explicitly.

### In the standalone repo

- Add further documentation for the intended long-term product surface.
- Decide whether to rename requirement language from `MCP-02` to a new
  skill/CLI tool-surface requirement family.
- Decide whether to keep `v3/compat/v2` in the extracted repo or prune it in a
  follow-up cleanup.

## Current Continuity Note

This handoff is retained for historical context only.

- Current standalone continuity lives in `.planning/STATE.md`.
- Current planning context lives in `.planning/ROADMAP.md`,
  `.planning/REQUIREMENTS.md`, and the Phase 18 artifacts under
  `.planning/phases/18-standalone-packaging-and-planning-autonomy/`.
- Removed upstream startup instructions are obsolete and should not be used for
  future sessions.
