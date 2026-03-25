# Phase 31: Finalization state interface enhancement and default external ports - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the finalization-state interface explicit enough that downstream callers can
reliably distinguish exploration from finalization, while reducing setup friction
by providing default implementations for external dependency ports such as holdout
and embedding. Phase 31 does NOT add new convergence capabilities — those belong
to Phases 26-28. It clarifies the existing state surface and lowers the entry
barrier for port injection.

</domain>

<decisions>
## Implementation Decisions

### Run lifecycle visibility — ExplorationMode extension
- Extend `ExplorationMode` enum with `FINALIZED = "finalized"`.
- Run lifecycle now follows: `EXPLORATION → CONVERGENCE → FINALIZED`.
- `MultiBranchService._try_finalize()` writes `FINALIZED` to run snapshot
  automatically when holdout finalization succeeds.
- `BranchBoardSnapshot.mode` synchronizes to `FINALIZED` alongside the run
  snapshot — the entire board surface reflects finalization state.
- Minimal change: no extra fields (no `is_finalized`, no `final_submission_id`).
  `ExplorationMode.FINALIZED` + existing `FinalSubmissionSnapshot` is sufficient.

### Default port implementations — centralized defaults module
- All default port implementations live in a new `v3/ports/defaults.py` (or
  `v3/ports/default_impls/` directory) — separate from the protocol definitions.
- **DefaultHoldoutSplitPort**: Real random shuffle + split of validation data
  into K folds. Replaces the opaque string-reference-only `StratifiedKFoldSplitter`
  as the production default.
- **DefaultEvaluationPort**: Parameterized implementation accepting `eval_fn:
  Callable` and `dataset_ref: str`. Reads fold partitions from the split port's
  output, runs `eval_fn` on the holdout partition. Does NOT re-implement split.
- **DefaultEmbeddingPort**: Research the lightest available embedding approach and
  integrate it. Researcher task to survey options (e.g., sentence-transformers
  MiniLM, TF-IDF vectors, hash-based). Pick the lightest that produces
  semantically meaningful vectors for interaction kernel scoring.

### rd_agent() entry behavior — graceful degradation
- Remove the `ValueError` when `holdout_evaluation_port` is missing.
- When holdout port is absent: silently fall back to Phase 27 convergence path
  (shortlist + merge). Add `finalization_skipped: true` to `structuredContent`
  response so callers know holdout finalization was not performed.
- When holdout port is present: proceed with full holdout finalization as today.

### Embedding-absent sharing — agent-driven candidate selection
- When `EmbeddingPort` is unavailable: degrade to agent-selected sharing
  candidates only. The agent determines which branches help the current branch
  and injects them via `branch_list` parameter in CLI tool calls.
- When `EmbeddingPort` is available: **hybrid retrieval** — union of interaction
  kernel computed candidates AND agent-selected candidates. Both pools merged,
  deduplicated.
- No `LLMJudgePort` needed. The agent IS the LLM judge. CLI tool surface accepts
  `branch_list` as an explicit sharing-candidates input parameter.

### State query convenience
- Adding `FINALIZED` to `ExplorationMode` is sufficient. No extra helper,
  service, or computed property needed. Callers check `run.exploration_mode`.
- Exploration round progress ("exploring round 3/20") integrated into existing
  `OperatorGuidance` current_state text generation. No new structured field.

### Finalization entry explicitness
- Add public `should_finalize(run_id) -> bool` method on `MultiBranchService`.
  Checks `current_round >= max_rounds` and holdout service availability.
- `_try_finalize()` stays private — internal to exploration round.
- `finalize_early()` stays public as-is.
- Both `should_finalize` and `finalize_early` exposed through CLI tool surface
  (rd-tool-catalog) so operators can query and trigger finalization from terminal.

### Claude's Discretion
- Exact `DefaultHoldoutSplitPort` shuffle and stratification strategy
- `DefaultEvaluationPort` error handling when eval_fn raises
- Exact CLI tool names and argument shapes for finalize commands
- Whether defaults module is a single file or a sub-package
- How `branch_list` parameter integrates into existing dispatch payload schema

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase boundary and constraints
- `.planning/ROADMAP.md` — Phase 31 entry, depends on Phase 30
- `.planning/REQUIREMENTS.md` — All v1.3 requirements complete; Phase 31 is
  interface/UX enhancement, not new capability
- `.planning/STATE.md` — Current continuity truth

### Phase 26-28 decisions (direct dependencies)
- `.planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-CONTEXT.md`
  — DAG layer, ExplorationMode enum definition, BranchBoardSnapshot.mode field,
  round tracking (current_round, max_rounds)
- `.planning/phases/28-aggregated-validation-with-holdout-calibration-and-standardized-ranking/28-CONTEXT.md`
  — Holdout port design (HoldoutSplitPort + EvaluationPort), FinalSubmissionSnapshot,
  auto-finalization trigger, StratifiedKFoldSplitter default, EmbeddingPort pattern

### Key source files to modify or extend
- `v3/contracts/exploration.py` — Add `FINALIZED` to `ExplorationMode` enum
- `v3/orchestration/multi_branch_service.py` — Write FINALIZED mode on successful
  finalization, add public `should_finalize()`, update `_try_finalize()` to set mode
