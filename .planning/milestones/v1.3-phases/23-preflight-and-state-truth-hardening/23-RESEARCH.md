# Phase 23: Preflight and State Truth Hardening - Research

**Researched:** 2026-03-22
**Domain:** Canonical preflight truth for standalone V3 stage entry, routing, and
operator-facing readiness/blocker claims
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Preflight must run at the recommendation boundary, not only at execution time
- `rd-agent` should keep recommending the ideal next high-level skill, but it
  must also tell the truth about whether that skill is executable right now.
- Read-only inspect flows should still surface blocker summaries instead of
  implying the paused state is healthy.
- The surface must not use a two-step story where routing says "continue" and
  a later layer reveals that continuation was never executable.

### Executability truth requires all four evidence classes
- Any positive "ready" claim must be backed by:
  1. persisted state consistency
  2. required artifact presence
  3. runtime and dependency readiness
  4. recovery validity
- If a snapshot lists artifact ids but the underlying artifact snapshots are
  missing from V3 state, artifact truth fails.
- If run, branch, and stage snapshots disagree about the current situation,
  the system must block explicitly instead of silently choosing one source.
- If a completed stage would be reused, a persisted recovery assessment must
  already exist; missing recovery truth is a blocker, not a soft success.

### Blocker presentation must stay truthful but operational
- Blockers should stay grouped by the locked categories:
  `runtime`, `dependency`, `artifact`, `state`, and `recovery`.
- The first reply should surface one primary blocker and one concrete repair
  action instead of dumping every failure at once.
- The strongest allowed wording on failure is:
  "the recommended path is X, but X is currently blocked by Y."
- Unknown checks count as failed truth. The surface must not collapse unknown
  into ready.

### Deferred Ideas (OUT OF SCOPE)
- Richer next-step UX polish and progressive disclosure belong to Phase 24.
- Automatic environment repair flows belong to later work.
- Cross-run or cross-branch progress surfaces remain out of scope for this
  phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREFLIGHT-01 | Before stage execution advances state, the pipeline checks required runtime versions and Python dependencies and reports exact missing prerequisites with concrete fix guidance. | Add one canonical preflight service that derives runtime and dependency requirements from repo-owned declarations (`pyproject.toml`, `scripts/setup_env.sh`) and returns blocker categories plus exact repair text before any stage mutation or readiness claim. |
| PREFLIGHT-02 | Before a stage consumes data, artifacts, or state, the pipeline checks that required files and snapshots exist and blocks early with an explicit reason when they do not. | Make preflight validate run/branch/stage snapshot consistency plus artifact snapshot existence before any stage-specific entrypoint reuses or advances state. |
| STATE-01 | User-visible claims such as "next stage ready" are backed by persisted stage snapshots and current handoff artifacts rather than surface prose alone. | Remove unconditional "ready" phrasing from preflight-blind code paths (`resume_planner`, seeded ready summaries, routing replies) and replace it with wording derived from canonical preflight results. |
| STATE-02 | Verification can distinguish "results exist" from "environment is reproducible" and records that difference as a first-class blocked or passed state. | Keep recovery truth separate from runtime/dependency truth, but report both in one preflight result so blocked reproducibility becomes explicit instead of being hidden behind "results already exist." |
</phase_requirements>

## Summary

Phase 23 is a shared-orchestration hardening phase, not a string-polish phase.
The existing code already has strong persisted-state and recovery primitives:
`ArtifactStateStore` is the canonical snapshot reader, `RecoveryService`
evaluates reuse/replay/rebuild semantics, and every public stage entrypoint
already funnels through the same run/branch/stage lookups. The missing piece is
that no single service decides whether the current recommendation is actually
executable now.

The strongest seam is therefore a new canonical preflight layer in
`v3/orchestration`, beside `RecoveryService`, with a small contract module under
`v3/contracts`. That layer should be read-only and deterministic: it reads the
repo-declared environment requirements, the persisted run/branch/stage/artifact
snapshots, and any existing recovery assessment; then it returns one structured
truth result with category-level blockers, a primary blocker, and exact repair
guidance. Routing and stage entrypoints should consume the same result instead
of each inventing their own readiness story.

**Primary recommendation:** implement Phase 23 in two plan slices:
1. Add a canonical `PreflightService` plus focused unit coverage for runtime,
   dependency, artifact, state, and recovery blockers.
