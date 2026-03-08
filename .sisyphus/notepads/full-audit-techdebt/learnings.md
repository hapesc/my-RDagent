## Learnings

- Current approved baseline: branch `feat/paper-fc-implementation`, tests previously at `548 passed, 3 warnings`.
- The only pre-session boulder drift was `.sisyphus/boulder.json` pointing to stale FC-2/FC-3 tracking; `.sisyphus/evidence/` is valid and must not be touched.
- Confirmed dead modules with zero or effectively zero external usage: `development_service/`, `execution_service/`, `artifact_registry/`.
- `reasoning_service/` is not safe to delete immediately; `scenarios/synthetic_research/plugin.py` and `tests/test_scenario_fc3_integration.py` depended on it, so migration must precede deletion.
- `core/loop/engine.py` hardcodes Layer-0 params `5/2`; `app/config.py` already defines `layer0_n_candidates` and `layer0_k_forward`, so this is config wiring debt, not new feature work.
- `plugins/__init__.py` imports `scenarios`, and `exploration_manager/service.py` imports `core.reasoning.virtual_eval`; these are the two main cycle sources to fix conservatively.
- `hasattr` cleanup must preserve optional capability semantics; do not accidentally make diverse roots or merge mandatory.
- Exception handling splits into two classes: silent swallow (`workspace_manager.py`, `ui/trace_ui.py`) vs rollback+reraise (`memory_service/service.py`, `core/storage/sqlite_store.py`, `core/storage/branch_trace_store.py`). Treat them differently.
- Document cleanup scope is limited to stale references, contradictions, outdated counts/commands. Do not rewrite architecture docs wholesale.
- App-layer test audit found weak coverage for `app/api_main.py`, `app/startup.py`, `app/run_supervisor.py`, `app/query_services.py`, `app/fastapi_compat.py`.
- Metadata cleanup completed: `.sisyphus/boulder.json` was stale (dated 2026-03-08 05:16, pointing to old FC-2/FC-3 plan). It blocked clean state and was safely deleted. `.sisyphus/plans/paper-fc2-fc3.md` (110KB) archived to `ARCHIVED-*` prefix. `.sisyphus/evidence/` (544KB, 68 items) left untouched—all valid tracking data. This preserves the audit trail while unblocking Wave 1.

## Wave 1 Task 3: execution_service/ Deletion

- Fresh grep verification: ZERO references to `execution_service` across entire codebase (confirms it was truly dead).
- Module inspection: `execution_service/` contained only placeholder stubs (execute_artifact, stream_logs, terminate_run all returned placeholders).
- Deletion: Removed `/execution_service/` directory entirely; safe removal with zero external dependencies.
- Test audit: `tests/test_task_01_core_models.py::ModelLayerUsageTests::test_core_services_import_model_layer` was validating all core services; removed `execution_service/service.py` from expected list.
- Regression result: Full pytest run = 548 passed, 3 warnings (pre-existing, baseline verified).
- Files modified: `execution_service/` deleted, `tests/test_task_01_core_models.py` updated to remove dead service from validation.
- Conclusion: Dead placeholder successfully removed with zero side effects. Safe to proceed with `development_service/` deletion in follow-on task.

### Wave 1 Deletion #4: artifact_registry/ completed
- **Deletion date**: 2026-03-08
- **Verification approach**: Grep for `artifact_registry` and `ArtifactRegistry` across all Python files (excluding self-references inside the module); only external reference found was in `tests/test_task_01_core_models.py` where it was listed in the `core_service_files` list.
- **Changes made**: 
  1. Deleted `/Users/michael-liang/Code/my-RDagent/artifact_registry/` directory completely
  2. Updated `tests/test_task_01_core_models.py` to remove `artifact_registry/service.py` from the `core_service_files` list
- **Test result**: 548 passed, 3 warnings (same baseline as pre-session approval)
- **No regressions detected**: Full test suite passes with identical pass count

## Wave 1 Cleanup: development_service/ Deletion

