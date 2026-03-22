# Phase 20: Stage Skill Execution Contracts - Research

**Researched:** 2026-03-22
**Domain:** standalone V3 stage-skill execution contracts
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Deferred Ideas (OUT OF SCOPE)
- Removing `rd-tool-catalog` from the public surface entirely belongs to a
  later public-surface phase.
- README-level public-surface narrative work belongs to Phase 21.
- Any new orchestration helper that auto-fills state beyond existing public
  contracts belongs to a later behavior phase rather than this guidance phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SKILL-01 | Developer can start `rd-agent` from the skill package with an explicit minimal-input contract that names the required run fields and the required stage payload fields. | Put the literal start fields from `RunStartRequest` and `SkillLoopService` into `skills/rd-agent/SKILL.md`, with a strict minimal contract section separate from the richer recommended multi-branch example. |
| SKILL-02 | Developer can understand the default `rd-agent` gated behavior, including that `gated + max_stage_iterations=1` pauses after the first completed stage for operator review. | Translate `ExecutionMode.GATED`, `max_stage_iterations`, and the current pause behavior from `execution_policy.py` and its tests into plain-language skill guidance that says the current step completes, then the run pauses for review while the next step is prepared. |
| SKILL-03 | Developer can continue from a paused `rd-agent` run by following stage-skill guidance that states the exact identifiers and payload fields needed for `rd-propose`, `rd-code`, `rd-execute`, and `rd-evaluate`. | Document one shared continuation skeleton across the four stage skills, then add exact per-skill differences from `rd_execute` and `rd_evaluate`, while keeping missing-field handling agent-led and explicit. |
</phase_requirements>

## Summary

Phase 20 is a skill-guidance and regression phase, not an orchestration-change
phase. The underlying public contracts already exist: `RunStartRequest` defines
the run-level start fields, the stage entrypoints define the exact continuation
fields, `SkillLoopService` shows the shared continuation skeleton, and
`execution_policy.py` plus its tests define the pause semantics. The product
gap is that the current `skills/rd-*.md` files still stop at routing advice and
do not surface those contracts in an operator-usable way.

The safest implementation seam is the skill packages themselves plus focused
doc-surface regressions. The skill docs already have stable headings like
`When to use`, `Failure handling`, and `Success contract`, so Phase 20 can
harden the existing packages instead of inventing a second doc format or
touching orchestration code. The repo currently lacks dedicated tests that read
`skills/rd-agent/SKILL.md` and the four stage-skill docs for contract strings,
which means the new execution guidance would drift unless this phase adds
purpose-built file-reading tests.

**Primary recommendation:** implement Phase 20 in two slices:
1. Harden `skills/rd-agent/SKILL.md` with an explicit two-layer start contract,
   plain-language pause semantics, and a focused regression file.
2. Harden `skills/rd-propose`, `skills/rd-code`, `skills/rd-execute`, and
   `skills/rd-evaluate` with one shared continuation skeleton, exact
   stage-specific deltas, agent-led missing-field guidance, and a second
   regression file for continuation contracts.

## Current Surface Findings

### Finding 1: The skill packages already expose the right public seam
- `skills/rd-agent/SKILL.md` and the four stage skills already act as the
  operator-facing wrappers for `v3.entry.*`.
- They already contain sections for trigger requests, routing boundaries,
  failure handling, and success contracts.
- This means Phase 20 can harden an existing public surface instead of
  introducing a new handbook, README appendix, or hidden reference doc.

### Finding 2: The exact start-field truth is already centralized
- `v3/contracts/tool_io.py` defines `RunStartRequest` with the literal fields
  `title`, `task_summary`, `scenario_label`, `initial_branch_label`,
  `execution_mode`, and `max_stage_iterations`.
- `v3/entry/rd_agent.py` shows that `rd-agent` also needs `stage_inputs`, and
  `SkillLoopService._run_stage()` proves that the minimal usable stage payload
  for the first step is `summary` plus `artifact_ids`.
- No new schema discovery is needed; the skill package just needs to name these
  fields explicitly.