2. Wire that service into `rd-agent`, the four stage entrypoints,
   `resume_planner`, and seeded stage summaries so user-visible claims no
   longer outrun preflight truth.

## Standard Stack

### Core
| Asset | Version / Source | Purpose | Why Standard |
|------|-------------------|---------|--------------|
| Python | `>=3.11` from `pyproject.toml` | Baseline runtime requirement | This is the only explicit runtime version contract currently declared by the repo. |
| `uv` | Required by `scripts/setup_env.sh` | Canonical environment/bootstrap command | The setup script already fails if `uv` is missing, so preflight should use the same truth source. |
| `pydantic` | `[project.dependencies]` in `pyproject.toml` | Core repo dependency | This is the only always-on Python dependency declared by the project. |
| `pytest`, `import-linter` | `[project.optional-dependencies].test` plus `scripts/setup_env.sh` | Verification-stage reproducibility gate | Verify/reproducibility claims already depend on these tools, so preflight should not ignore them for verification-oriented flows. |
| `ArtifactStateStore` | `v3/orchestration/artifact_state_store.py` | Canonical snapshot reader/writer | All public state truth already funnels through this boundary. |
| `RecoveryService` | `v3/orchestration/recovery_service.py` | Canonical artifact/recovery truth | Phase 23 should reuse it, not fork a second recovery interpretation. |

### Supporting
| Asset | Source | Purpose | When to Use |
|------|--------|---------|-------------|
| `resume_planner` | `v3/orchestration/resume_planner.py` | Current ready/reuse/review wording | Update it once preflight can prove or block executability. |
| `SkillLoopService` | `v3/orchestration/skill_loop_service.py` | Seeds READY-stage summaries | Replace false-ready summaries with preflight-aware language. |
| `route_user_intent` | `v3/entry/rd_agent.py` | Current paused-run recommendation surface | Keep `recommended_next_skill`, but pair it with preflight blockers when needed. |
| Stage entrypoints | `v3/entry/rd_propose.py`, `rd_code.py`, `rd_execute.py`, `rd_evaluate.py` | Current stage-entry mutation path | Gate state mutation here before replay/complete/block writes. |
| Existing tests | `tests/test_phase14_*`, `tests/test_phase16_rd_agent.py`, `tests/test_phase22_intent_routing.py` | Current truth anchors | Extend these patterns instead of inventing snapshot-heavy golden tests. |

## Current Surface Findings

### Finding 1: Recovery truth exists, but executability truth does not
- `RecoveryService.assess()` already tells V3 whether completed stage evidence
  is reusable, stale, incomplete, or blocked.
- It does not check runtime requirements, dependency presence, or run/branch/
  stage snapshot consistency.
- It also writes an assessment even when the current stage is unfinished, which
  means downstream callers must not treat "assessment exists" as "stage ready."

### Finding 2: `resume_planner` has a false-ready branch today
- When an assessment exists and the stage status is `NOT_STARTED`, `READY`, or
  `IN_PROGRESS`, `plan_resume_decision()` currently says
  "the stage is ready to run" even if the assessment disposition is only
  `review`.
- This is exactly the kind of user-visible truth drift Phase 23 is supposed to
  eliminate.
- A shared preflight result should become the gate for any "ready" wording.

### Finding 3: `SkillLoopService` seeds optimistic READY summaries
- `_ensure_stage_exists()` writes summaries like
  `"Build iteration 1 is ready for /rd-agent."`
- Those summaries are published before any runtime, dependency, artifact, or
  state-consistency checks run.
- The code should still seed the next stage snapshot, but the summary needs to
  stop claiming executability before preflight proves it.

### Finding 4: Routing currently knows the ideal next skill, not the real blocker
- `route_user_intent()` in `v3/entry/rd_agent.py` only inspects a paused-run
  shape plus a coarse `high_level_boundary_sufficient` boolean.
- It has no hook into runtime readiness, dependency state, missing artifacts,
  or persisted recovery evidence.
- Phase 23 should keep `recommended_next_skill` but add a second truth layer:
  whether that recommendation is executable now.

### Finding 5: The stage entrypoints already share the right integration seam
- `rd_propose`, `rd_code`, `rd_execute`, and `rd_evaluate` all load:
  run snapshot, branch snapshot, current stage snapshot, artifact list, and
  recovery assessment before deciding whether to reuse/replay/rebuild/review.
- This is already the canonical preflight input set.
- A shared helper/service can therefore be inserted without redesigning the
  public stage contracts.