- **Action**: Deleted `development_service/` directory (confirmed zero external references via fresh grep).
- **Test Impact**: Updated `tests/test_task_01_core_models.py::ModelLayerUsageTests::test_core_services_import_model_layer` to remove hardcoded path for `development_service/service.py`. Also removed already-deleted `execution_service/service.py` from the same test.
- **Verification**: Fresh grep confirmed no imports of `from development_service` or `import development_service` across entire codebase.
- **Regression**: `548 passed, 3 warnings` (same as baseline after cache clear).
- **Note**: Deletion was straightforward because module was pure placeholder with no external usage. Single test update needed.

## Wave 1 Task 5: Layer-0 Params Runtime Wiring

- `core/loop/engine.py` no longer hardcodes `n_candidates=5` / `k_forward=2`; `LoopEngine` now reads both values from `LoopEngineConfig`.
- `app/runtime.py::build_run_service` now passes `runtime.config.layer0_n_candidates` and `runtime.config.layer0_k_forward` into `LoopEngineConfig`, preserving existing `VirtualEvaluator` wiring unchanged.
- `tests/test_loop_engine_mcts.py` now asserts `generate_diverse_roots` receives configured values (custom `9/4`), proving call-site behavior is config-driven rather than hardcoded.
- `tests/test_runtime_wiring.py` adds env-driven wiring verification (`RD_AGENT_LAYER0_N_CANDIDATES=11`, `RD_AGENT_LAYER0_K_FORWARD=6`) and checks these land in `run_service._loop_engine._config`.
- Validation: targeted tests (`21 passed`) and full regression (`549 passed, 3 warnings`) both green; required grep checks for hardcoded `5/2` return `0`.

## Wave 2 Task 6: synthetic_research decoupled from reasoning_service (Phase 1)

- Removed external `reasoning_service` imports from callers by migrating `scenarios/synthetic_research/plugin.py` and `tests/test_scenario_fc3_integration.py` to a local fallback path.
- `SyntheticResearchProposalEngine` fallback order remains conservative and unchanged: `virtual_evaluator -> reasoning_pipeline -> llm_adapter -> local fallback`.
- Local fallback returns `proposal-placeholder` with `summary=task_summary_or_context` and `constraints=["synthetic_research_pipeline"]`, preserving prior policy semantics.
- Fresh grep confirms no non-`reasoning_service/` Python caller imports of `reasoning_service` or `ReasoningService`.
- Verification: targeted tests (`15 passed`) and full regression (`549 passed, 3 warnings`) pass.

## Wave 1 Task 7: Silent Exception Handler Logging

- **Task**: Add logging to silent-swallow exception handlers in `workspace_manager.py` and `trace_ui.py` while preserving return-value semantics.
- **Files modified**:
  - `core/execution/workspace_manager.py`: Added `import logging` and module logger; wrapped `execute_with_recovery()` line 127 exception handler with `logger.exception()` call capturing exception and contextual run_id/checkpoint_id.
  - `ui/trace_ui.py`: Added `import logging` and module logger; wrapped `_extract_metrics()` line 206 exception handler with `logger.exception()` call capturing exception and file path.
- **Return semantics preserved**: Both handlers maintain exact original return values (`execute_with_recovery()` still returns `False` after restore, `_extract_metrics()` still returns fallback error dict).
- **Verification**:
  - LSP diagnostics: `workspace_manager.py` clean (no errors). `trace_ui.py` shows pre-existing streamlit import warning (not introduced by this task).
  - Targeted tests: `test_task_07_workspace_manager.py::test_checkpoint_create_restore_and_recovery` PASSED. `test_task_15_trace_ui.py::test_load_runs_events_and_artifacts` PASSED.
  - Full regression: 549 passed, 3 warnings (1 additional test vs baseline 548; likely due to logging instrumentation not introducing regressions).
- **Scope adherence**: Did not touch rollback+reraise paths in `memory_service/` or `core/storage/`; confined changes to silent-swallow handlers only; did not broaden into repo-wide exception policy.

## Wave 3 Task 10: hasattr() Replacement in Three Low-Risk Sites