### Finding 3: The current pause behavior is precise and test-backed
- `v3/orchestration/execution_policy.py` is the source of truth for how
  `gated` and `max_stage_iterations` behave.
- In gated mode, the code pauses after a completed step and sets
  `stop_reason=awaiting_operator`.
- `tests/test_phase14_execution_policy.py` proves the next step is created in a
  ready state before the pause is persisted.
- This is an operator-usable story already; the gap is translation into plain
  language rather than additional runtime work.

### Finding 4: The four continue skills share a real common skeleton
- `rd_propose`, `rd_code`, `rd_execute`, and `rd_evaluate` all require
  `run_id`, `branch_id`, `summary`, and `artifact_ids`.
- `rd_execute` alone adds `blocking_reasons`.
- `rd_evaluate` alone adds `recommendation` with the exact public values
  `continue` or `stop`.
- `SkillLoopService._run_stage()` confirms this shared shape and is the best
  place to anchor the shared continuation contract in planning.

### Finding 5: Resume outcomes are already public and should inform doc wording
- The stage entrypoints surface `decision.disposition` values such as reuse,
  review, and replay, and `rd_execute` also surfaces blocked vs completed
  outcomes.
- `tests/test_phase14_resume_and_reuse.py` proves these paths are not edge
  cases; they are normal public outcomes.
- Phase 20 guidance should therefore explain what the operator or agent should
  do after reuse, review, replay, or blocked results instead of pretending all
  continuations are simple happy paths.

### Finding 6: There are currently no focused skill-doc contract tests
- Existing Phase 17/18/19 public-surface tests focus on README, tool catalog,
  installer behavior, and orchestration/tool payloads.
- Nothing currently fails if a `SKILL.md` drops the required field list,
  removes the pause explanation, or stops telling the agent how to handle
  missing identifiers.
- Phase 20 needs dedicated regression files that read the skill docs as the
  product surface being hardened.

## Recommended Patterns

### Pattern 1: Two-layer `rd-agent` contract
**What:** separate the strict minimum start contract from the richer
recommended multi-branch contract.
**Why:** the user explicitly wants the default narrative to foreground
multi-branch work, but the product still needs a truthful minimum.
**Recommended form:** `Required`, `Optional`, `Minimal start`, then
`Recommended multi-branch start`.

### Pattern 2: Plain-language-first operator guidance
**What:** explain the default path as "complete the current step, then pause for
review" before mapping to internal stage names.
**Why:** the user rejected leading with internal terminology like `framing`.
**Where:** especially in `skills/rd-agent/SKILL.md`, with only secondary
mapping to public stage keys when needed.

### Pattern 3: Shared continuation skeleton plus exact deltas
**What:** give one shared list of continuation fields for all four stage
skills, then one exact extra-field section per special case.
**Why:** avoids four near-duplicate contracts while still satisfying SKILL-03.
**Exact deltas:** `rd-execute` adds `blocking_reasons`; `rd-evaluate` adds
`recommendation = continue|stop`.

### Pattern 4: Agent-led field recovery
**What:** high-level skills should say that if a field is missing, the agent
should inspect current run or branch state and surface the exact missing values
or follow-up questions.
**Why:** the user explicitly does not want operators pushed into manual
`rd-tool-catalog` browsing for common continuation cases.
**Boundary:** this is guidance hardening, not new orchestration behavior.

### Pattern 5: File-reading regressions for public skill contracts
**What:** add two Phase 20 pytest files that read `SKILL.md` content directly.
**Why:** this phase is hardening skill packages as a public operator surface,
not only Python functions.
**Recommended split:** one test file for `rd-agent`, one for the four
continuation skills.

## Likely Plan Slices

1. Harden `skills/rd-agent/SKILL.md`
   - add a literal minimum start contract
   - add a recommended multi-branch example
   - add plain-language pause semantics and next-step guidance
   - lock with a dedicated `rd-agent` skill-contract test

2. Harden the four stage-skill packages
   - add one shared continuation skeleton
   - add exact per-skill differences and outcome guidance
   - add agent-led missing-field wording
   - lock with a dedicated stage-skill contract test