### Finding 6: Repo-owned runtime and dependency truth is already declared
- `pyproject.toml` declares `requires-python = ">=3.11"` and the core
  dependency `pydantic`.
- `scripts/setup_env.sh` explicitly requires `uv`, runs `uv sync --extra test`,
  and uses `pytest` / `lint-imports` as verification commands.
- Phase 23 should treat these files as the runtime/dependency truth source
  instead of inventing hidden environment assumptions.

### Finding 7: Artifact/state truth should stay inside `StateStorePort`
- `ArtifactStateStore` keeps latest stage snapshots plus iteration history,
  branch snapshots, artifact snapshots, and persisted recovery assessments.
- This gives Phase 23 one place to prove:
  run/branch ownership,
  branch/current-stage alignment,
  latest-stage vs history alignment,
  artifact existence,
  and recovery assessment presence.
- A second ad hoc filesystem check path would create the exact silent
  canonicalization bug the context forbids.

## Recommended Architecture Patterns

### Pattern 1: Canonical `PreflightService` beside `RecoveryService`
**What:** Add `v3/orchestration/preflight_service.py` plus a lightweight
contract module such as `v3/contracts/preflight.py`.

**Recommended result shape:**
- one top-level readiness state (`executable` or `blocked`)
- `recommended_next_skill`
- `primary_blocker_category`
- `primary_blocker_reason`
- `repair_action`
- category-grouped blocker inventory for:
  `runtime`, `dependency`, `artifact`, `state`, `recovery`
- enough snapshot metadata to show which run/branch/stage was evaluated

**Why:** routing-time and execution-time truth must use one canonical path. If
`rd-agent` and the stage entrypoints each infer readiness differently, Phase 23
fails by design.

### Pattern 2: No silent canonicalization when snapshots disagree
**What:** Preflight should block on any persisted-state ambiguity instead of
choosing a winner silently.

**Minimum mismatch checks to plan for:**
- branch belongs to a different run than the requested run id
- current branch stage does not match the stage the entrypoint is trying to use
- latest stage snapshot on disk disagrees with the matching stage embedded in
  the branch snapshot
- stage lists artifact ids that cannot be loaded from `StateStorePort`
- a completed/reused stage lacks a persisted recovery assessment

**Why:** the context explicitly forbids claiming a canonical source unless the
store already proves it.

### Pattern 3: Fresh execution and reuse must stay distinct
**What:** Preflight should not collapse these cases:
- fresh execution of an incomplete stage
- reuse/replay of a completed stage
- blocked/manual-review stage

**Recommended rule:**
- incomplete stages can still be executable if runtime/dependency/state truth
  passes and the stage is not trying to reuse unpublished artifacts
- completed-stage continuation requires persisted recovery truth
- unknown recovery state on a reuse path is a `recovery` blocker, not a
  successful fallback

**Why:** this is the concrete engineering interpretation of `STATE-02`.

### Pattern 4: Gate state mutation before any stage publish
**What:** Each public stage entrypoint should run canonical preflight before it
calls `rd_stage_replay`, `rd_stage_complete`, or `rd_stage_block`.

**If preflight blocks:**
- return a structured blocked payload with preflight evidence
- do not publish a new stage snapshot
- do not tell the user the stage is ready or proceeding

**If preflight passes:**
- continue through the existing reuse/replay/rebuild/review logic

**Why:** requirements talk about blocking before stage execution advances state,
not after.

### Pattern 5: Recommendation truth must distinguish ideal path vs executable now
**What:** The routing surface should keep the ideal path visible while clearly
separating it from the current executable action.

**Recommended operator shape:**
- current state
- recommended path
- current blocker
- exact repair action
- `recommended_next_skill`

**Why:** the context explicitly says the operator still needs to know the
intended next skill after repair, but the surface must stop implying that the
skill is runnable right now.

### Pattern 6: Replace false-ready language at the source
**What:** Update both:
- `v3/orchestration/resume_planner.py`
- `v3/orchestration/skill_loop_service.py`

**Recommended wording shift:**
- from: "the stage is ready to run"
- to: "the stage is prepared and requires preflight truth before execution"
  or equivalent wording that does not claim readiness before the new service
  passes

**Why:** fixing only the final user reply while leaving persisted summaries and
shared messages optimistic will leak the same bug through another path.

## Anti-Patterns to Avoid

