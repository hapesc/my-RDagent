# Phase 24: Operator Guidance and Next-Step UX - Research

**Researched:** 2026-03-22
**Domain:** Shared operator-facing next-step guidance for standalone V3 routing
and stage outcomes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### State summary framing
- Default state summaries should be human-first while still preserving
  canonical identifiers such as `run_id` and `branch_id`.
- Paused work should read like "implementation stage (`build`)" or
  "verification stage (`verify`)" rather than exposing raw stage keys alone.
- New-run answers should read like an operator assistant first and only then
  append the canonical route truth such as `start_new_run`.

### Next action must be minimally executable
- Default `exact_next_action` should point to the minimum executable next move,
  not only an abstract direction or only a skill name.
- When continuation inputs are incomplete, the answer should give a minimal
  continuation skeleton that helps the operator fill missing fields.
- When the recommendation is blocked, the answer should include both the repair
  action and the continuation target after repair.

### Blocked responses prioritize the executable repair step
- Blocked guidance must keep `recommended_next_skill` visible, but the first
  emphasis should be the current executable repair step.
- Default blocked order is:
  current state -> recommended path -> not currently executable -> repair ->
  continue target after repair.
- Repair language should be hard-gated, not optimistic.

### Detail expansion stays selective
- Extra detail should auto-expand only when work is blocked or when
  continuation fields are missing.
- A healthy paused run should not dump a continuation skeleton by default.
- A new-run answer should include a one-line minimum start skeleton by default.

### Deferred Ideas (OUT OF SCOPE)
- Multi-run or multi-branch dashboards
- Semi-automated environment repair flows
- A separate operator console beyond the current skill and CLI surfaces
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIDE-05 | User can ask what to do next and receive a concise answer that states the current state, the reason for the recommendation, and the exact next action without requiring orchestration jargon. | Add one shared operator-guidance layer that consumes canonical state and preflight truth, emits the same three-part answer across routing and stage outcomes, and only expands into commands or skeletons when the user is blocked or needs minimum executable detail. |
</phase_requirements>

## Summary

Phase 24 is not another truth-engine phase. Phase 22 already added concise
route fields and Phase 23 already hardened canonical blocked-vs-executable
truth. The remaining gap is translation quality: the repo still exposes that
truth through multiple inconsistent surfaces. `route_user_intent()` returns
field-oriented guidance, but its summaries are still too raw and it does not
offer minimum executable payloads. The four stage entrypoints already respect
preflight truth, but their blocked and completed text still reads like narrow
stage wrappers rather than one shared operator answer. Skill docs describe the
exact continuation fields, but runtime code does not yet reuse those field
contracts to generate minimum start or continuation skeletons.

The strongest seam is therefore a shared operator-guidance contract plus a
single builder/composer in `v3/orchestration` that formats:
- human-first state summaries
- recommendation reason
- exact next action
- repair-first blocked guidance
- optional `next_step_detail` and `detail_hint`

That layer should **not** compute new readiness or new state truth. It should
only consume existing canonical truth from:
- `route_user_intent()` paused/new-run selection
- `PreflightService`
- `resume_planner`
- locked skill-contract field names from the public `SKILL.md` files

**Primary recommendation:** implement Phase 24 in two plan slices:
1. Add a shared operator-guidance contract/composer and wire it into
   `route_user_intent()` so the top-level "what next?" answer becomes human,
   concise, and minimally executable.
2. Reuse the same guidance layer across stage entrypoints, shared resume
   wording, and public docs so runtime and public-surface contracts stop
   drifting apart.

## Standard Stack

### Core
| Asset | Version / Source | Purpose | Why Standard |
|------|-------------------|---------|--------------|
| Python | `>=3.11` from `pyproject.toml` | Runtime baseline | Existing Phase 22/23 operator surfaces already run here; Phase 24 should stay inside the same stack. |
| `pydantic` | `[project.dependencies]` in `pyproject.toml` | Typed surface contracts | Existing V3 public contracts already use frozen Pydantic models for structured public truth. |
| `route_user_intent()` | `v3/entry/rd_agent.py` | Current top-level next-step routing surface | It already owns `current_state`, `routing_reason`, `exact_next_action`, and `recommended_next_skill`. |
| `PreflightService` | `v3/orchestration/preflight_service.py` | Canonical blocked/executable truth | Phase 24 must format this truth, not reinterpret it. |
| Stage skill docs | `skills/rd-*.SKILL.md` | Public source of exact start/continue fields | These docs already define the minimum field names for start and continuation skeletons. |