- `v3/orchestration/operator_guidance.py` — Add round progress to guidance text
- `v3/entry/rd_agent.py` — Remove holdout_evaluation_port ValueError, add
  `finalization_skipped` to response, accept `branch_list` parameter
- `v3/ports/holdout_port.py` — Keep protocol definitions; defaults move out
- `v3/ports/embedding_port.py` — Keep protocol definitions; default moves out
- `v3/ports/defaults.py` (NEW) — DefaultHoldoutSplitPort, DefaultEvaluationPort,
  DefaultEmbeddingPort
- `v3/orchestration/branch_share_service.py` — Hybrid retrieval: merge interaction
  kernel candidates with agent-injected branch_list; degrade gracefully when
  EmbeddingPort absent
- `v3/entry/tool_catalog.py` — Add should_finalize and finalize_early CLI tools

### Port pattern references
- `v3/ports/state_store.py` — StateStorePort protocol pattern
- `v3/ports/holdout_port.py` — HoldoutSplitPort + EvaluationPort protocols
- `v3/ports/embedding_port.py` — EmbeddingPort protocol + EmbeddingUnavailableError

### Verification anchors
- `tests/test_phase28_integration.py` — Finalization lifecycle tests
- `tests/test_phase28_holdout_service.py` — HoldoutValidationService tests
- `tests/test_phase29_entry_wiring.py` — Entry-layer wiring tests
- `tests/test_phase27_interaction_kernel.py` — Interaction kernel tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ExplorationMode` (`v3/contracts/exploration.py`): StrEnum with EXPLORATION,
  CONVERGENCE — direct extension point for FINALIZED.
- `HoldoutValidationService` (`v3/orchestration/holdout_validation_service.py`):
  Full finalization pipeline. `_try_finalize` and `finalize_early` already call it.
- `StratifiedKFoldSplitter` (`v3/ports/holdout_port.py`): Current default splitter
  producing opaque string references. To be replaced by DefaultHoldoutSplitPort
  with real data splitting.
- `StubEmbeddingPort` (`v3/ports/embedding_port.py`): Returns all-zero vectors.
  To be replaced by DefaultEmbeddingPort with lightweight real embedding.
- `EmbeddingUnavailableError` (`v3/ports/embedding_port.py`): Existing error type
  for graceful degradation when embedding service is unreachable.
- `OperatorGuidance` (`v3/contracts/operator_guidance.py`): Reusable contract for
  operator-facing state summaries. Round progress text goes here.
- `build_finalization_guidance` (`v3/orchestration/operator_guidance.py`): Already
  builds finalization summary — extend with mode transition context.
- `MultiBranchService._try_finalize` (`v3/orchestration/multi_branch_service.py`):
  Budget-exhaustion check + holdout call. Add FINALIZED mode write here.
- `MultiBranchService.finalize_early`: Public early finalization entry. Also needs
  FINALIZED mode write.
- `BranchShareService.compute_sharing_candidates` (`v3/orchestration/branch_share_service.py`):
  Current interaction-kernel-based sharing. Extend to accept agent-injected candidates
  and merge with kernel results.

### Established Patterns
- Services depend on `StateStorePort` protocol — new defaults follow same pattern.
- All contracts use Pydantic BaseModel with `ConfigDict(extra="forbid", frozen=True)`.
- Port protocols in `v3/ports/`, implementations can be stubs, defaults, or injected.
- CLI tools defined in `v3/entry/tool_catalog.py` with structured request/response.
- Branch decisions recorded as `BranchDecisionSnapshot` for traceability.

### Integration Points
- `MultiBranchService._try_finalize()` — write FINALIZED mode on success
- `MultiBranchService.finalize_early()` — write FINALIZED mode on success
- `rd_agent()` multi-branch path — remove ValueError, add finalization_skipped
- `BranchShareService` — accept and merge agent-injected branch_list
- `tool_catalog.py` — register should_finalize + finalize_early CLI tools
- `operator_guidance.py` — embed round/max_rounds in current_state text

</code_context>

<specifics>
## Specific Ideas

- The "agent IS the LLM judge" insight means no new protocol for LLM-based sharing
  decisions. The agent operating the pipeline decides which branches help the current
  branch and passes them as explicit parameters. This keeps V3 as pure orchestration.
- Hybrid retrieval (kernel ∪ agent) is more robust than either alone: the kernel
  catches structural similarity the agent might miss, while the agent catches semantic
  relevance the kernel might miss.
- DefaultEmbeddingPort research should prioritize: (1) zero external service dependency,
  (2) < 100MB model size, (3) reasonable semantic quality for hypothesis comparison.
  Candidates: sentence-transformers MiniLM, TF-IDF, hash-based bag-of-words.
- The `finalization_skipped: true` marker lets downstream tooling (e.g., operator
  dashboards) clearly distinguish "run completed with holdout" from "run completed
  via convergence fallback."

</specifics>

<deferred>
## Deferred Ideas

- Cross-run finalization comparison (requires comparable holdout sets — hard)
- Visual finalization dashboard with interactive ranking table
- Adaptive K selection for holdout folds based on candidate pool size
- Ensemble submission (combine Top-N candidates instead of selecting one)
- Auto-retry finalization when transient port failures occur
- Finalization rollback (undo FINALIZED state and resume exploration)

</deferred>

---

*Phase: 31-finalization-state-interface-enhancement-and-default-external-ports*
*Context gathered: 2026-03-25*
