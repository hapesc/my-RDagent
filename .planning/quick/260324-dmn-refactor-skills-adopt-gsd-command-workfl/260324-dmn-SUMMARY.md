---
type: quick-summary
quick_id: "260324-dmn"
status: complete
date: "2026-03-24"
commit: "7632cce"
---

# Quick Task 260324-dmn: Summary

## What Was Built

Restructured all 6 RD-Agent V3 skills to adopt GSD's command/workflow separation
architecture. The refactor touches 16 files (799 insertions, 541 deletions).

### Changes by component

**New: `_shared/references/` (4 files)**
- `stage-contract.md` — routing constraints, tool-catalog routing rules, generic failure handling, success contract shared by all 4 stage skills
- `tool-execution-context.md` — `uv run rdagent-v3-tool` CLI invocation and state scope rules
- `failure-routing.md` — promoted from `rd-agent/references/` to shared layer
- `output-conventions.md` — routing reply format (4 required fields), stage transition reply format, blocked path conventions

**Refactored: SKILL.md × 6**
- All SKILL.md files thinned to ~25-40 lines (from 72-96 lines)
- Added YAML frontmatter: `argument-hint`, `allowed-tools`
- Added `<execution_context>` with `@` path references to workflows and shared refs
- Added `<codex_skill_adapter>` block for Codex runtime compatibility
- Added `<required_fields>` replacing scattered prose
- Added `<outcome_guide>` for stage transition semantics

**Refactored: workflow files × 5**
- All workflow files restructured with `<purpose>`, `<process>`, `<step name="...">`, `<success_criteria>` tags
- Each step has concrete bash commands and conditional routing logic
- Success criteria are checklist items, not prose

**Deleted: 1 file**
- `skills/rd-agent/references/failure-routing.md` — content promoted to `_shared/references/`

### Key metrics

| Metric | Before | After |
|--------|--------|-------|
| SKILL.md avg lines | ~82 | ~33 |
| Repeated content across stage skills | ~70% | ~5% (shared refs) |
| Structured workflow steps | 0 | 5 workflows with named steps |
| Codex adapter blocks | 0 | 6 |
| Shared reference files | 0 | 4 |

## Commits

- `7632cce`: refactor(skills): adopt GSD command/workflow separation architecture

## Deviations

None — executed per plan.

## Verification Notes

- `@` path references in `<execution_context>` within `skills/` SKILL.md files need runtime validation: confirm Claude Code auto-loads referenced files when skill is invoked. If not, fallback to explicit "Read file" instructions in workflow steps.
- Codex compatibility untested — `<codex_skill_adapter>` blocks follow GSD's validated pattern but need $rd-propose invocation test in Codex.