### Supporting
| Asset | Source | Purpose | When to Use |
|------|--------|---------|-------------|
| `resume_planner` | `v3/orchestration/resume_planner.py` | Shared reuse/review/replay/completed wording | Harmonize it once the shared operator-guidance layer exists. |
| Stage entrypoints | `v3/entry/rd_propose.py`, `rd_code.py`, `rd_execute.py`, `rd_evaluate.py` | Runtime stage outcome text + structured content | Reuse the same guidance contract for blocked, review, replay, and completed outcomes. |
| `README.md` | Public narrative | Public explanation of the operator path | Update only after runtime guidance shape is stable. |
| Existing tests | `tests/test_phase22_intent_routing.py`, `tests/test_phase23_stage_preflight_integration.py`, `tests/test_phase21_public_surface_narrative.py` | Regression anchors | Extend these instead of inventing snapshot-heavy golden output files. |

## Current Surface Findings

### Finding 1: `route_user_intent()` has the right fields but the wrong presentation layer
- The function already exposes:
  `current_state`, `routing_reason`, `exact_next_action`,
  `recommended_next_skill`, and preflight-blocked fields.
- The summary still defaults to raw phrasing such as
  `paused run run-001 on branch branch-001 is at build`.
- It does not yet emit a minimum start skeleton for new runs or a reusable
  detail hint / detail payload contract.

### Finding 2: Blocked stage entry text is truthful but not operator-shaped
- `rd_propose`, `rd_code`, `rd_execute`, and `rd_evaluate` all block before
  state mutation when preflight fails.
- Their blocked text is currently a single stage-scoped sentence like
  `/rd-code is currently blocked by dependency: ... Repair action: ...`
- That satisfies truth, but it does not match the Phase 24 decision to lead
  with current state, preserve the recommended path, and front-load the
  currently executable repair step.

### Finding 3: The repo has no shared contract for next-step UX
- Routing returns one ad hoc dict shape.
- Stage entrypoints return per-entrypoint `structuredContent` plus freeform
  text.
- `resume_planner` returns decision messages in its own tone.
- Without one shared guidance model/builder, Phase 24 will devolve into string
  patching and drift immediately.

### Finding 4: Skill docs already define the exact payload fields Phase 24 needs
- `skills/rd-agent/SKILL.md` locks the minimum start fields:
  `title`, `task_summary`, `scenario_label`,
  `stage_inputs.framing.summary`,
  `stage_inputs.framing.artifact_ids`.
- Stage skill docs lock the continuation skeleton:
  `run_id`, `branch_id`, `summary`, `artifact_ids`.
- `rd-execute` adds `blocking_reasons`; `rd-evaluate` adds `recommendation`.
- Phase 24 should reuse these exact field names when generating minimum
  skeletons rather than inventing a second vocabulary.

### Finding 5: The detail-expansion rules need explicit state-based triggers
- The context says healthy paused runs should stay terse.
- New-run answers should include a start skeleton by default.
- Blocked or incomplete continuation answers should auto-expand one layer.
- No existing runtime helper centralizes those rules, so each surface would
  otherwise have to reinvent them.

### Finding 6: This is not a frontend/UI component phase despite the word "UX"
- The work is on operator-language payloads, shared response shaping, and doc
  alignment inside Python entrypoints and markdown skill/docs surfaces.
- There is no browser, component, or layout implementation here.
- A frontend-style UI-SPEC would be noise rather than guidance for this phase.

## Recommended Architecture Patterns

### Pattern 1: Add one shared `OperatorGuidance` contract
**What:** Add a new contract module such as
`v3/contracts/operator_guidance.py` with a frozen Pydantic model that carries
the operator-facing guidance fields used across surfaces.

