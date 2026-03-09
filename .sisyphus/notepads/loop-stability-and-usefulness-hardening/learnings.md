## 2026-03-08T16:20:15.275Z Session bootstrap
- Real-provider-safe first-phase preset agreed: n_candidates=1, k_forward=1, costeer_max_rounds=1, timeout_sec=120, retries<=1.
- Acceptance standard changed from "can run" to "output must be useful".
- usefulness rollout is scenario-first: common hard gate first, then scene-specific validators.

## 2026-03-08T16:36:20Z T1 implementation learnings
- Real-provider-safe defaults need source-aware config merging; otherwise provider selection still inherits mock-era breadth and timeout defaults.
- Keeping mock-mode ergonomics intact is easiest when config applies conservative defaults only for real providers and runtime rewrites scenario step defaults for retries/model wiring.
- Guardrail warnings are most useful when stored in the run config snapshot so smoke audits can inspect effective settings without replaying config resolution.

## 2026-03-08T16:40:44Z T1 scope correction
- Task 1 can stay narrow if retry bounds are enforced at config+runtime snapshot boundaries without editing provider or scenario implementation files.

## 2026-03-09T00:00:00Z T2 provider reliability learnings
- LiteLLM transient outage classes (`APIConnectionError`, `ServiceUnavailableError`) are best handled in the provider boundary with explicit bounded retries, so adapter-level parse retries stay focused on schema validity only.
- Deterministic provider timeouts by model family (thinking vs standard) keep behavior stable under flaky networks while avoiding hidden dependency on external defaults.

## 2026-03-09T11:15:00Z T3 adapter hardening learnings
- Schema `from_dict` defaults can mask partial/invalid LLM payloads; adapter-level required-field validation must run before conversion to avoid false success.
- Parse retry loops are more diagnosable when each attempt records stage classification (`json_decode`, `required_fields`, `schema`) and retryability instead of only surfacing the final exception.
- JSON extraction must avoid treating closed non-JSON fences as unclosed JSON blocks; a simple fence-count guard prevents accidental misparse in mixed metadata+code responses.

## 2026-03-09T16:45:00Z T4 outcome-contract learnings
- Keeping `ExecutionResult.resolve_outcome()` as the canonical derivation point avoids module drift: step executor and backend can consume one contract shape while existing callers remain backward-compatible.
- False-success handling is stable when enforced at step boundary (`feedback.decision/acceptable` clamped by usefulness eligibility) instead of scattering exit-code checks into loop policy.
- Full-suite compatibility requires additive contract fields (`outcome` optional defaults) and non-breaking engine behavior for older mocked `StepExecutionResult` fixtures.

## 2026-03-09T17:20:00Z T5 adversarial-harness learnings
- Adapter-level retry coverage was missing provider disconnect behavior entirely because `provider.complete()` failures escaped before parse diagnostics were recorded; wrapping provider calls inside the retry loop keeps transient disconnects observable and recoverable without widening product logic.
- Minimal rollout observability can stay deterministic by exposing small metrics at existing boundaries: `step_latency_ms` on step events plus adapter-side `retry_count`/`failure_counts` on structured parse failures were enough to cover latency, retries, and validator rejects in tests.
- Exact provider call-count assertions are brittle once retry/recovery hardening is introduced; replacing them with lower-bound contract checks preserves behavior coverage without pinning internal orchestration.

## 2026-03-09T19:10:00Z T8 common usefulness-gate learnings
- A reusable gate is stable when it emits deterministic stage+reason (`syntax`/`semantic`/`utility`) and writes that metadata into existing execution/feedback events, instead of introducing an opaque score.
- Hard negatives are best split between common checks (`empty`, `template-only`, `missing key field`, `contradictory status`) and scene hooks for required domain fields; this keeps shared logic strict while avoiding scenario coupling.
- Scene-level validators should be first-class bundle hooks (`scene_usefulness_validator`) so new scenarios can layer checks without bypassing the common gate path in `StepExecutor`.

## 2026-03-09T19:45:00Z T8 regression-fix learnings
- Docker-first execution needs runtime-availability fallback, not just binary-presence checks; when docker CLI exists but daemon is unreachable, allowing local fallback keeps deterministic tests stable without weakening failure propagation for real command errors.

## 2026-03-09T18:10:00Z T7 backend-runner verification alignment learnings
- Artifact verification cannot infer validity from non-empty payloads; strict manifest decoding (valid JSON + `paths: List[str]` shape) is required to distinguish `MISSING_REQUIRED` from `MALFORMED_REQUIRED` and avoid false eligibility.
- Runner/backend alignment is most stable when runner forwards backend-derived `outcome` and `artifact_manifest` directly into `ExecutionResult`, instead of recomputing from `exit_code` and raw path arrays.
- Loop completion semantics need a final outcome gate: hitting `max_loops` should mark run `FAILED` when process succeeded but artifact verification failed, otherwise artifact regressions are mislabeled as full completion.

