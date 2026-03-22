# RDAGENT Real-World UX Report

**Created:** 2026-03-22
**Scope:** real user conversations from external Kaggle-style project usage
**Status:** active input for v1.3 planning

## Source Logs

- `/Users/michael-liang/Code/aerial-cactus-identification/.waylog/history/2026-03-21_15-59-59Z-codex-rd-agent-description-to-assess-the-impact-of-clim.md`
- `/Users/michael-liang/Code/aerial-cactus-identification/.waylog/history/2026-03-22_07-16-18Z-codex-rd-agent.md`

## Executive Summary

The current rdagent pipeline is no longer unusable, but it still feels too
much like an exposed workflow engine and not enough like an operator assistant.
The strongest problems are:

1. the user must think too early about orchestration layers and skill names
2. paused-run continuation is not the default interaction model
3. environment and state blockers surface too late
4. surface wording and persisted state can drift apart
5. users still need to ask what the next skill should be

These are not isolated wording issues. They are pipeline/control-plane
problems, so they should shape milestone v1.3 directly.

## Problems Exposed by the Logs

### 1. Entry and user intent are on the wrong layer

**Observed**
- The user wanted to solve a Kaggle task or ask “what next?”
- The pipeline responded by explaining run/stage/state contracts first.

**Why this is bad**
- It shifts orchestration cognition onto the user before the system has helped
  them do useful work.
- It makes the product feel like a framework API instead of an assistant.

**Evidence**
- The logs repeatedly explain why a competition description is not yet an
  executable contract before giving the user a productive next step.

**Recommended fix**
- Add an intent-first routing layer above current skills.

**Priority**
- P0

### 2. `rd-agent` vs stage-skill routing is still too implicit

**Observed**
- The system had to infer mid-conversation that the correct next step was
  `rd-code`, not `rd-agent`.
- The user later had to ask explicitly which skill should be used next.

**Why this is bad**
- A persisted paused run should be the strongest routing signal in the system.
- If the user still has to ask which skill comes next, the control plane is not
  doing enough.

**Evidence**
- In the second log, the assistant discovers an existing paused run and then
  re-routes away from `rd-agent`.
- Later, after verify was blocked, the user asks “那下一步应该使用哪个skill”.

**Recommended fix**
- Default to continuation routing when paused work exists.
- Add a state-derived `recommended_next_skill` surface.

**Priority**
- P0

### 3. Surface contracts and real state can diverge

**Observed**
- A skill path could claim the next stage was prepared even though the expected
  persisted snapshot was missing.
- The assistant had to use a lower-level primitive to materialize `verify`
  state and then explain that the surface had been misleading.

**Why this is bad**
- It directly undermines trust in the pipeline.
- A user-visible claim without persisted state is effectively false.

**Evidence**
- The second log explicitly identifies that `rd-code` claimed verify was
  prepared while `verify.json` did not yet exist.

**Recommended fix**
- Enforce snapshot/materialization invariants before success text.
- Keep summary artifacts and latest-run handoff files synchronized with stage
  state.

**Priority**
- P0

### 4. Environment blockers are discovered too late

**Observed**
- Python version and dependency problems surfaced only after meaningful work
  had already been done.
- Verification later blocked on reproducibility because the active runtime did
  not satisfy the environment contract.

**Why this is bad**
- It wastes context, execution effort, and user trust.
- It turns a preflight problem into a mid-stage surprise.

**Evidence**
- The second log surfaces Python 3.9 vs 3.11 mismatch and missing
  `sklearn/joblib` only after baseline work and stage progression had already
  started.

**Recommended fix**
- Add a dedicated preflight layer before `rd-code` / `rd-execute`.

**Priority**
- P0

### 5. The pipeline lacks a formal “repair environment” path

**Observed**
- Once verify was blocked on environment reproducibility, the assistant could
  only say “先修环境，再重跑 `$rd-execute`”.

**Why this is bad**
- The recommendation is logically correct but not product-complete.
- Environment repair is a recurring workflow, not an edge case.

**Evidence**
- The final recommendation in the second log is effectively manual environment
  repair outside the formal skill surface.

**Recommended fix**
- Add an explicit remediation surface for environment blockers, even if it is
  not exposed as a top-level user skill.

**Priority**
- P1

### 6. Response verbosity is too orchestration-heavy

**Observed**
- The assistant emitted many intermediate messages about what it was checking
  and why.

**Why this is bad**
- The user mostly wants:
  - current state
  - why the next action is recommended
  - exact next action
- Everything else should be optional detail.

**Evidence**
- Both logs contain many “我先确认 / 我发现 / 我准备” style updates before
  arriving at a concrete action.

**Recommended fix**
- Standardize default user-facing responses to a 3-part shape:
  current state / reason / next action.

**Priority**
- P1

### 7. Execution scheduling is not dependency-hard enough

**Observed**
- Data extraction and training were run in parallel despite a hard dependency.
- This created a false failure that later had to be diagnosed away.

**Why this is bad**
- It makes the pipeline look unreliable even when the model or data are fine.
- False failures are more damaging than honest model failures.

**Evidence**
- The second log explicitly admits the earlier failure was caused by parallel
  execution against incomplete extracted data.

**Recommended fix**
- Add stronger DAG/dependency awareness for producer/consumer subwork.

**Priority**
- P1

### 8. Artifact sprawl is heavy for trial users

**Observed**
- `.rdagent-v3/`, `artifacts/`, and result files appeared quickly.

**Why this is bad**
- Good for debugging, but heavy for users who are only trying the flow.
- Makes the system feel invasive before it has proven value.

**Evidence**
- The second log creates many files before the user has clearly committed to a
  stable long-running workflow.

**Recommended fix**
- Distinguish lightweight trial mode from full persisted-run mode, or at least
  summarize the artifact footprint clearly.

**Priority**
- P2

## Root Cause Themes

### Workflow-engine-first bias

The product still assumes the user can tolerate thinking in run/stage mechanics
early, because the system is built around orchestration truth first and UX
translation second.

### Missing control-plane surfaces

The system needs stronger first-class answers for:
- what state am I in?
- what should I do next?
- why is that the next step?
- what is blocking me before I waste time?

### Weak preflight boundary

Runtime, dependency, artifact, and state consistency checks are not yet
enforced early enough.

## Recommended Priority Order

### P0

1. Intent-first entry routing
2. Paused-run-first continuation routing
3. State/materialization invariants
4. Early preflight for runtime, dependencies, data, and state

### P1

5. Formal remediation path for environment blockers
6. Concise state / reason / next-action UX
7. Stronger dependency-aware execution scheduling

### P2

8. Artifact footprint / trial-mode simplification

## How This Should Feed v1.3

This report should be treated as a primary planning input for:

- Phase 22: Intent Routing and Continuation Control
- Phase 23: Preflight and State Truth Hardening
- Phase 24: Operator Guidance and Next-Step UX

If later planning or execution drifts into generic “improve UX” phrasing, this
report is the corrective source of truth.