- **Task**: Replace `hasattr()` checks conservatively in `llm/adapter.py`, `app/control_plane.py`, and `ui/trace_ui.py`.
- **Files modified**:
  - `llm/adapter.py:299`: Replaced `hasattr(schema_cls, "from_dict")` with try-except on `getattr()`, raising `TypeError` if `AttributeError` is caught.
  - `app/control_plane.py:208-225`: Replaced `hasattr(request.stop_conditions, "to_dict")` with try-except; graceful fallback to manual dict construction preserves both optional method call and manual fallback semantics.
  - `ui/trace_ui.py:137-152`: Replaced `hasattr(client, f"{action}_run")` with try-except on `getattr()`, raising `AttributeError` triggers POST fallback path; preserves client abstraction (ControlPlaneClient-like vs plain POST-based clients).
- **Verification**:
  - grep verification: `grep -n "hasattr(" llm/adapter.py app/control_plane.py ui/trace_ui.py` returns zero matches (confirmed removal).
  - Targeted tests: `test_task_12_llm_adapter.py` 3 passed, `test_task_21_control_plane.py` 6 passed, `test_task_15_trace_ui.py` 1 passed.
  - Full regression: 549 passed, 3 warnings (same as Wave 1/2 baseline; zero new failures).
- **Pattern notes**:
  - All three replacements maintain exact original fallback behavior: silent or exception-raising paths unchanged.
  - No changes to DTO field names, response shapes, or call site semantics.
  - Pre-existing LSP errors in `app/control_plane.py` (unrelated type annotation issues) left unchanged; runtime behavior unaffected.

## Wave 3 Task 10: hasattr() Replacement (Revised - ATLAS REJECTION FIX)

**REJECTION ANALYSIS:**
- Previous attempt removed `hasattr()` textually but lacked test coverage for the new behavior.
- Atlas identified a critical logic bug: `perform_control_action()` wrapped `getattr(...)(run_id)` in `try/except AttributeError`, which misclassifies exceptions thrown *inside* a real client method as "method missing" and incorrectly falls back to HTTP POST.
- Atlas also flagged static analysis issue in `_build_config_snapshot()`: direct access to `.to_dict()` on `StopConditions` triggers Pyright error.

**FIXES APPLIED:**

1. **`llm/adapter.py:299-303`** – Explicit validation before call:
   - Use `getattr(schema_cls, "from_dict", None)` with `callable()` check before invocation.
   - Import `cast` from typing; use `cast(T, converter(payload))` to satisfy type checker.
   - Preserves exact error semantics: raises `TypeError` wrapped in `ValueError` retry loop.

2. **`app/control_plane.py:208-229`** – Pre-check approach with fallback:
   - Use `getattr(request.stop_conditions, "to_dict", None)` with `callable()` check.
   - Avoids direct `.to_dict()` access that triggers static analysis.
   - Manual fallback dict construction uses field access (max_loops, max_steps, max_duration_sec).
   - Preserves exact serialization semantics for both optional and mandatory paths.

3. **`ui/trace_ui.py:137-152`** – Method availability check, not exception handling:
   - Use `getattr(client, method_name, None)` and check `callable()`.
   - Only invoke direct method if truly callable; otherwise use HTTP POST.
   - Avoids catching `AttributeError` from inside method bodies.
   - Preserves both ControlPlaneClient-like and plain HTTP client abstractions.

**TESTS ADDED:**
- `test_task_12_llm_adapter.py`: 2 new tests for schema without/with non-callable `from_dict`.
- `test_task_21_control_plane.py`: 1 new test for fallback serialization of `StopConditions`.
- `test_task_15_trace_ui.py`: 3 new tests proving method path is used when available, POST fallback when method is missing, and non-callable attributes fallback to POST.

**VERIFICATION:**
- Targeted tests: 16 passed (10 original + 6 new).
- Full regression: 555 passed, 3 warnings (6 new test cases, zero regressions).
- grep confirmation: zero `hasattr(` calls in target files.
- Pre-existing Pyright errors in `app/control_plane.py` (lines 31, 187) unrelated to this task; not touched.
- Pre-existing streamlit import warning in `ui/trace_ui.py` unrelated to this task; not touched.

**PATTERN SUMMARY:**
- All three fixes validate presence + callability *before* use, rather than catching exceptions *after* calls.
- All preserve exact return/value semantics for both primary and fallback paths.
- No DTO field names or response shapes changed; no new dependencies added.


