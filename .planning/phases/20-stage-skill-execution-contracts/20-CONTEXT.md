# Phase 20: Stage Skill Execution Contracts - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the existing standalone stage-skill surface executable from
the skill packages alone. It covers explicit start and continue contracts for
`rd-agent`, `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`, plus
clear default pause/continue semantics and next-step guidance. It does not add
new orchestration behavior, new state semantics, or a new routing layer beyond
the already-locked skills-plus-CLI surface.

</domain>

<decisions>
## Implementation Decisions

### `rd-agent` start contract
- High-level skill contracts must stay easy to use; Phase 20 should not dump
  low-level contract complexity directly onto the operator.
- The default narrative and main example for `rd-agent` should show the
  recommended multi-branch path rather than a single-branch-only story.
- Even though the main example is multi-branch, the skill must still state the
  strict minimal start contract separately so the operator can see the true
  minimum required fields without reverse-engineering the larger example.
- The strict minimal start contract must name fields explicitly, not only by
  prose category.
- The minimum start contract for `rd-agent` must call out:
  `title`, `task_summary`, `scenario_label`,
  `stage_inputs.framing.summary`, and
  `stage_inputs.framing.artifact_ids`.
- `branch_hypotheses` should be treated as part of the recommended
  multi-branch start path, not hidden as an afterthought.
- The contract presentation format should be:
  `Required` fields, `Optional` fields, then a minimal executable example.

### Default stop/continue semantics
- Phase 20 should describe the default behavior in plain operator language
  rather than leading with internal stage jargon.
- The default behavior should be explained concretely as:
  complete the current step, then pause for human review before continuing.
- The guidance should explicitly say that the next step is prepared but is not
  continued automatically.
- The skill guidance should explain the difference between:
  the default "do one step and pause" path and the more continuous unattended
  path, while keeping the pause-after-review path as the primary explanation.
- The wording must remain truthful to the actual defaults in code, but it
  should avoid unnecessary internal terminology in the main operator path.

### Continue contracts for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`
- The four continue skills should share one common input skeleton rather than
  four unrelated explanations.
- That shared skeleton must explicitly name the common required continuation
  fields in operator language:
  run identifier, branch identifier, current-step summary, and current-step
  artifact identifiers.
- Each skill must then list its stage-specific additions explicitly:
  `rd-execute` adds blocking reasons when the verification step cannot pass,
  and `rd-evaluate` adds the required continue-or-stop decision.
- Every stage skill must say that if required fields are missing, the agent
  must stop and ask for them rather than guessing.
- High-level skills should actively keep the contract lightweight: when a field
  is complex or awkward, the skill should tell the operator exactly what field
  is missing, what shape it should have, and what value can already be derived
  from the current run or branch state.

### Follow-up guidance and agent initiative
- Successful outcomes should point to the next recommended high-level action
  explicitly instead of saying only "continue".
- Reuse, review, replay, and blocked outcomes should each have distinct
  next-step guidance rather than being collapsed into one vague fallback.
- `rd-tool-catalog` should remain part of the existing public surface, but
  Phase 20 guidance should treat it as an agent-side escalation path rather
  than something the operator is expected to drive manually.
- When a high-level skill lacks enough context, the agent should proactively
  inspect current run or branch state and proactively surface the missing
  identifiers or values to the operator.
- The skill guidance should prefer:
  the agent checks state, identifies the right next action, and presents it,
  over telling the operator to browse tools and decide alone.

### Claude's Discretion
- The exact heading names and example payload formatting may be decided during
  planning as long as the locked field names, plain-language semantics, and
  agent-initiative behavior remain intact.
- Planning may decide whether the minimal contract and recommended
  multi-branch contract appear in one section or two, as long as both are
  explicit and cannot be confused with each other.

</decisions>

<specifics>
## Specific Ideas

- Avoid opening the main operator explanation with internal labels such as
  `framing`; start with plain-language descriptions of "the current step" and
  "the next step", then optionally map those to the internal stage names.
- Treat the operator-facing contract as two layers:
  the strict minimum needed to start or continue, and the recommended richer
  path the agent should normally drive.
- If the agent can inspect the current environment to discover a run ID, branch
  ID, or existing artifact IDs, it should do that proactively and present the
  result instead of asking the operator to hunt through state blindly.
- Keep the user on the high-level skill path; when lower-level inspection is
  necessary, the agent should use `rd-tool-catalog` or concrete tools in the
  background and return the answer.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and milestone truth
- `.planning/PROJECT.md` — v1.2 milestone goal, active operator-usability
  requirement, and the constraint that this phase hardens guidance rather than
  rebuilding orchestration.
- `.planning/ROADMAP.md` — Phase 20 boundary and success criteria for explicit
  start, pause, and continue contracts.
- `.planning/REQUIREMENTS.md` — `SKILL-01`, `SKILL-02`, and `SKILL-03`, which
  define the required operator-facing skill-contract outcomes.
- `.planning/STATE.md` — current milestone sequencing and the reminder that
  Phase 20 must preserve the completed Phase 19 surface.