- **Do not add fallback readiness rules.** Missing runtime/dependency or
  missing recovery truth must block, not downgrade to a warning.
- **Do not hide environment truth in ad hoc shell calls scattered across entry
  modules.** One shared service should own the checks and repair guidance.
- **Do not let docs outrun runtime truth.** README and skill wording should only
  be updated after the runtime fields and tests exist.
- **Do not silently infer the canonical snapshot source.** If run/branch/stage
  disagree, the result must say so explicitly.
- **Do not merge all blockers into one opaque string.** The operator needs one
  primary blocker, but the structured payload still needs category fidelity.

## Likely Plan Slices

1. **Core preflight truth layer**
   - add contracts and a `PreflightService`
   - derive runtime/dependency truth from repo-owned declarations
   - validate artifact/state/recovery truth from `StateStorePort`
   - add focused Phase 23 unit tests for each blocker category

2. **Surface integration and truth-language hardening**
   - wire preflight into `rd-agent` and the four stage entrypoints
   - remove false-ready wording from shared orchestration helpers
   - add integration tests for blocked routing, blocked stage entry, and
     truthful readiness/reproducibility messages
   - align README / `skills/rd-agent/SKILL.md` wording with the new runtime
     truth surface

## Validation Architecture

### Test Strategy
- **Unit layer:** add `tests/test_phase23_preflight_service.py` to cover:
  Python-version mismatch, missing `uv`, missing required Python package,
  missing artifact snapshot, run/branch/stage mismatch, and missing persisted
  recovery assessment for completed-stage reuse.
- **Integration layer:** add
  `tests/test_phase23_stage_preflight_integration.py` to cover:
  blocked stage entry before publish,
  truthful blocked routing/recommendation output,
  and the distinction between "results exist" and "environment reproducible."
- **Regression reuse:** keep Phase 14, Phase 16, and Phase 22 suites in the
  phase gate so Phase 23 does not regress existing recovery, execution-policy,
  or intent-routing behavior while hardening the truth layer.

### Recommended Commands
- **Quick gate:** `uv run python -m pytest tests/test_phase23_preflight_service.py -q`
- **Wave gate:** `uv run python -m pytest tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase22_intent_routing.py tests/test_phase23_preflight_service.py tests/test_phase23_stage_preflight_integration.py -q`
- **Full phase gate:** `uv run python -m pytest tests/test_phase14_execution_policy.py tests/test_phase14_resume_and_reuse.py tests/test_phase14_stage_skills.py tests/test_phase16_rd_agent.py tests/test_phase22_intent_routing.py tests/test_phase23_preflight_service.py tests/test_phase23_stage_preflight_integration.py -q && uv run lint-imports`

### Feedback Targets
- quick loop under ~10 seconds on the focused service suite
- wave loop under ~25 seconds
- no task should go three commits without an automated preflight-related gate

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| environment truth | ad hoc shell checks spread across `rd_*` modules | one shared preflight service reading `pyproject.toml` and `scripts/setup_env.sh` | keeps runtime/dependency rules consistent |
| artifact truth | raw filesystem existence checks outside the state store | `StateStorePort` artifact/stage/recovery reads | public truth already lives there |
| readiness wording | one-off string patches in entrypoints only | shared preflight result + resume/skill-loop wording updates | prevents surface drift |
| blocked guidance | vague "inspect more" prose | category-specific repair action derived from the failed check | matches the locked operational requirement |

## Common Pitfalls

### Pitfall 1: Treating recovery truth as full preflight truth
**What goes wrong:** code sees a recovery assessment and assumes the stage is
ready.
**Why it fails:** recovery does not check runtime versions, dependency
availability, or cross-snapshot consistency.

### Pitfall 2: Blocking only execution, not recommendation
**What goes wrong:** `rd-agent` still tells the user to continue with
`rd-code`, but `rd-code` later blocks.
**Why it fails:** the context requires the blocker to be surfaced at the
recommendation boundary too.

### Pitfall 3: Allowing unknown checks to pass
**What goes wrong:** missing repo declarations, missing recovery assessment, or
ambiguous snapshots degrade to warnings.
**Why it fails:** the locked rule is "unknown counts as failed truth."

### Pitfall 4: Fixing text without fixing persisted summaries
**What goes wrong:** the top-level reply improves, but seeded stage summaries
still claim "ready."
**Why it fails:** later tooling or docs can still surface the stale wording.

---
_Research completed: 2026-03-22_
