# Phase 24: Operator Guidance and Next-Step UX - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase consolidates the standalone V3 operator-facing "what next?" answer
into one concise, truthful, state-aware surface. It covers how default next-step
responses should summarize current state, present the recommendation, prioritize
blocked-vs-executable actions, and decide when to expand into concrete commands
or continuation skeletons. It does not add new orchestration capabilities, a
multi-run dashboard, automated environment repair, or a separate cross-run
progress center.

</domain>

<decisions>
## Implementation Decisions

### State summary framing
- The default `current_state` summary should use a mixed operator-facing format:
  lead with plain language first, then include canonical identifiers as
  secondary grounding.
- For paused work, the first line should describe the situation in human terms
  and still preserve `run_id` / `branch_id` in the default answer rather than
  hiding them behind a deeper detail layer.
- Stage naming should use plain-language stage names plus the internal stage key,
  for example "implementation stage (`build`)" or "verification stage
  (`verify`)".
- When no paused run dominates, the default wording should read like an operator
  assistant first and then append the canonical route outcome such as
  `start_new_run` rather than leading with internal routing labels.

### Next action must be minimally executable
- Default `exact_next_action` should target the minimum executable next move,
  not only an abstract action category and not only a skill name.
- When continuation is missing required inputs, the default answer should give a
  minimal continuation skeleton that helps the user fill missing fields rather
  than merely stating that information is missing.
- When preflight blocks the recommendation, the default answer should include
  both the concrete repair action and the continuation target after repair in
  one operator-facing sequence.
- The answer should stay layered: a concise high-level next action first, then a
  one-line minimal command or minimal continuation/start skeleton when needed.

### Blocked responses prioritize the executable repair step
- For blocked paths, the first emphasis should be the currently executable repair
  action, not the ideal future path alone.
- The default blocked response order should be:
  current state -> recommended path -> not currently executable -> repair action
  -> continue target after repair.
- `recommended_next_skill` must remain visible in the first-screen response even
  when the path is blocked.
- Repair guidance should use a hard gate tone: do not imply the user can safely
  continue before the blocker is repaired.

### Detail expansion stays selective
- The surface should automatically expand one layer of detail only when the user
  is blocked or when continuation is missing required fields.
- A healthy paused run should not automatically dump a continuation skeleton in
  the default response; that stays on-demand unless required by missing inputs.
- A new-run recommendation should include a one-line minimum start skeleton by
  default so the user can act immediately without spelunking for the contract.
- The default response may end with one short, fixed detail-offer line such as:
  "If you want, I can expand the next step into the minimum command or
  skeleton."

### Claude's Discretion
- Planning may choose the exact wording templates, field names for plain-language
  stage labels, and whether the detail-offer line is emitted as text content or
  as a structured optional hint field, as long as the locked prioritization and
  expansion rules above hold.
- Planning may decide whether the minimal start / continuation skeleton is
  expressed as prose, fenced text, or a structured payload fragment, as long as
  it stays minimal and directly actionable.

</decisions>

<specifics>
## Specific Ideas

- The preferred state-summary style is "human explanation first, canonical truth
  still visible," not "raw `run-001 / branch-001 / build` first."
- Missing continuation inputs should trigger a concrete minimum skeleton that
  helps the operator fill `run_id`, `branch_id`, `summary`, `artifact_ids`, or
  other required values instead of making them rediscover the contract.
- Blocked responses should behave like a truthful control plane:
  show the intended continuation skill, clearly say it is not executable yet,
  then front-load the repair step.
- The default surface should stay terse by default, but it should proactively
  expand when the user is stuck rather than forcing another round trip just to
  learn the minimum next command or payload.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and phase truth
- `.planning/PROJECT.md` — active v1.3 milestone framing, operator-assistant
  product goal, and the constraint that public guidance must stay grounded in
  persisted state.
- `.planning/ROADMAP.md` — Phase 24 boundary and the `GUIDE-05` success
  criteria.
- `.planning/REQUIREMENTS.md` — `GUIDE-05`, the acceptance requirement for the
  concise "what next?" surface.
- `.planning/STATE.md` — current continuity truth, including the explicit note
  that Phase 24 must decide blocked-vs-recommended next-step UX.

### Prior phase decisions that still apply
- `.planning/phases/20-stage-skill-execution-contracts/20-CONTEXT.md` — locked
  continuation-contract guidance, plain-language operator posture, and the rule
  that missing fields should surface exact values or minimal skeletons instead
  of vague requests.
- `.planning/phases/21-executable-public-surface-narrative/21-CONTEXT.md` —
  locked `Start -> Inspect -> Continue` public narrative and the rule that the
  agent should inspect current state and present the next valid step.
