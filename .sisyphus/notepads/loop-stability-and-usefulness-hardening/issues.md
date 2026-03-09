## 2026-03-08T16:20:15.275Z Known risks at start
- Existing defaults are mock-friendly and likely unstable/costly under real providers.
- Provider layer currently under-handles transient Gemini/LiteLLM failures.
- Historical tests over-index on happy-path and brittle exact internal counters.

## 2026-03-08T16:36:20Z T1 follow-up issues
- Real-provider smoke tests still depend on patching the provider in unit/integration coverage because live LiteLLM execution would add network flakiness to config/runtime verification.
- `app.control_plane.py` still builds its own config snapshot path and may need the same guardrail metadata later to keep API parity with the CLI.

## 2026-03-08T16:40:44Z T1 residual issue
- Control-plane snapshot parity is still open, but left untouched because this task is restricted to CLI/config/runtime wiring only.

## 2026-03-09T00:00:00Z T2 follow-up issues
- Provider backoff currently uses fixed constants without jitter; acceptable for deterministic tests, but production hardening may later require bounded jitter if correlated retries become noisy.
- Retryability classification is intentionally narrow (`APIConnectionError`, `ServiceUnavailableError`); if upstream LiteLLM adds provider-specific transient subclasses, mapping should be revisited.

## 2026-03-09T11:15:00Z T3 follow-up issues
- Required-field validation currently checks presence/non-null but not deep element typing (e.g., list member types), so malformed nested structures can still rely on schema coercion.
- `generate_code` extraction prefers fenced blocks and returns empty string when no block exists; future consumers may require fallback heuristics for inline code-only responses.

## 2026-03-09T16:45:00Z T4 follow-up issues
- Backend contract currently treats any non-empty artifact list as verified; required-artifact shape/contents are not scenario-aware yet and should be tightened by later scene validators.
- `DataScienceRunner` still reconstructs `ExecutionResult` from primitive backend fields, so richer backend-level contract fields are re-derived in `StepExecutor` until runner/backend alignment task lands.

## 2026-03-09T17:20:00Z T5 follow-up issues
- Worktree already contains unrelated modified files outside this task; verification stayed scoped to touched hardening files plus full regression, but cleanup/segmentation is still needed before any commit.
- `step_latency_ms` is wall-clock timing from in-process orchestration and intentionally not a full metrics pipeline; if rollout needs aggregation/export later, a dedicated observability sink still has to be wired.

## 2026-03-09T19:10:00Z T8 follow-up issues
- Local verification can fail spuriously when `docker` binary exists but daemon is unavailable; for deterministic no-docker tests we had to hide `/opt/homebrew/bin/docker` from `PATH` so local execution fallback is exercised.

## 2026-03-09T19:45:00Z T8 regression-fix follow-up
- Docker daemon error detection currently relies on stderr markers + exit codes (`125`/`-1`); if docker CLI wording changes, fallback detection patterns may need refresh.

## 2026-03-09T23:55:00Z T11 follow-up issues
- Real-provider branch clamp currently hard-fixes scheduler breadth to one branch per iteration with no dedicated explicit override channel beyond code-level config mutation; if product later needs controlled real-provider multi-branch, add a first-class guarded override in runtime snapshot/CLI contract.

## 2026-03-09T23:55:00Z T14 rollout follow-up
- Real-provider smoke still cannot prove upstream provider health deterministically in local CI, so confidence comes from explicit preset/validator unit coverage plus optional live execution in suitably provisioned environments.

## 2026-03-09T23:59:00Z T12 follow-up issues
- Resume manager currently fails hard on latest-checkpoint corruption instead of scanning older checkpoints; this is deterministic and safe, but availability-oriented fallback remains an explicit future policy choice.

## 2026-03-09T23:59:00Z T13 follow-up issues
- Resume corruption now fails deterministically in tests, but `RunService.resume_run()` persists the run as `RUNNING` briefly before checkpoint restore flips it to `FAILED`; if operators need cleaner state transitions, restore may need a pre-run staging status.
- Concurrency coverage currently proves restored-workspace handoff semantics in scheduler mode, but there is still no locking around real concurrent `resume_run()` / `fork_branch()` callers; production control-plane concurrency would need explicit serialization.

## 2026-03-10T02:10:00Z F1 regression fix follow-up
- Global usefulness-reject => run `FAILED` broke mock/default CLI/UI/control-plane flows that intentionally treat usefulness as continuation signal in non-real-provider mode.
- Repaired by scoping terminal usefulness-fail policy to `runtime.uses_real_llm_provider=true`; mock/legacy runs keep compatibility, while real-provider runs keep hardened semantic contract.
