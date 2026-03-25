# Phase 23: Preflight and State Truth Hardening - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the standalone V3 pipeline tell the truth about whether work
can actually proceed. It adds preflight checks for runtime, dependencies,
artifacts, and persisted state before stage execution claims a step is
executable, and it hardens user-visible status/recommendation text so those
claims are backed by canonical V3-owned snapshots and recovery evidence. It
does not redesign the public routing surface, add broader next-step UX polish,
or create new orchestration capabilities outside the existing V3 contracts.

</domain>

<decisions>
## Implementation Decisions

### Preflight must run at the recommendation boundary, not only at execution time
- `rd-agent` should not stop at intent routing alone; when it recommends the
  next high-level action, it should also run preflight truth checks for that
  recommendation.
- The system should not use a two-step story where the entrypoint says "go do
  X" and the next layer later reveals that X was never executable.
- If a paused run points to `rd-code` or `rd-execute`, the reply should still
  identify that recommended next skill, but it must also surface the blocker
  immediately when preflight fails.
- Read-only inspect flows should also expose blocker summaries instead of
  pretending the current state is healthy just because the caller did not ask
  to execute yet.

### Executability truth requires all four evidence classes
- The pipeline may only claim that a stage is executable when all four classes
  of truth pass: persisted state consistency, required artifact presence,
  runtime/dependency readiness, and recovery validity.
- Artifact truth is strict: it is not enough for a snapshot to list an
  `artifact_id`; the underlying artifact must still be loadable/listable from
  V3 state.
- If persisted run, branch, and stage snapshots disagree about the current
  reality, the system must block with an explicit state-inconsistency error
  instead of choosing a canonical source silently.
- If a completed stage is being reused, a recovery assessment must already
  exist. Without that persisted recovery truth, the pipeline must not claim
  the stage is ready to continue.

### Blocker presentation should stay truthful but operational
- Default replies should group blockers by category:
  `runtime`, `dependency`, `artifact`, `state`, and `recovery`.
- The first reply should surface the single most important blocker rather than
  dumping the full blocker inventory up front.
- Fix guidance should be concrete and action-oriented, ideally specific enough
  to give the operator the next command or exact repair step.
- The preferred operator tone is:
  recommend the ideal next skill or path, then immediately say that it is not
  currently executable and why.

### Status language must be downgraded unless truth checks pass
- When preflight fails or cannot be completed, the system must not say
  "ready", "continue now", or any equivalent positive-execution claim.
- In those cases the strongest allowed wording is:
  the recommended path is X, but X is currently blocked by Y.
- `recommended_next_skill` should remain visible even when blocked, because it
  tells the operator the intended path after repair, but it must be paired
  with an explicit blocked/not-executable state.
- Unknown checks count as failed truth. If runtime, artifact, state, or
  recovery status cannot be determined, the surface must treat that as blocked
  or unknown-not-ready, not as soft success.
- User-visible messaging should prioritize the current executable action over
  the ideal future stage progression.

### Claude's Discretion
- Planning may choose whether the new preflight logic lives in a shared helper,
  a service beside `RecoveryService`, or an entry-layer coordinator, as long as
  one canonical truth path is reused across routing and stage entrypoints.
- Planning may choose the exact blocker ranking policy within the locked
  categories, as long as the first reply surfaces one primary blocker and keeps
  the remaining categories inspectable.
- Planning may decide the exact payload field names for any new preflight
  result object as long as they distinguish "recommended path" from "currently
  executable action" and do not blur unknown with ready.

</decisions>

<specifics>
## Specific Ideas

- The current Phase 22 behavior of surfacing `recommended_next_skill` should be
  preserved, but the reply now needs one more truth layer: whether that skill
  is actually executable right now.
- The preferred message shape is:
  current state, recommended path, current blocker, and exact repair action;
  not a vague "inspect more" loop.
- For inspect/read-only requests, the user still wants truth, not a sanitized
  happy path. Showing a blocker summary there is better than forcing the user
  to step into execution just to learn that the state was never viable.
- `resume_planner`'s current "the stage is ready to run" style wording is
  exactly the kind of claim that should become conditional on preflight truth
  rather than stage snapshot status alone.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase truth
- `.planning/PROJECT.md` — active v1.3 milestone framing, non-negotiable
  constraints, and the rule that public state claims must stay V3-owned.
- `.planning/ROADMAP.md` — Phase 23 goal and success criteria for preflight
  and state truth hardening.
- `.planning/REQUIREMENTS.md` — `PREFLIGHT-01`, `PREFLIGHT-02`, `STATE-01`,
  and `STATE-02`, which define the acceptance boundary for this phase.
- `.planning/STATE.md` — current continuity position and the explicit note that
  Phase 23 must decide preflight truth sources.

### Prior phase decisions that still apply
- `.planning/phases/20-stage-skill-execution-contracts/20-CONTEXT.md` —
  locked continuation contracts, pause semantics, and the rule that high-level
  skills should surface missing values precisely rather than making the user
  browse blindly.
