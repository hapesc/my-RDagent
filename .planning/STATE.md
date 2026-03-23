---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: milestone
current_phase: 25
current_phase_name: fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
current_plan: 2
status: executing
stopped_at: Phase 25 plan 01 completed; 25-02 is next
last_updated: "2026-03-23T03:57:35Z"
last_activity: 2026-03-23
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 8
  completed_plans: 6
  percent: 75
---

# Session State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** A developer can use a self-contained V3 skill and CLI surface
on top of V3-owned contracts and orchestration, without reading source code
just to discover how to start, pause, resume, or continue the loop.
**Current focus:** Phase 25 — fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps

## Position

**Current Phase:** 25
**Current Phase Name:** fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps
**Total Phases:** 7
**Current Plan:** 2
**Total Plans in Phase:** 3
**Milestone:** v1.3 pipeline experience hardening  
**Roadmap span:** Phases 22-28
**Next phase:** Phase 26 after Phase 25 completion
**Status:** Ready to execute
**Canonical continuity entrypoint:** `.planning/STATE.md`

**Last activity:** 2026-03-23
Phase 25 plan 01 completed; plan 02 is ready to execute next.
**Progress:** [████████░░] 75%

## Performance Metrics

- Completed plans in shipped milestones: 32
- Last shipped milestone phases: 3
- Last shipped milestone plans: 5 completed
- Latest completed plan: Phase 25 plan 01 completed with 1/3 summarized plan(s)
- Current milestone execution trend: v1.3 phase 25 is in progress

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
- [Phase 22-intent-routing-and-continuation-control]: Route plain-language entry through persisted state first, prefer paused-run continuation, and expose `recommended_next_skill` explicitly.
- [Phase 23]: Preflight stays read-only and does not persist a second truth source. — Runtime and entry surfaces should reuse canonical state instead of introducing another persistence path.
- [Phase 23]: Runtime truth uses pyproject.toml and mandatory uv checks before execution claims. — Phase 23 must derive environment readiness from repo-owned declarations instead of hidden shell heuristics.
- [Phase 23]: Completed-stage reuse is blocked when persisted recovery truth is missing. — Results existing in artifact state is insufficient; Phase 23 must distinguish stored outputs from reproducible continuation.
- [Phase 23]: Paused-run routing keeps recommended_next_skill visible even when canonical preflight blocks execution. — The operator still needs the ideal post-repair path, but the current executable action must be truthful.
- [Phase 23]: Stage entrypoints return preflight_blocked before they publish replay, completion, or blocker state. — Phase 23 requires blocker truth to surface before stage mutation, not after.
- [Phase 23]: Seeded next-stage summaries now say prepared and requires preflight before execution. — Shared operator text must stop implying ready-by-default execution once Phase 23 truth gating exists.

### Pending Todos

- Execute Phase 25 plan 02 to rename `disposition` to `recovery_assessment`
  across recovery models, services, entry surfaces, and tests.

- Execute Phase 25 plan 03 after plan 02 to land multi-branch UX defaults and
  next-stage materialization.

### Roadmap Evolution

- Phase 25 added: Fix QA-discovered operator guidance and multi-branch UX gaps

### Blockers/Concerns

- Wave 1 plans share `rd_propose`, `rd_code`, `rd_execute`, and
  `rd_evaluate`, so plan 25-02 must continue sequentially rather than in
  parallel with 25-01.

- Phase 25 must preserve the Phase 23 preflight truth and the Phase 24
  operator-guidance contract while renaming recovery fields and extending the
  multi-branch start surface.

## Session Continuity

Last session: 2026-03-23T03:57:35Z
Stopped at: Phase 25 plan 01 completed; 25-02 is next
Resume file: .planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-02-PLAN.md