## Wave 3 Task 8: ExplorationManager capability protocol + engine hasattr cleanup

- Added explicit optional capability protocols in `exploration_manager/service.py`: `SupportsDiverseRoots` and `SupportsTraceMerge`.
- Added concrete capability guards `supports_diverse_roots()` / `supports_trace_merge()` based on class-level callable methods, so legacy doubles without methods correctly fall back while dynamic mocks do not get accidental capability promotion.
- `core/loop/engine.py` now uses capability guards instead of `hasattr(self._exploration_manager, ...)` for both Layer-0 diverse root generation and merge-traces stage.
- Fallback semantics preserved: no diverse-root capability => single `root` node path; no merge capability => merge skipped without failure.
- Test updates:
  - `tests/test_loop_engine_mcts.py`: replaced mock-based diverse-root test double with concrete capability double to verify configured `n_candidates/k_forward` path and legacy fallback path.
  - `tests/test_engine_multibranch.py`: added explicit tests for merge capability supported vs unsupported branches.
- Verification green: targeted suite `39 passed`; full regression `557 passed, 3 warnings` (warning profile unchanged).

## Wave 3 Task 9: import-cycle removal

- `plugins/__init__.py` no longer imports `scenarios` at module top level; built-in scenario configs/builders now load lazily inside manifest/registry helpers, preserving `build_default_registry()` behavior with minimal churn.
- `exploration_manager/service.py` no longer imports `core.reasoning.virtual_eval`; it accepts an injected evaluator-like object and only does a duck-typed re-instantiation when the injected object exposes concrete VirtualEvaluator state (`_llm_adapter`, `_n_candidates`, `_k_forward`).
- Runtime wiring behavior remains intact: `build_runtime()` still injects the shared `VirtualEvaluator` into both `ExplorationManager` and built-in plugin bundles, and import smoke (`import plugins`, `import exploration_manager.service`, `import scenarios.synthetic_research.plugin`) now passes cleanly.
- Added regression coverage in `tests/test_runtime_wiring.py` for subprocess import smoke and evaluator injection into `ExplorationManager`.
- Verification: targeted runtime/integration suite passed (`22 passed`), focused exploration/runtime suite passed (`45 passed`), full regression passed (`559 passed, 3 warnings`).

## Wave 3 Task 11: reasoning_service/ Deletion

- **Precondition verified**: Task 6 migration moved all external callers (`scenarios/synthetic_research/plugin.py`, `tests/test_scenario_fc3_integration.py`) to local fallback paths; zero external imports found via fresh grep.
- **Deletion executed**: Removed `/reasoning_service/` directory entirely (deleted `__init__.py` and `service.py`).
- **Test update required**: `tests/test_task_01_core_models.py::ModelLayerUsageTests::test_core_services_import_model_layer` was validating all core services; removed `reasoning_service/service.py` from expected list.
- **Verification**:
  - Targeted tests: `test_scenario_fc3_integration.py` (11 passed), `test_task_19_synthetic_research.py` (4 passed) both green.
  - Full regression: `559 passed, 3 warnings` (baseline matched).
  - Final grep: zero references to `reasoning_service` outside `.sisyphus/`.
  - Directory deleted: `test ! -d reasoning_service` succeeds.
- **Files modified**: `reasoning_service/__init__.py` deleted, `reasoning_service/service.py` deleted, `tests/test_task_01_core_models.py` updated.
- **Conclusion**: Dead service successfully removed with zero side effects. Task 11 blocks Task 14 cleanly.

## Wave 4 Task 12: rollback+reraise Exception Handler Logging

- **Task**: Add structured logging to rollback+reraise paths in 3 storage/memory modules while preserving exact transaction semantics.
- **Files modified**:
  - `memory_service/service.py:56-66`: Added `import logging` and module logger; wrapped `_managed_connection` except block with `logger.exception(f"Database operation failed... rolling back")` capturing context (db_path).
  - `core/storage/sqlite_store.py:37-48`: Same pattern for `SQLiteMetadataStore._managed_connection` with contextual db_path in log message.
  - `core/storage/branch_trace_store.py:37-48`: Same pattern for `BranchTraceStore._managed_connection` with contextual db_path in log message.