- `.planning/phases/22-intent-routing-and-continuation-control/22-CONTEXT.md`
  — locked intent-first routing behavior, paused-run preference, concise
  operator-facing output, and the rule that `rd-tool-catalog` stays
  subordinate.

### Architecture and persistence truth
- `.planning/codebase/ARCHITECTURE.md` — current V3 layering, state-store
  boundary, and orchestration/data-flow overview.
- `.planning/codebase/TESTING.md` — test style, fixture conventions, and the
  existing pattern of asserting both structured payloads and operator text.
- `v3/ports/state_store.py` — canonical persistence interface for run, branch,
  stage, artifact, and recovery snapshots.
- `v3/orchestration/stage_transition_service.py` — current publisher of
  branch-stage truth into persisted snapshots.
- `v3/orchestration/recovery_service.py` — current canonical interpretation of
  artifact/recovery truth and invalidation reasons.
- `v3/orchestration/resume_planner.py` — current source of resume/ready/review
  messaging that must be hardened against false-ready claims.
- `v3/orchestration/skill_loop_service.py` — current high-level stage chaining
  path that seeds READY stages and persists stop reasons.
- `v3/orchestration/execution_policy.py` — current stop/continue semantics that
  interact with user-visible readiness claims.

### Entry surfaces affected by preflight truth
- `v3/entry/rd_agent.py` — current intent router and recommendation surface
  that will need preflight-aware next-step truth.
- `v3/entry/rd_code.py` — representative build-stage entrypoint currently using
  state, artifacts, and recovery truth for continuation decisions.
- `v3/entry/rd_execute.py` — representative verify-stage entrypoint with both
  completion and blocked outcomes.
- `skills/rd-agent/SKILL.md` — current public routing contract that should stay
  truthful once preflight is introduced.
- `README.md` — current public `Start -> Inspect -> Continue` narrative that
  must not drift away from runtime truth.

### Verification anchors
- `tests/test_phase14_stage_skills.py` — stage snapshot, replay, and blocked
  verification behavior over persisted state.
- `tests/test_phase14_resume_and_reuse.py` — resume/reuse/replay/review truth
  over stage and recovery artifacts.
- `tests/test_phase14_execution_policy.py` — public stop reasons and iteration
  boundaries that shape current user-visible state claims.
- `tests/test_phase16_rd_agent.py` — end-to-end rd-agent orchestration flow
  over persisted snapshots.
- `tests/test_phase22_intent_routing.py` — current recommendation surface that
  Phase 23 will harden with preflight truth instead of replacing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `v3/ports/state_store.py` already defines one canonical read/write boundary
  for run, branch, stage, artifact, and recovery truth; Phase 23 should build
  on that instead of adding a second state source.
- `v3/orchestration/recovery_service.py` already computes concrete invalid
  reasons such as missing artifacts, stale evidence, and blocked stages, so it
  is a natural truth input for the new preflight layer.
- `v3/orchestration/resume_planner.py` already centralizes operator-facing
  resume decisions, making it a likely place where preflight-aware messaging
  must be introduced or consumed.
- `v3/entry/rd_agent.py` now owns the intent-first recommendation surface and
  is the natural place to expose "recommended path vs blocked reality."
- `v3/entry/rd_code.py` and `v3/entry/rd_execute.py` already gather run,
  branch, stage, artifact, and recovery state before acting, so their entry
  flow is a direct integration point for execution-time preflight.

### Established Patterns
- Public truth in this repo is expected to come from persisted V3 snapshots and
  structured result payloads, not from prose-only heuristics.
- The test suite favors deterministic seeded state plus explicit assertions on
  both `structuredContent` and human-readable `content`; Phase 23 should keep
  that style rather than introduce snapshot-heavy golden tests.
- High-level surfaces should stay agent-first and operator-facing; direct-tool
  browsing remains a fallback, not the primary answer to missing or conflicting
  state.
- Existing orchestration code distinguishes recommendation, blocked, replay,
  and review outcomes already; the gap is not missing structure but insufficient
  truth gating before emitting user-facing claims.

### Integration Points
- Planning should expect cross-cutting changes across `rd_agent`,
  stage-specific entrypoints, recovery/resume logic, and their tests; this is
  not a single-file patch.
- A shared preflight result object or service is likely needed so routing-time
  and execution-time truth use the same rules and blocker categories.
- The user-facing phrases that currently imply readiness live in both entry
  modules and orchestration helpers, so message hardening must be coupled to
  truth checks rather than applied as ad hoc string edits.

</code_context>

<deferred>
## Deferred Ideas

- Richer operator-facing next-step UX polish, including how much detail to show
  by default and when to progressively disclose more context, belongs to
  Phase 24.
- Machine-readable remediation workflows or semi-automated environment repair
  flows belong to later pipeline UX work, not this phase.
- Multi-run or cross-branch unified progress surfaces remain future work beyond
  this phase's single-path preflight truth boundary.

</deferred>

---

*Phase: 23-preflight-and-state-truth-hardening*
*Context gathered: 2026-03-22*
