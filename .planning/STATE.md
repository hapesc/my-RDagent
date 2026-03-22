---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: skill-and-tool-guidance-hardening
status: ready_for_closeout
stopped_at: Completed 21-01-PLAN.md
last_updated: "2026-03-22T07:00:45.451Z"
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
**Current focus:** Phase 21 complete — executable-public-surface-narrative

## Position

**Milestone:** v1.2 skill and tool guidance hardening  
**Roadmap span:** Phases 19-21
**Next phase:** None - milestone v1.2 is complete
**Status:** Phase 21 complete; milestone ready for closeout
**Canonical continuity entrypoint:** `.planning/STATE.md`

**Last activity:** 2026-03-22
Completed Phase 21 by rewriting `README.md` into an executable `Start -> Inspect -> Continue` public playbook and adding focused regression coverage for the README narrative.
**Progress:** [██████████] 100%

## Performance Metrics

- Completed plans in shipped milestones: 32
- Current milestone planned phases: 3
- Current milestone planned plans: 5 completed, 0 remaining
- Latest completed plan: Phase 21 Plan 01 in 2min across 2 tasks and 3 tracked files
- Current milestone execution trend: Phase 21 completed the README-level public narrative lock; the milestone is now ready for closure or the next milestone discussion

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

- Close out milestone v1.2 or start the next milestone discussion.

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

Last session: 2026-03-22T07:00:45.451Z
Stopped at: Completed 21-01-PLAN.md
Resume file: .planning/STATE.md
