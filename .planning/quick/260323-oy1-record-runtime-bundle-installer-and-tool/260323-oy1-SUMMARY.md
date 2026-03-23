# Quick Task 260323-oy1 Summary

**Description:** Record runtime-bundle installer and tool-invocation contract hardening
**Date:** 2026-03-23
**Implementation Commit:** `777d1fc`
**Status:** Completed

## Outcome

Converted standalone V3 installation from skill-only exposure to a managed
runtime-bundle install and tightened the public skill contracts so direct tools
must run from the installed bundle or standalone V3 repo root.

## What Changed

- Reworked the installer to write a managed `rdagent-v3/` runtime bundle plus
  generated installed skills under Claude/Codex runtime roots.
- Added managed runtime and skill markers, preserved unmanaged same-name
  targets, and made link/copy modes rebuild managed targets idempotently.
- Updated source skills and README so direct-tool execution context is explicit:
  `uv run rdagent-v3-tool ...` must run from the installed runtime bundle or
  standalone V3 repo root, and canonical state inspection must not fall back to
  scanning unrelated repos or `HOME`.
- Expanded regression coverage to lock the new install model and the new public
  execution-context wording.

## Validation

```bash
uv run python -m pytest tests/test_phase18_skill_installation.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py tests/test_phase17_surface_convergence.py tests/test_phase18_planning_continuity.py tests/test_phase21_public_surface_narrative.py -q
```

Result: `33 passed`

## Notes

- This quick task records the change as a quick artifact only; it does not
  change `ROADMAP.md`.
- Unrelated untracked planning files and temp state remained outside this quick
  task's staged file set.
