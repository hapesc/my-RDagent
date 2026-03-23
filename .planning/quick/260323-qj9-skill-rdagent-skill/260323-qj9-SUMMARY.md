---
phase: quick
plan: 260323-qj9
subsystem: skills
tags: [skill-refactoring, blueprint, progressive-disclosure, deduplication]

# Dependency graph
requires:
  - phase: quick-260323-qfz
    provides: "Skill improvement analysis identifying what to refactor"
provides:
  - "Complete refactoring blueprint for all 6 RDagent skills"
  - "Dependency-ordered execution sequence (6 waves)"
  - "Mechanical skill-review checklist"
  - "Shared reference extraction map eliminating 4x duplication"
affects: [skill-refactoring-execution, rd-agent, rd-propose, rd-code, rd-execute, rd-evaluate, rd-tool-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: ["thin-adapter-skill", "shared-parameterized-references", "progressive-disclosure-loading"]

key-files:
  created:
    - ".planning/quick/260323-qj9-skill-rdagent-skill/BLUEPRINT.md"
  modified: []

key-decisions:
  - "Shared references go in skills/_shared/references/ with a symlink from .claude/skills/_shared"
  - "Use repo-root-relative @skills/_shared/references/ paths, not relative ../_shared/ paths, to avoid symlink resolution ambiguity"
  - "Merge rd-agent stop-behavior into start-contract workflow rather than creating a 7-line orphan reference"
  - "Parameterization table approach over literal template variables for stage-specific shared references"

patterns-established:
  - "Skill refactoring wave ordering: shared infra -> shared extractions -> stage skills (parallel) -> orchestrator skill -> polish -> verification"
  - "Mechanical skill-review checklist with grep/wc verification commands"

requirements-completed: [SKILL-REFACTOR-BLUEPRINT]

# Metrics
duration: 4min
completed: 2026-03-23
---

# Quick Task 260323-qj9: Skill Refactoring Blueprint Summary

**570-line blueprint converting 260323-qfz skill-improvement analysis into concrete extraction maps, shared references, wave-ordered execution sequence, and mechanical review checklist for all 6 RDagent skills**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T11:11:57Z
- **Completed:** 2026-03-23T11:16:00Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- Created complete extraction map for all 6 skills with source line ranges and destination files
- Defined 5 shared references and 2 rd-agent-specific workflows with explicit scope boundaries (owns / does not own)
- Established 6-wave dependency-ordered execution sequence with per-wave verification gates
- Built mechanical skill-review checklist with structural verification commands (grep, wc, diff)
- Documented symlink risks and progressive-disclosure constraints as non-negotiable execution requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Produce the skill refactoring blueprint** - `1e24519` (docs)

## Files Created/Modified

- `.planning/quick/260323-qj9-skill-rdagent-skill/BLUEPRINT.md` - Complete refactoring blueprint with 6 parts: target architecture, per-skill extraction map, workflow/reference definitions, skill-review checklist, execution order, risk notes

## Decisions Made

1. **Shared references location:** `skills/_shared/references/` with a `.claude/skills/_shared` symlink, rather than duplicating references per skill or using a separate `references/` root directory. Rationale: keeps shared content within the skills tree while making it accessible through both entry points.

2. **Repo-root-relative paths:** All SKILL.md reference lines use `@skills/_shared/references/...` instead of relative `../_shared/references/...`. Rationale: symlinks make `..` resolution unpredictable depending on which entry point loaded the skill.

3. **Stop-behavior merged into start-contract:** Rather than creating a standalone `references/stop-behavior.md` (7 lines), merged it into `workflows/start-contract.md` where it logically belongs (stop behavior is defined by the start payload's execution_mode).

4. **Parameterization table over templates:** Shared references contain a parameter table that the loading SKILL.md references contextually, rather than literal `{stage_name}` template variables. Rationale: Claude does not natively support template substitution in `@` references.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Steps

The BLUEPRINT.md is ready for execution. An executor can pick up any wave and apply it independently:
- Wave 0 (infrastructure) and Wave 1 (shared references) have no prerequisites
- Wave 2 (stage skills) depends on Wave 1
- Wave 3 (rd-agent) depends on Wave 2 proving the pattern
- Wave 4 (rd-tool-catalog) can run in parallel with Waves 2-3
- Wave 5 (verification) is the final cross-skill audit

---
*Quick task: 260323-qj9*
*Completed: 2026-03-23*
