# Milestone v1.3 Research — FEATURES

**Scope:** user-facing pipeline improvements
**Confidence:** HIGH

## Table stakes

### Intent-first entry

- User can describe the work in plain language without choosing a skill first.
- System decides whether to:
  - start a new run
  - continue a paused run
  - inspect existing state
  - route to a stage skill

### State-aware next-step guidance

- User can ask “what next?” and receive:
  - current state
  - reason for the recommendation
  - exact next action
- Recommendation should be derived from persisted run/branch/stage state rather
  than from surface prose only.

### Early preflight

- Before stage execution, system validates:
  - runtime version
  - required dependencies
  - expected data/artifact presence
  - state consistency
- Failures are surfaced as exact blockers with suggested fixes.

### Truthful state materialization

- Surface claims like “verify ready” or “continue with X” must be backed by
  persisted snapshots and summary artifacts.
- `latest-run-result` style artifacts must stay synchronized with real state.

## Differentiators

### Agent-first guidance layer

- The system helps the agent help the user, instead of teaching the user raw
  orchestration mechanics.
- Replies should default to:
  - where you are
  - why this next step
  - what to do now

### Recovery without tool spelunking

- Missing fields should trigger agent-led inspection and recovery first.
- Users should not need to browse low-level tools for normal continuation.

### Brownfield continuation model

- Existing paused work should dominate over creating a fresh run by default.
- New-run creation should require a positive reason, not happen accidentally.

## Anti-features

- Forcing the user to manually choose `rd-agent` vs `rd-code` vs `rd-tool-catalog`
  as the first step
- Claiming progress from surface text when persisted state does not match
- Discovering environment blockers only after costly stage execution has begun
- Verbose orchestration narration that obscures the actual next action