- `.planning/phases/22-intent-routing-and-continuation-control/22-CONTEXT.md`
  — locked concise routing fields (`current_state`, `routing_reason`,
  `exact_next_action`, `recommended_next_skill`) and the rule that paused-run
  continuation dominates over silent fresh starts.
- `.planning/phases/23-preflight-and-state-truth-hardening/23-CONTEXT.md` —
  locked preflight truth, blocked-vs-executable semantics, blocker categories,
  and the requirement that `recommended_next_skill` stays visible even when
  execution is blocked.

### Research inputs
- `.planning/research/RDAGENT-REAL-WORLD-UX-REPORT.md` — primary UX evidence
  that users mainly want current state, reason, next action, and less
  orchestration-heavy narration.
- `.planning/research/FEATURES.md` — milestone feature definition for
  state-aware next-step guidance and agent-first guidance.
- `.planning/research/ARCHITECTURE.md` — recommended operator UX response shape
  and suggested build order that explicitly reserves Phase 24 for next-step UX
  consolidation.
- `.planning/research/PITFALLS.md` — anti-patterns around orchestration-heavy
  verbosity and the need to compress default replies.

### Public surfaces and runtime anchors
- `README.md` — current public `Start -> Inspect -> Continue` playbook and the
  existing operator wording that Phase 24 should consolidate into a stronger
  runtime answer.
- `skills/rd-agent/SKILL.md` — current public routing contract, concise routing
  field list, blocked-path guidance, and minimum-start language.
- `skills/rd-tool-catalog/SKILL.md` — locked downshift boundary showing that
  lower-level detail is subordinate to the high-level surface.
- `v3/entry/rd_agent.py` — current runtime source of `current_state`,
  `routing_reason`, `exact_next_action`, `recommended_next_skill`, blocked
  fields, and paused-run/new-run routing wording.
- `v3/contracts/preflight.py` — canonical blocked/executable truth contract
  reused by routing and stage entry.
- `v3/orchestration/preflight_service.py` — exact blocker and repair-action
  truth that the new UX layer must not weaken.
- `v3/orchestration/resume_planner.py` — current recovery/continuation wording
  that Phase 24 may need to harmonize with the new operator phrasing.

### Verification anchors
- `tests/test_phase22_intent_routing.py` — current assertions for concise
  routing fields and paused-run recommendation behavior.
- `tests/test_phase23_preflight_service.py` — canonical blocked/executable
  truth and repair-action assertions.
- `tests/test_phase23_stage_preflight_integration.py` — proof that blocked
  routing keeps `recommended_next_skill` visible and that stage entrypoints do
  not claim executability ahead of canonical preflight truth.
- `tests/test_phase21_public_surface_narrative.py` — regression lock for the
  inspect-first public narrative that the new UX layer should preserve.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `v3/entry/rd_agent.py` already centralizes the paused-run and new-run
  operator response fields, making it the most likely integration point for the
  Phase 24 next-step UX consolidation.
- `v3/contracts/preflight.py` and `v3/orchestration/preflight_service.py`
  already provide canonical blocked/executable truth, blocker categories, and
  repair actions; Phase 24 should reuse these directly instead of inventing a
  softer UX-only truth path.
- `v3/orchestration/resume_planner.py` already turns recovery truth into
  operator-facing continuation messages, so it is a likely harmonization point
  when aligning stage-entry wording with the new top-level UX.
- `skills/rd-agent/SKILL.md` and the stage-skill contracts already encode the
  minimum start/continuation field language that can feed the new minimal
  skeleton outputs.

### Established Patterns
- Public runtime truth in this repo is expected to come from structured payloads
  and persisted snapshots, not from prose-only heuristics.
- Default operator replies are already expected to be concise and to expose the
  four routing fields explicitly.
- High-level skills remain the default surface; downshift tooling is only for
  the cases where the high-level boundary is insufficient.
- Tests in this repo favor deterministic structured assertions plus targeted
  human-readable text checks, not snapshot-heavy golden output files.

### Integration Points
- Planning should assume cross-cutting work across `rd_agent`, resume/continue
  wording, README-aligned operator language, and regression coverage; this is
  not just a string touch-up in one file.
- The next-step UX likely needs one shared formatting layer or response
  composer so paused-run routing, start-new-run advice, and blocked stage-entry
  messages do not drift apart.
- Minimal start and continuation skeleton generation should reuse the already
  locked skill-contract field names rather than inventing a second contract
  vocabulary.

</code_context>

<deferred>
## Deferred Ideas

- A unified multi-run or multi-branch progress dashboard belongs to a later
  phase.
- Machine-readable or semi-automated environment repair flows belong to a later
  remediation-focused phase.
- A separate cross-run progress center or operator console beyond the current
  high-level surfaces belongs to future pipeline UX work.

</deferred>

---

*Phase: 24-operator-guidance-and-next-step-ux*
*Context gathered: 2026-03-22*