## 2026-03-09T23:40:00Z T6 deterministic failure propagation learnings
- Step-level explicit terminal state (`RECORDED` vs `FAILED`) in `StepExecutionResult` removes engine dependence on exception-only control flow and gives deterministic run-state transitions.
- Treating non-success `ExecutionOutcomeContract.process_status` as fatal at loop policy boundary prevents non-zero exit/timeouts from being recorded as successful iterations.
- In scheduler mode, isolating branch failures but failing iteration when `successful_branches==0` and `failed_branches>0` preserves multi-branch resilience while blocking silent completion on fully failed iterations.

## 2026-03-10T00:35:00Z T6-T8 regression repair learnings
- Fatality checks in `LoopEngine` must be backward-compatible with legacy mocked `step_result` fixtures (`SimpleNamespace` without `step_state/outcome`) by using `getattr` guards at every read site, not only in helper predicates.
- Treating all usefulness-ineligible outcomes as fatal is too broad for existing long-running control-plane workflows; narrowing fatality to process failure and artifact verification failure preserves deterministic failure propagation while keeping scene-level usefulness as a ranking/decision signal.
- Artifact contract now expects JSON manifest semantics for `artifacts_ref`; test fixtures that previously returned plain path strings must emit JSON list strings (or manifest objects) to avoid `MALFORMED_REQUIRED` false regressions.

## 2026-03-09T21:30:00Z T10 synthetic usefulness validator learnings
- Synthetic scene validators need explicit synthesized-content fields (`synthesized_summary`, `synthesized_findings`) to prevent artifact-file-exists false positives.
- Prompt-echo and template-only rejection is more stable when scene checks run alongside common gate semantics: common gate handles raw placeholders, scene gate enforces domain-specific synthesis quality and task linkage.
- Deterministic usefulness outcomes are easiest when rejection reasons are fixed-string contracts (`generic synthesized summary`, `prompt-echo synthesized findings`, `missing task-specific synthesis`) and tests assert those exact reasons.

## 2026-03-09T23:59:00Z T13 brittle-test migration learnings
- FC-3 tests are more robust when they assert ranking/no-ranking semantics from prompt shape and returned designs, instead of pinning exact provider call totals that change under retry hardening.
- Pipeline failure coverage needs adapter diagnostics surfaced at the scenario boundary (`payload_type`, provider disconnect recovery), otherwise malformed structured-output regressions can hide behind generic `ValueError` assertions.
- Resume and multi-branch tests stay deterministic when they encode failure mode and resource handoff explicitly: corrupted checkpoints must fail closed with restore context, and restored workspaces should only seed the first parallel branch.

## 2026-03-08T18:04:17Z T9 data_science usefulness validator learnings
- Scene validator should explicitly reject row-count-only payloads (`status` + `row_count` only), otherwise generic positive logs can mask analytically empty outputs.
- Stable pass criteria for `data_science` should require at least one informative metric beyond execution shell fields (`status`/`row_count`), with placeholder-like values treated as non-informative.
- Keeping checks layered (`CommonUsefulnessGate` first, scene validator second) preserves contract semantics and blocks LLM summary text from bypassing hard utility constraints.

## 2026-03-09T23:55:00Z T11 real-run gating learnings
- Layer-0 gating must be call-time overridable (`VirtualEvaluator.evaluate(..., n_candidates, k_forward)`) because engine policy may need to tighten width per run, and manager-level parameters were previously ignored by evaluator internals.
- Real-provider run safety is most reliable when enforced at loop execution time from `run_session.config_snapshot.runtime`, with conservative fallback to safe profile unless guardrail warnings explicitly indicate sanctioned non-conservative overrides.
- Suppressing positive continuation requires dual-channel clamping: both MCTS backup reward inputs (`score=None`, `decision=False`) and node prior potential (`node.score=None`) for usefulness-ineligible outcomes.
- CoSTEER acceptance must honor execution outcome contract (`process_succeeded` + `artifacts_verified` + `usefulness_eligible`) so analyzer-only positives cannot short-circuit on unverified outputs.

