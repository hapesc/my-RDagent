# Milestone v1.3 Research — ARCHITECTURE

**Scope:** pipeline/control-plane architecture
**Confidence:** HIGH

## Reference architecture lessons from get-shit-done

### 1. Command taxonomy above orchestration internals

The reference repo does not ask the user to think in internal state machine
terms first. It exposes lifecycle-oriented commands:

- start work
- inspect progress
- discuss/plan/execute/verify
- complete milestone

This gives the user a stable mental model even though the internal workflow is
artifact-heavy.

### 2. Single visible mainline, many hidden artifacts

`PROJECT.md`, `STATE.md`, `REQUIREMENTS.md`, `ROADMAP.md`, phase directories,
and summaries all exist, but the user is guided by one visible path. The
artifacts support the workflow; they are not the workflow UX.

### 3. “What’s next?” is a first-class control-plane answer

The reference pipeline repeatedly answers:

- where am I?
- what just happened?
- what should I do next?

This is a control-plane primitive in its own right, not an afterthought.

## Recommended architecture for rdagent

### Intent router layer

Add a thin layer above existing skills that:

- reads user intent
- inspects persisted run state
- chooses the correct high-level action
- returns a concise operator-facing explanation

Likely integration points:
- `rd-agent` entry surface
- a future “next-step” or “progress” surface
- shared helpers over `.rdagent-v3` state

### Preflight gate layer

Before `rd-code` / `rd-execute` / later high-value stage actions:

- validate environment and runtime contracts
- validate required artifacts
- validate snapshot consistency

Outputs should be first-class and machine-readable so blocked states are
truthful and reproducible.

### State truth harmonization

Unify:
- skill/tool surface claims
- stage snapshots on disk
- handoff summaries such as `latest-run-result`

A user-visible claim should never outrun persisted state.

### Operator UX layer

Standard response shape for high-level surfaces:

1. current state
2. why this action
3. exact next step

Detailed orchestration reasoning should be available but not default.

## Suggested build order

1. intent routing and paused-run detection
2. preflight and environment blocker surfacing
3. state/materialization consistency fixes
4. operator-facing progress and next-step UX consolidation