### Prior phase decisions that still apply
- `.planning/phases/17-skill-and-cli-surface-terminology-convergence/17-CONTEXT.md`
  — locked decisions on skill-first routing, public surface truth, and keeping
  `rd-agent` as the primary high-level entrypoint.
- `.planning/phases/18-standalone-packaging-and-planning-autonomy/18-CONTEXT.md`
  — locked decisions on repo-local skills, public-vs-internal doc boundaries,
  and keeping the standalone surface self-contained.
- `.planning/phases/19-tool-catalog-operator-guidance/19-CONTEXT.md` — locked
  decisions on structured guidance, follow-up semantics, and keeping direct
  tools subordinate to the high-level skill path.

### Skill-package implementation anchors
- `skills/rd-agent/SKILL.md` — current `rd-agent` contract that needs explicit
  minimal start inputs and clearer pause semantics.
- `skills/rd-propose/SKILL.md` — current continue contract for the first
  step-specific skill.
- `skills/rd-code/SKILL.md` — current continue contract for the implementation
  step-specific skill.
- `skills/rd-execute/SKILL.md` — current continue contract for the verification
  step-specific skill, including the blocked-path branch.
- `skills/rd-evaluate/SKILL.md` — current continue contract for the summary and
  continue-or-stop decision.
- `skills/rd-tool-catalog/SKILL.md` — existing routing boundary that should
  stay available but move into the background for high-level skill flows.

### Contract and orchestration truth
- `v3/contracts/tool_io.py` — source of truth for `RunStartRequest`,
  stage-write request fields, and the public request contracts that the skill
  guidance must name explicitly.
- `v3/entry/rd_agent.py` — actual `rd-agent` start signature, defaults, and
  multi-branch vs single-branch behavior.
- `v3/entry/rd_propose.py` — actual required fields and outcomes for the first
  continue skill.
- `v3/entry/rd_code.py` — actual required fields and outcomes for the build
  continue skill.
- `v3/entry/rd_execute.py` — actual required fields and the blocked-path
  continuation behavior.
- `v3/entry/rd_evaluate.py` — actual required fields and the continue-or-stop
  recommendation behavior.
- `v3/orchestration/skill_loop_service.py` — shared continuation skeleton and
  per-step payload differences used by the high-level loop.
- `v3/orchestration/execution_policy.py` — source of truth for the pause,
  unattended, and iteration-ceiling semantics that must be explained in plain
  language.

### Verification anchors
- `tests/test_phase14_skill_agent.py` — current proof of the single-branch
  `rd-agent` loop contract and payload expectations.
- `tests/test_phase14_stage_skills.py` — current proof of stage-write behavior,
  replay behavior, and blocked verification semantics.
- `tests/test_phase14_execution_policy.py` — current proof of default pause
  behavior, operator-review stop reason, and unattended iteration ceilings.
- `tests/test_phase16_rd_agent.py` — current proof of the multi-branch
  `rd-agent` path that the new guidance intends to foreground.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/rd-agent/SKILL.md` and the four stage-skill `SKILL.md` files already
  provide a shared structure with trigger requests, when-to-use guidance, and
  failure handling; Phase 20 can harden these instead of inventing a new skill
  template.
- `v3/contracts/tool_io.py` already centralizes the public request-field truth,
  so the skill packages can name concrete fields without duplicating private
  implementation details.
- `v3/orchestration/skill_loop_service.py` already reveals a clean shared
  continuation skeleton:
  summary + artifact IDs for every step, plus special fields only for
  verification blocking and continue-or-stop decisions.
- `v3/orchestration/execution_policy.py` already encodes the exact pause and
  unattended semantics, giving planning a precise truth source for operator
  wording.

### Established Patterns
- High-level skills remain the primary operator surface; direct tools are a
  secondary layer used when the high-level boundary is insufficient.
- Public surface contracts are locked with explicit regression tests rather than
  loose prose, so Phase 20 should probably add targeted assertions for new
  guidance fields and language.
- Entry-point functions validate concrete required fields and fail fast when the
  state relationship is invalid; the skill guidance should mirror that
  precision.
- Current skill docs already have `When to use`, `When not to use`, and
  `Failure handling` sections, so the most natural place to add explicit
  contracts is within that existing structure.

### Integration Points
- Planning will need to update all five public `rd-*` skill packages together
  so the common continuation skeleton and default pause story stay consistent.
- Any new contract wording should stay aligned with Phase 19 follow-up
  semantics so a paused `rd-agent` result and a stage-skill next step do not
  contradict each other.
- Regression coverage will likely need to read both skill docs and the current
  code-level contract truth so guidance cannot drift away from the actual field
  names or pause behavior.

</code_context>

<deferred>
## Deferred Ideas

- Any attempt to remove `rd-tool-catalog` from the public standalone surface
  entirely belongs to a later public-surface phase; Phase 20 only changes how
  high-level skills use or mention it.
- Broader README-level product narration for start, inspect, and continue flows
  belongs to Phase 21.
- Any new orchestration convenience features that auto-fill state without
  existing public contracts belong to a later phase if they require code-level
  behavior changes rather than guidance hardening.

</deferred>

---

*Phase: 20-stage-skill-execution-contracts*
*Context gathered: 2026-03-22*