## Anti-Patterns to Avoid

- **Schema dump disguised as guidance:** listing every low-level field with no
  operator framing will recreate the original product gap.
- **Internal-jargon-first writing:** leading with `framing`, `verify`, or
  `synthesize` before telling the operator what happens in plain language will
  fail the user's stated preference.
- **Manual tool browsing as the default recovery path:** high-level skills
  should not tell the user to go pick tools on their own when the agent can
  inspect current state and answer directly.
- **Behavior creep:** do not modify orchestration code just to make the
  documentation easier to write.
- **README spillover:** broad public-surface narrative work still belongs to
  Phase 21 unless a narrowly scoped mention is absolutely required.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| start-field discovery | a second docs-only schema table | `RunStartRequest` + `rd_agent` + explicit field names in `skills/rd-agent/SKILL.md` | the code already names the contract truth |
| pause semantics | new runtime flags or wrapper helpers | plain-language translation of `execution_policy.py` behavior | Phase 20 is guidance hardening, not runtime redesign |
| stage continuation variance | four unrelated prose contracts | one shared continuation skeleton plus per-skill deltas | minimizes drift and keeps SKILL-03 precise |
| contract drift detection | manual review of docs | focused pytest files that read `SKILL.md` content | this phase hardens skill packages as a product surface |

## Common Pitfalls

### Pitfall 1: Treating the recommended multi-branch path as the minimum contract
**What goes wrong:** the doc foregrounds multi-branch work but never says what
the true minimum start payload is.
**How to avoid:** force the doc and tests to assert both a minimum contract and
a recommended contract.

### Pitfall 2: Explaining `gated + max_stage_iterations=1` incorrectly
**What goes wrong:** the doc implies that both values do the exact same thing
or says only "the run may pause" without a concrete stop point.
**How to avoid:** explain that the current step finishes, then the run pauses
for review, and keep the unattended/iteration-ceiling path as contrast only.

### Pitfall 3: Omitting reuse/review/replay/blocked outcomes
**What goes wrong:** the stage-skill docs read as if every continue action is a
simple success path.
**How to avoid:** explicitly mention these public outcomes and the next action
the agent should take after each one.

### Pitfall 4: Missing-field guidance that still makes the user do the work
**What goes wrong:** the doc says "ask for run_id" but does not tell the agent
to inspect current state or surface the likely value.
**How to avoid:** make agent initiative a literal contract line and test for it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=7.4.0` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q` |
| Full suite command | `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q` |
| Estimated runtime | ~20 seconds |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 | `rd-agent` names the exact minimum start fields and a richer recommended path | doc-surface/unit | `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py -q` | `tests/test_phase20_rd_agent_skill_contract.py` ❌ Wave 0 |
| SKILL-02 | `rd-agent` explains the default "complete one step, then pause for review" behavior in plain language and ties it to the actual public stop semantics | doc-surface/unit + behavior anchor | `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase20_rd_agent_skill_contract.py -q` | `tests/test_phase14_execution_policy.py` ✅ / `tests/test_phase20_rd_agent_skill_contract.py` ❌ Wave 0 |
| SKILL-03 | the four stage-skill packages name the exact continuation identifiers, shared fields, and stage-specific extras | doc-surface/unit + behavior anchor | `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase20_stage_skill_contracts.py -q` | `tests/test_phase14_resume_and_reuse.py` ✅ / `tests/test_phase14_stage_skills.py` ✅ / `tests/test_phase20_stage_skill_contracts.py` ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q`
- **Per wave merge:** `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase20_rd_agent_skill_contract.py tests/test_phase20_stage_skill_contracts.py -q`
- **Before phase verification:** full suite above must be green

### Wave 0 Requirements
- [ ] `tests/test_phase20_rd_agent_skill_contract.py` — new regression file for `rd-agent` minimum-input and pause semantics
- [ ] `tests/test_phase20_stage_skill_contracts.py` — new regression file for the four continuation skill packages

### Manual-Only Verifications
All targeted Phase 20 behaviors can be guarded with automated file-reading and
existing behavior-anchor tests; no manual-only checks are required.