- **Semantics preserved**: All three modules maintain identical rollback+reraise behavior (commit exception triggers rollback then re-raise); logging is side-effect-only and does not change exception propagation or transaction boundaries.
- **Test approach**: Existing tests for write_memory, create_run, record_node all pass and verify the rollback semantics are intact; logging presence verified via grep showing `logger.exception(...)` calls in all three except blocks.
- **Verification**:
  - LSP diagnostics: All 3 modified files clean (no new errors).
  - Targeted tests: 12 passed (6 MemoryService + 4 SQLiteMetadataStore + 2 BranchTraceStore tests).
  - Full regression: 559 passed, 3 warnings (matches healthy baseline; no regressions).
  - Logging pattern consistency: All three modules use identical `logger.exception()` call with contextual message and rolling-back semantics preserved.
- **Scope adherence**: Only added logging to the exact 3 rollback+reraise paths per plan; did not modify silent-swallow handlers (Task 7) or transaction boundaries; did not expand into repo-wide exception policy review.

## Wave 5 Task 14: stale doc reference cleanup

- README now points full-repo regression to `python3 -m pytest tests -q`; Task-17 acceptance stays on `./scripts/run_task17_acceptance.sh`.
- `dev_doc/reverse_engineered_spec.md` had the highest drift risk: old CLI commands, old scenario inventory, stale test-count prose, and removed file-path references. Constraining edits to concrete stale claims was enough; no architecture rewrite was needed.
- `dev_doc/reverse_engineered_architecture.md` now avoids brittle `main.py` samples and fixed `N=5/K=2` wording, using config-driven wording plus placeholder hashes instead.
- Historical ADR context for `main.py` / `orchestrator_rd_loop_engine` remains valid only in `dev_doc/adr/005-dual-architecture-cleanup.md`; operational docs should no longer mention them.
- Wave 5 Task 15 app smoke coverage can stay test-only: one focused `tests/test_app_smoke.py` file is enough to cover `app/api_main.py`, `app/startup.py`, `app/run_supervisor.py`, `app/query_services.py`, and `app/fastapi_compat.py` without widening scope.
- The strongest low-cost real-path assertion is `app.api_main` import + `/health` request under temp env roots; it exercises real `RunSupervisor()` initialization and repeated `build_runtime()` calls instead of pure mocks.

## Wave 5 Task 16: Environment Variable Documentation Alignment

- **Action**: Updated `dev_doc/config_env_mapping.md` to comprehensively document all 25 environment variables defined in `app/config.py`.
- **Scope clarification**:
  - `AGENTRD_*` (9 vars): App/runtime settings (paths, execution modes, observability)
  - `RD_AGENT_*` (16 vars): Model, loop, and reasoning behavior settings (LLM, MCTS, Layer-0 config, debug, experimental features)
- **Changes**:
  - Restructured as two tables organized by prefix role (previously flat 14-row table)
  - Added 12 missing vars: `RD_AGENT_MCTS_WEIGHT`, `RD_AGENT_MCTS_C_PUCT`, `RD_AGENT_MCTS_REWARD_MODE`, `RD_AGENT_LAYER0_N_CANDIDATES`, `RD_AGENT_LAYER0_K_FORWARD`, `RD_AGENT_PRUNE_THRESHOLD`, `RD_AGENT_DEBUG_MODE`, `RD_AGENT_DEBUG_SAMPLE_FRACTION`, `RD_AGENT_DEBUG_MAX_EPOCHS`, `RD_AGENT_HYPOTHESIS_STORAGE`, `RD_AGENT_LLM_PLANNING`
  - Enhanced descriptions with concrete examples and use-case context
  - Preserved original startup validation command at end
- **README.md**: No env-var-specific changes needed (existing `AGENTRD_ALLOW_LOCAL_EXECUTION` reference is valid and sole occurrence)
- **Verification**:
  - Acceptance test: All 25 documented vars confirmed in `app/config.py` ✓
  - Full regression: 564 passed, 3 warnings (healthy baseline, +5 new tests from earlier waves)
  - Single source of truth: config_env_mapping.md now comprehensive and authoritative