## 2026-03-09T23:55:00Z T14 smoke rollout learnings
- Real-provider smoke verification is safest when the script injects an explicit config snapshot with conservative step overrides instead of relying on ambient runtime defaults or local env drift.
- Warning-stage rollout needs two surfaces: persisted `guardrail_warnings` in the run snapshot for auditability and immediate CLI stderr warnings so risky-but-allowed real runs are visible before operators trust the result.
- Smoke success must be derived from execution/feedback usefulness events, not only run completion, otherwise validator rejects still look green in environments where the loop intentionally keeps usefulness as a non-fatal signal.

## 2026-03-09T23:59:00Z T12 checkpoint integrity and idempotent recovery learnings
- Checkpoint restore must be staged and swapped atomically; deleting workspace before payload validation turns missing/corrupt checkpoint into destructive state loss.
- Zip integrity checks (`ZipFile.testzip` + invalid-archive normalization) are most useful when performed before final workspace replacement, so failure leaves prior workspace untouched.
- Resume-path restore failures should be promoted to deterministic run failure (`RunStatus.FAILED` + `last_error`) to prevent corruption from being misclassified as resumable/running progress.

## 2026-03-10T01:15:00Z T14 smoke-script semantic fix learnings
- Single-loop smoke execution status semantics: `max_loops=1` affects loop iteration count, NOT run state transition; run may remain RUNNING after one loop completes. Success must be based purely on usefulness+feedback validator gates, not run completion status.
- `evaluate_smoke_success()` signature change: removed `run_status` parameter and final run-completion check; acceptance criteria now solely depends on execution.finished.usefulness_status=ELIGIBLE + feedback.generated.acceptable=true.
- Explicit stop_conditions injection in create_run ensures single-loop smoke semantics are machine-readable in run config snapshot without depending on ambient loop-engine defaults.
- Smoke test case generalization: test cases dropped `run_status="COMPLETED"` argument and added explicit coverage for RUNNING-status scenario to prevent future run-state refactoring from breaking smoke validity.

## 2026-03-09T23:59:59Z F1 gap remediation learnings
- Control-plane `create_run` snapshot must call `resolve_scenario_runtime_profile(...)` (not `resolve_step_override_config(...)`) to keep runtime guardrail behavior exactly aligned with CLI, including `guardrail_warnings` and `real_provider_safe_profile` surfaces.
- `LoopEngine` run-finalization needs a dedicated usefulness-reject gate; relying only on fatal process/artifact checks still allows `max_loops` exhaustion to mislabel usefulness-rejected runs as `COMPLETED`.
- Minimal regression coverage is sufficient when split by boundary: control-plane snapshot parity assertion (real-provider runtime fields + warning capture) and loop-level terminal-state assertion for `process=SUCCESS`, `artifact=VERIFIED`, `usefulness=INELIGIBLE`.

## 2026-03-10T02:10:00Z F2 artifact-status gate learnings
- `CommonUsefulnessGate.evaluate()` must gate on `artifact_status==VERIFIED` immediately after process success; otherwise malformed manifests can pass semantic/utility checks and be incorrectly marked `ELIGIBLE`.
- Keeping early-exit order fixed (`process_status` first, then `artifact_status`) preserves layered contract semantics and keeps rejection reasons diagnosable by stage.

## 2026-03-09T03:27:04Z F2 field-type validation hardening learnings
- Adapter must validate schema field types before  coercion; otherwise values like  can silently pass via cast and hide malformed LLM payloads.
- Type mismatch diagnostics are most actionable when mapped to a distinct parse stage (), allowing retries/telemetry to separate structural absence from semantic type drift.

## 2026-03-09T03:27:09Z F3 feedback-consistency guardrail learnings
- Feedback acceptance needs an internal semantic consistency gate: if  contains explicit negative qualifiers (/////), force  even when analyzer returns positive flags.
- This guardrail should live at StepExecutor clamping boundary (next to usefulness eligibility clamp) so scene analyzers remain unchanged while false-positive risk is reduced across all plugins.

## 2026-03-09T03:27:14Z F2 field-type validation hardening learnings
- Adapter must validate schema field types before from_dict coercion; otherwise values like string numeric literals can silently pass via cast and hide malformed LLM payloads.
- Type mismatch diagnostics are most actionable when mapped to a distinct parse stage (field_types), allowing retries and telemetry to separate structural absence from semantic type drift.

## 2026-03-09T03:27:17Z F3 feedback-consistency guardrail learnings
- Feedback acceptance needs an internal semantic consistency gate: if reason contains explicit negative qualifiers (synthetic/placeholder/template-only/preventing real assessment/not useful/insufficient), force acceptable=False even when analyzer returns positive flags.
- This guardrail should live at StepExecutor clamping boundary (next to usefulness eligibility clamp) so scene analyzers remain unchanged while false-positive risk is reduced across all plugins.
