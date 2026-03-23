# Phase 22: Intent Routing and Continuation Control - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds an intent-first control layer over the existing standalone V3
surface so users can describe work in plain language and get routed to the
correct high-level path. It covers default continuation routing for paused
runs, high-level action selection, and user-facing next-step recommendations.
It does not rebuild core orchestration contracts, add a web UI, or solve the
later preflight/state-truth problems that belong to subsequent phases.

</domain>

<decisions>
## Implementation Decisions

### Intent-first entry is the primary product change
- Users should not need to choose `rd-agent`, `rd-code`, `rd-execute`, or
  `rd-tool-catalog` as their first move.
- The system should accept plain-language intent first, inspect current state,
  and then choose the correct high-level path.
- The default user question to optimize for is:
  "help me do this task" or "what should I do next?", not "which skill should I
  invoke?".

### Paused-run continuation should dominate over new-run creation
- If a clear paused run already exists in the current working context, the
  system should prefer continuation routing over creating a fresh run.
- In that case, the system should surface the current run, current branch,
  current stage, and recommended next skill explicitly.
- Creating a new run should require a positive reason rather than happening as
  the silent default.

### Routing output should be concise and operator-facing
- The default user-facing reply should be compressed to three parts:
  current state, reason for the recommendation, and exact next action.
- Deep orchestration reasoning may still exist internally, but it should not be
  the default user-visible output.
- The routing layer should reduce orchestration jargon rather than amplifying
  it.

### Downshift remains subordinate
- `rd-tool-catalog` remains a downshift surface, not a coequal entrypoint.
- The routing layer should choose `rd-tool-catalog` only when the high-level
  skill boundary is insufficient.
- Common continuation flows should not push the user into manual tool browsing.

### Claude's Discretion
- Planning may choose whether this routing layer lives inside `rd-agent`,
  beside it, or behind a shared helper as long as the user-visible behavior is
  intent-first and state-aware.
- Planning may choose the exact output shape and helper module boundaries as
  long as they preserve the locked behavior above.

</decisions>

<specifics>
## Specific Ideas

- Use the `gsd-build/get-shit-done` pipeline as the reference for one visible
  operator path and strong “what’s next?” answers, not as a reason to copy its
  full artifact surface.
- Treat the real Kaggle logs as primary product evidence: they show that users
  naturally state tasks and ask what to do next, and that forcing them into raw
  skill names is the wrong default UX.
- A good Phase 22 outcome is:
  the user asks for work in plain language, the system says “you already have a
  paused run at build, so continue with `rd-code`”, and the user never has to
  rediscover that from state internals.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase truth
- `.planning/PROJECT.md` — current milestone framing for pipeline-experience
  hardening.
- `.planning/ROADMAP.md` — Phase 22 boundary and success criteria.
- `.planning/REQUIREMENTS.md` — `ROUTE-01` and `ROUTE-02`.
- `.planning/STATE.md` — current project status and continuity context.

### Research inputs
- `.planning/research/SUMMARY.md` — milestone-level research synthesis.
- `.planning/research/RDAGENT-REAL-WORLD-UX-REPORT.md` — primary evidence of
  real user pain points and priority order.
- `.planning/research/ARCHITECTURE.md` — recommended architecture shape for an
  intent router and next-step surface.
- `.planning/research/PITFALLS.md` — concrete anti-patterns to avoid while
  implementing Phase 22.

### Existing public surfaces
- `skills/rd-agent/SKILL.md` — current high-level start contract and pause
  guidance.
- `skills/rd-code/SKILL.md` — representative continuation contract that the
  router may recommend when paused work exists.
- `skills/rd-execute/SKILL.md` — representative later-stage continuation
  contract.
- `skills/rd-tool-catalog/SKILL.md` — current downshift contract that must stay
  subordinate.
- `README.md` — current public narrative that already expresses
  `Start -> Inspect -> Continue` but still assumes the caller already knows the
  right surface.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rd-agent` already owns the high-level orchestration identity and is the most
  plausible host for intent-first routing.
- Stage skill contracts are now explicit, so a router can recommend them
  truthfully instead of guessing from prose.
- Public state artifacts already exist in persisted run/branch/stage snapshots;
  Phase 22 should read those instead of introducing a second state source.

### Established Patterns
- Public surfaces are locked with focused, file-reading regressions and
  explicit string/payload assertions.
- High-level skills should stay above direct tools; tool browsing is a fallback
  path, not a primary operator story.
- README now tells a visible public path; Phase 22 should make the runtime UX
  match that path more closely.

### Integration Points
- The routing layer will likely touch whichever entrypoint currently handles the
  user’s first request and whichever helper reads current persisted state.
- Planning should reserve regression coverage for:
  intent-first requests, paused-run-first recommendations, and “next skill”
  recommendations grounded in current state.

</code_context>

<deferred>
## Deferred Ideas

- Environment/data/runtime preflight belongs to Phase 23.
- State materialization invariants and surface/persisted-state reconciliation
  also belong to Phase 23.
- Broader operator-facing progress UX and “what next?” presentation polish
  belongs to Phase 24.

</deferred>

---

*Phase: 22-intent-routing-and-continuation-control*
*Context gathered: 2026-03-22*
