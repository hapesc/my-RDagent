## 2026-03-08T16:20:15.275Z Session bootstrap
- Selected plan: loop-stability-and-usefulness-hardening.
- Selected worktree: /Users/michael-liang/Code/my-RDagent.
- Execution mode: TDD, no manual verification-only acceptance.

## 2026-03-08T16:36:20Z T1 decisions
- Applied conservative profile only when `llm_provider` is non-mock, so local mock trials keep existing breadth defaults.
- Enforced real-provider hard bounds in `app/config.py` and `agentrd_cli.py`: broad fan-out and retry overrides now fail deterministically before execution.
- Exposed `real_provider_safe_profile`, `uses_real_llm_provider`, and resolved `guardrail_warnings` in CLI config snapshots for later rollout auditing.

## 2026-03-08T16:40:44Z T1 scope correction
- Re-scoped Task 1 to config/runtime/CLI plus direct wiring tests only; reverted unrelated runtime/provider/plugin/test edits.

## 2026-03-09T00:00:00Z T2 decisions
- Added provider-local bounded retry/backoff for LiteLLM transient connectivity/unavailable failures with fixed delays `(0.1, 0.3)` and max 3 attempts total.
- Preserved existing auth/rate-limit/timeout error semantics as immediate failures with stable RuntimeError messages (no retry path for those categories).
- Set deterministic model-aware request timeout defaults in LiteLLM provider: standard=60s, thinking-model family=120s.

## 2026-03-09T11:15:00Z T3 decisions
- Kept structured-output strictness in `llm/adapter.py` rather than widening schema classes: required fields are inferred from dataclass typing (non-optional fields required) and validated before `from_dict` conversion.
- Added `StructuredOutputParseError` with per-attempt diagnostics and retryability classification; schema-contract failures are permanent, while malformed/missing-field payloads remain retryable.
- Added `LLMAdapter.generate_code` to keep metadata parsing and pure-code extraction split in adapter boundary, with code-fence stripping that prefers non-JSON fenced blocks.

## 2026-03-09T16:45:00Z T4 decisions
- Introduced shared outcome contract in `data_models.py` (`process_status`, `artifact_status`, `usefulness_status`) and made it derivable from legacy `ExecutionResult` fields via `resolve_outcome()`.
- Extended backend result/event payload to emit the same contract statuses so backend observability and loop semantics use aligned vocabulary.
- Enforced usefulness gate in `StepExecutor`: feedback cannot stay positive when contract marks process/artifact semantics as ineligible, while `LoopEngine` keeps reward wiring backward-compatible by preserving score propagation.

## 2026-03-09T17:20:00Z T5 decisions
- Kept observability scaffolding narrow: only added `step_latency_ms` fields in `core/loop/step_executor.py` event payloads and retry/failure summaries on `StructuredOutputParseError` in `llm/adapter.py`.
- Added adversarial tests at boundary modules already owning the contracts (`tests/test_task_12_llm_adapter.py`, `tests/test_task_09_loop_engine.py`, `tests/test_task_07_workspace_manager.py`) instead of expanding runtime architecture.
- Treated transient `ConnectionError`/`TimeoutError` from providers as retryable `provider_disconnect` failures so structured-output retries can recover from disconnects while schema-contract failures remain permanent.