**Recommended field family:**
- `current_state`
- `routing_reason`
- `exact_next_action`
- `recommended_next_skill`
- `current_action_status`
- `current_blocker_category`
- `current_blocker_reason`
- `repair_action`
- `next_step_detail`
- `detail_hint`

**Why:** Phase 24 is fundamentally about keeping multiple public surfaces on
the same answer shape.

### Pattern 2: Use one shared builder/composer, not per-entrypoint prose
**What:** Add a shared builder module under `v3/orchestration`, for example
`v3/orchestration/operator_guidance.py`, that accepts canonical truth inputs
and produces one `OperatorGuidance` result.

**It should accept inputs such as:**
- route kind (`start_new_run`, `continue_paused_run`, downshift)
- run / branch / stage identity
- preflight truth
- current or next stage skill
- whether minimum-detail expansion is required

**Why:** this phase fails if `rd_agent`, `resume_planner`, and the four stage
entrypoints all phrase "what next?" independently.

### Pattern 3: Keep truth computation separate from guidance formatting
**What:** The shared guidance layer should never decide whether the work is
blocked or executable. That remains the job of Phase 22 routing logic and Phase
23 preflight truth.

**Recommended rule:**
- routing chooses the ideal path
- preflight decides blocked vs executable
- operator guidance decides how to present that truth

**Why:** Phase 24 is translation, not a second truth source.

### Pattern 4: Encode stage labels and skeleton templates explicitly
**What:** Add one explicit stage-label mapping and one explicit set of minimum
payload templates.

**Recommended stage-label mapping:**
- `framing` -> `framing stage (`framing`)`
- `build` -> `implementation stage (`build`)`
- `verify` -> `verification stage (`verify`)`
- `synthesize` -> `synthesis stage (`synthesize`)`

**Recommended minimum payload templates:**
- start:
  `title="..."`, `task_summary="..."`, `scenario_label="..."`,
  `stage_inputs.framing.summary="..."`,
  `stage_inputs.framing.artifact_ids=["artifact-plan-001"]`
- continue:
  `run_id="run-001"`, `branch_id="branch-001"`, `summary="..."`,
  `artifact_ids=["artifact-001"]`
- verify blocked:
  add `blocking_reasons=["..."]`
- synthesize:
  add `recommendation="continue"` or `recommendation="stop"`

**Why:** exact field names are already a public contract. Reusing them keeps
runtime guidance aligned with skill docs.

### Pattern 5: Progressive disclosure must be state-driven
**What:** The builder should choose detail expansion from state, not from
entrypoint preference.

**Recommended rule set:**
- new run: emit `next_step_detail` with minimum start skeleton
- healthy paused run: emit `detail_hint`, but keep `next_step_detail` empty
- blocked path: emit `next_step_detail` when repair or continuation needs one
  minimum actionable command/skeleton
- missing continuation fields: emit `next_step_detail` with placeholders for
  unresolved values

**Why:** this matches the user-locked "only expose deeper mechanics when
needed" rule.

### Pattern 6: Harmonize stage outcomes with the same 3-part answer
**What:** Stage entrypoints and `resume_planner` should adopt the same operator
shape as routing:
1. current state
2. reason
3. next action

**For blocked stage entry:**
- keep the stage skill visible
- explicitly say it is not executable now
- front-load the repair step
- keep the after-repair continuation target

**Why:** otherwise the user gets a clean answer from `rd-agent` and a totally
different voice from `rd-code` or `rd-execute`.

## Anti-Patterns to Avoid

- **Do not patch strings independently in each entrypoint.** That creates
  immediate drift across route and stage surfaces.
- **Do not compute a second readiness truth.** `PreflightService` already owns
  blocked vs executable truth.
- **Do not hide canonical IDs completely.** The user asked for less jargon, not
  unverifiable prose.
- **Do not always dump full payload skeletons.** Healthy paused work should stay
  terse.
- **Do not treat this as a browser-UI phase.** No component library or UI-SPEC
  work is needed here.

## Likely Plan Slices

