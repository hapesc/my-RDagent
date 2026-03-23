# TODOS

## Orchestration

### Preload stage context once across stage entry and preflight

**What:** Introduce a shared preloaded stage-context path so `rd_propose`, `rd_code`, `rd_execute`, and `rd_evaluate` do not each re-read run, branch, stage, artifact, and recovery state before calling preflight.

**Why:** Phase 24 deliberately avoided a larger state-read refactor, but the current stage entry flow still does one round of entrypoint reads and then another round inside `PreflightService`. This is acceptable now with the local state store, but it is repeated work, makes the code harder to reason about, and will become a larger tax if the state backend grows more expensive.

**Context:** Keep the current Phase 24 rule that new guidance helpers must not read state themselves. After Phase 24 lands, revisit the stage entrypoints plus preflight integration and decide whether a shared `StageExecutionContext` or similar preload object can be created once and passed through. The goal is not a broad rewrite; it is to remove duplicate state-loading while keeping `PreflightService` as the canonical blocked/executable truth source and preserving the existing public field names and outcome semantics.

**Effort:** M
**Priority:** P2
**Depends on:** Phase 24 operator-guidance work landing cleanly first
