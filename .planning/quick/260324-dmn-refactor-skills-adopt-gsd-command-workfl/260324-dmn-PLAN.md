---
type: quick
quick_id: "260324-dmn"
description: "refactor(skills): adopt GSD command/workflow separation architecture"
date: "2026-03-24"
status: complete
tasks: 5
---

# Quick Task 260324-dmn: Refactor skills to adopt GSD command/workflow separation

## Goal

Restructure all 6 RD-Agent V3 skills to borrow GSD's proven command/workflow
separation patterns: thin SKILL.md entries, structured `<step>` workflows,
shared `_shared/references/` layer, and Codex compatibility adapters.

## Plan 01: Create shared references layer and refactor all skills

### Task 1: Create `_shared/references/` shared layer
- **files:** `skills/_shared/references/stage-contract.md`, `skills/_shared/references/tool-execution-context.md`, `skills/_shared/references/failure-routing.md`, `skills/_shared/references/output-conventions.md`
- **action:** Extract ~70% repeated content from 4 stage skills into shared reference files
- **verify:** Files exist, content covers: stage routing constraints, CLI execution context, failure handling, output format conventions
- **done:** 4 shared reference files created

### Task 2: Refactor rd-propose (pilot)
- **files:** `skills/rd-propose/SKILL.md`, `skills/rd-propose/workflows/continue.md`
- **action:** Thin SKILL.md to ~25 lines with frontmatter (argument-hint, allowed-tools), `<execution_context>` @refs, `<codex_skill_adapter>` block. Restructure workflow with `<step>`, `<purpose>`, `<success_criteria>`.
- **verify:** SKILL.md has YAML frontmatter + XML structure, workflow has named steps
- **done:** Both files rewritten

### Task 3: Refactor remaining stage skills (rd-code, rd-execute, rd-evaluate)
- **files:** `skills/rd-code/SKILL.md`, `skills/rd-code/workflows/continue.md`, `skills/rd-execute/SKILL.md`, `skills/rd-execute/workflows/continue.md`, `skills/rd-evaluate/SKILL.md`, `skills/rd-evaluate/workflows/continue.md`
- **action:** Apply rd-propose template to all 3 remaining stage skills, with stage-specific differences (rd-execute has blocking_reasons, rd-evaluate has recommendation field)
- **verify:** All 6 files follow the new format, stage-specific fields preserved
- **done:** All 6 files rewritten

### Task 4: Refactor rd-agent (orchestration entry)
- **files:** `skills/rd-agent/SKILL.md`, `skills/rd-agent/workflows/intent-routing.md`, `skills/rd-agent/workflows/start-contract.md`
- **action:** Thin SKILL.md from 96→~35 lines. Restructure intent-routing.md with routing table + `<step>` flow. Restructure start-contract.md with minimum/recommended contract steps. Delete `rd-agent/references/failure-routing.md` (promoted to _shared).
- **verify:** SKILL.md thinned, workflows structured, old failure-routing.md removed
- **done:** 3 files rewritten, 1 file deleted

### Task 5: Light refactor rd-tool-catalog
- **files:** `skills/rd-tool-catalog/SKILL.md`
- **action:** Add frontmatter (argument-hint, allowed-tools), `<execution_context>` @refs, `<codex_skill_adapter>` block. No workflow added (stateless query entry).
- **verify:** SKILL.md has new frontmatter and XML structure
- **done:** File rewritten
