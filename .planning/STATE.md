---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: skill-and-tool-guidance-hardening
status: defining_requirements
stopped_at: Started milestone v1.3 Pipeline Experience Hardening
last_updated: "2026-03-22T15:30:00+08:00"
last_activity: 2026-03-22
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 5
  completed_plans: 5
  percent: 100
---

# Session State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** A developer can use a self-contained V3 skill and CLI surface
on top of V3-owned contracts and orchestration, without reading source code
just to discover how to start, pause, resume, or continue the loop.
**Current focus:** Milestone v1.3 — Pipeline Experience Hardening

## Position

**Milestone:** v1.3 pipeline experience hardening  
**Roadmap span:** defining fresh requirements and roadmap
**Next phase:** Not started — requirements and roadmap definition
**Status:** Defining requirements
**Canonical continuity entrypoint:** `.planning/STATE.md`

**Last activity:** 2026-03-22
Started `v1.3` to improve rdagent’s pipeline UX using `gsd-build/get-shit-done`
as a reference for intent routing, progress guidance, and user-facing flow
design.
**Progress:** [██████████] 100%

## Performance Metrics

- Completed plans in shipped milestones: 32
- Last shipped milestone phases: 3
- Last shipped milestone plans: 5 completed
- Latest completed plan: Phase 21 Plan 01 in 2min across 2 tasks and 3 tracked files
- Current milestone execution trend: v1.3 is in milestone-definition mode; next action is scoped requirements and roadmap creation

## Accumulated Context

### Decisions

- v1.2 stays scoped to guidance hardening for skill metadata, tool metadata,
  and executable operator flows only.

- Tool catalog guidance lands before stage-skill continuation guidance so the
  direct-tool routing layer is explicit first.

- README and regression coverage land after the guidance contracts exist, so
  the public surface is locked after the metadata is hardened.

- Phase 19 context auto-selected structured metadata, full direct-tool example
  coverage, explicit routing guidance, and follow-up semantics as the default
  guidance model.

- Phase 19 completed with a single-source tool-catalog metadata contract for
  examples, routing guidance, and next-step semantics, guarded by
  `tests/test_v3_tool_cli.py`, `tests/test_phase13_v3_tools.py`,
  `tests/test_phase16_tool_surface.py`, and `tests/test_phase19_tool_guidance.py`.

- Phase 20-02 standardized `rd-propose`, `rd-code`, `rd-execute`, and
  `rd-evaluate` on one continuation section layout with the exact shared
  fields `run_id`, `branch_id`, `summary`, and `artifact_ids`.

- Phase 20-02 keeps missing-field recovery agent-led: inspect current run or
  branch state first, surface exact missing values, and use `rd-tool-catalog`
  only as an agent-side escalation path.

- [Phase 20]: Document the strict rd-agent minimum start contract separately from the recommended multi-branch path.
- [Phase 20]: Explain gated + max_stage_iterations=1 in operator language first, then map it secondarily to framing and awaiting_operator.
- [Phase 21-executable-public-surface-narrative]: Kept README at the decision layer and linked to skill packages for exact field contracts instead of duplicating schema inventories.
- [Phase 21-executable-public-surface-narrative]: Positioned rd-tool-catalog only under the Inspect downshift path so rd-agent remains the public first-class start surface.

### Pending Todos

- Define scoped milestone requirements for pipeline UX, routing, preflight, and
  next-step guidance.
- Create a new roadmap continuing phase numbering after Phase 21.

### Blockers/Concerns

- Phase 20 must preserve the completed Phase 19 tool surface rather than
  reopening direct-tool metadata design.

- Stage-skill contract work must align with the new tool-catalog follow-up
  semantics instead of inventing a conflicting routing model.

- Full verification for Plan 20-02 still reports an out-of-scope mismatch in
  `.importlinter` versus `tests/test_phase14_stage_skills.py`; Phase 20-02 did
  not own that infrastructure file, so the issue was documented instead of
  fixed here.

## Session Continuity

Last session: 2026-03-22T15:30:00+08:00
Stopped at: Started milestone v1.3 Pipeline Experience Hardening
Resume file: .planning/STATE.md