1. **Shared operator-guidance contract + route surface integration**
   - add a typed `OperatorGuidance` model
   - add one shared builder/composer
   - wire `route_user_intent()` to the new guidance layer
   - add focused tests for mixed state summaries, blocked ordering, start
     skeletons, and selective detail expansion

2. **Stage outcome and public-surface alignment**
   - reuse the same guidance contract in `rd_propose`, `rd_code`,
     `rd_execute`, `rd_evaluate`, and `resume_planner`
   - keep blocked stage entry responses repair-first and recommendation-aware
   - align `README.md` and `skills/rd-agent/SKILL.md` with the new runtime UX
   - add cross-surface tests for stage outcome guidance and doc/runtime
     alignment

## Validation Architecture

### Test Strategy
- **Route-focused layer:** add `tests/test_phase24_operator_guidance.py` to
  cover:
  human-first + canonical-id mixed summaries,
  blocked response ordering,
  new-run minimum start skeletons,
  and healthy paused-run detail hints without automatic continuation dumps.
- **Stage-guidance integration layer:** add
  `tests/test_phase24_stage_next_step_guidance.py` to cover:
  blocked stage-entry operator guidance,
  completed/review/replay next-step phrasing,
  and alignment between stage outcomes and the shared guidance contract.
- **Regression reuse:** keep Phase 20, 21, 22, and 23 gates in the phase suite
  so Phase 24 cannot improve wording by regressing contract truth, public docs,
  or preflight semantics.

### Recommended Commands
- **Quick gate:** `uv run python -m pytest tests/test_phase24_operator_guidance.py -q`
- **Wave gate:** `uv run python -m pytest tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -q`
- **Full phase gate:** `uv run python -m pytest tests/test_phase14_stage_skills.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase21_public_surface_narrative.py tests/test_phase22_intent_routing.py tests/test_phase23_stage_preflight_integration.py tests/test_phase24_operator_guidance.py tests/test_phase24_stage_next_step_guidance.py -q && uv run lint-imports`

### Feedback Targets
- quick loop under ~10 seconds on the route-guidance suite
- wave loop under ~20 seconds
- no task should go three commits without either a route-guidance or
  stage-guidance automated gate

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| next-step UX | one-off strings inside each `rd_*` entrypoint | one shared `OperatorGuidance` contract + builder | keeps the public answer shape consistent |
| blocked truth | a second readiness heuristic | `PreflightService` inputs reused by the guidance builder | avoids conflicting sources of truth |
| continuation skeletons | ad hoc placeholder prose | exact field names already locked in `skills/rd-agent/SKILL.md` and stage skill docs | preserves contract alignment |
| public narrative | README-only polish disconnected from runtime | runtime changes first, README / `SKILL.md` updates second | prevents doc/runtime drift |

## Common Pitfalls

### Pitfall 1: Solving Phase 24 as doc polish only
**What goes wrong:** README or `SKILL.md` wording improves, but runtime payloads
still expose raw or inconsistent next-step answers.
**Why it fails:** `GUIDE-05` is a runtime answer requirement, not only a docs
requirement.

### Pitfall 2: Hiding canonical truth to reduce jargon
**What goes wrong:** the answer becomes friendlier but drops `run_id`,
`branch_id`, or the stage key completely.
**Why it fails:** the user loses verifiable anchors and downstream guidance can
no longer point precisely to the current state.

### Pitfall 3: Always dumping payload details
**What goes wrong:** every paused-run answer expands into a full continuation
payload even when the work is healthy and obvious.
**Why it fails:** it recreates the orchestration-heavy verbosity Phase 24 is
supposed to remove.

### Pitfall 4: Repair text without the continuation target
**What goes wrong:** blocked answers tell the user how to repair the system but
stop saying which skill or path will be correct afterward.
**Why it fails:** the operator still needs the intended post-repair route.

### Pitfall 5: Treating "UX" as a frontend signal
**What goes wrong:** planning drifts into browser/UI artifacts or a visual
design contract.
**Why it fails:** this phase is about operator-language response surfaces inside
the existing skill and CLI product, not about a browser interface.

---
_Research completed: 2026-03-22_
