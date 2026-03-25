# Phase 28: Aggregated validation with holdout calibration and standardized ranking - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement layer 4 of the R&D-Agent convergence mechanism: aggregated validation
that prevents overfitting to the primary validation set through K-fold holdout
calibration, parallel re-evaluation via abstract ports, and standardized ranking
for final submission selection. Phase 28 activates automatically when exploration
budget is exhausted (`current_round >= max_rounds`) or on-demand when the operator
triggers early finalization.

Phase 28 completely replaces Phase 27's proxy `validate_merge_holdout` with a
proper holdout validation pipeline. It does NOT add new exploration, sharing, or
merge capabilities — those belong to Phases 26-27.

</domain>

<decisions>
## Implementation Decisions

### Holdout set construction — abstract split contract
- V3 is the orchestration layer, not the data layer. Holdout construction is
  abstracted behind a `HoldoutSplitPort` protocol.
- `HoldoutSplitPort.split()` returns `list[FoldSpec]` (K=5 folds). Each `FoldSpec`
  contains opaque data references (paths or identifiers) for train and holdout
  partitions.
- Phase 28 provides a `StratifiedKFoldSplitter` as the default implementation.
- Two independent ports with different lifecycles:
  - `HoldoutSplitPort`: called once per finalization — produces K fold specs.
  - `EvaluationPort`: called once per candidate per fold — evaluates a candidate
    on a specific fold's holdout partition and returns a score.
- Follows the established port pattern (`StateStorePort`, `EmbeddingPort`).

### Phase 27 proxy replacement
- `validate_merge_holdout` in `v3/algorithms/merge.py` is completely replaced by
  the `HoldoutValidationService`. The merge stage now calls the same holdout
  pipeline instead of the simple score comparison proxy.
- All call sites of `validate_merge_holdout` are updated to use the new service.

### Candidate collection and activation
- **Activation trigger**: Dual-mode — automatically when `current_round >= max_rounds`
  in `MultiBranchService.run_exploration_round`, plus an explicit early-finalization
  entry point for operators who want to stop exploration early.
- **Candidate pool**: Frontier nodes (leaf nodes from `DAGService.get_frontier`) plus
  MERGED nodes. Both surviving individual branches and merge results compete.
- **Quality threshold filter**: Before K-fold evaluation, candidates below the median
  `validation_score` of the pool are filtered out. This halves the evaluation cost
  (each candidate × 5 folds).

### Ranking methodology
- **Primary sort**: Mean holdout score across 5 folds (higher is better).
- **Tiebreaker**: Standard deviation across folds (lower is better — prefer stability).
- **Scope**: Single run internal ranking. No cross-run comparison (each run has its
  own holdout data, making scores non-comparable across runs).
- **Result storage**: Extend `NodeMetrics` with `holdout_mean: float` and
  `holdout_std: float` fields (backward-compatible defaults of 0.0). Holdout
  results are persisted directly in the DAG node metrics.

### Final output and submission
- **Single best**: Phase 28 selects the rank #1 candidate as the final submission.
  Could be a MERGED node or an independent branch's frontier node.
- **New contract**: `FinalSubmissionSnapshot` — records `winner_node_id`,
  `winner_branch_id`, `holdout_mean`, `holdout_std`, full ranked list of all
  evaluated candidates, and DAG ancestry chain (source path traceability).
- **Operator presentation**: Reuses the Phase 24 `OperatorGuidance` contract and
  renderer to display a finalization summary (winner, holdout score, source branch,
  ranking table) without adding a new tool surface.

### Claude's Discretion
- Exact `FoldSpec` data model fields beyond train/holdout references
- `StratifiedKFoldSplitter` internal stratification strategy
- `EvaluationPort` protocol signature details (sync vs async, timeout handling)
- How `MultiBranchService` integrates the auto-finalization trigger
- Error handling when all candidates fail holdout evaluation
- Exact quality threshold computation (median vs percentile)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase boundary and constraints
- `.planning/ROADMAP.md` — Phase 28 entry, success criteria, and Phase 26/27
  constraints that Phase 28 must honor
- `.planning/REQUIREMENTS.md` — v1.3 convergence requirements context
- `.planning/STATE.md` — Current continuity truth

### Phase 26-27 decisions (direct dependencies)
- `.planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-CONTEXT.md`
  — DAG layer design, NodeMetrics fields, BranchScore extensions, round tracking
  (`current_round`, `max_rounds`), DAG frontier traversal. Phase 28 reads all
  of these directly.
- `.planning/phases/27-cross-branch-communication-and-multi-trace-solution-merge/27-CONTEXT.md`
  — MERGED edge type activation, `validate_merge_holdout` proxy gate (to be replaced),
  complementary merge pipeline, holdout validation basic version. Phase 28 replaces
  the proxy and adds rigorous K-fold evaluation.

### Key source files to modify or extend
- `v3/algorithms/merge.py` — Remove `validate_merge_holdout`; `MergeDesign.holdout_score`
  field may need rethinking since holdout is now multi-fold
- `v3/orchestration/branch_merge_service.py` — Update all `validate_merge_holdout`
  call sites to use `HoldoutValidationService`
- `v3/contracts/exploration.py` — Extend `NodeMetrics` with `holdout_mean`,
  `holdout_std`; add `FinalSubmissionSnapshot`
- `v3/orchestration/dag_service.py` — `get_frontier` used for candidate collection
- `v3/orchestration/convergence_service.py` — Shortlist construction; may need
  integration with holdout ranking
- `v3/orchestration/multi_branch_service.py` — Add auto-finalization trigger when
  `current_round >= max_rounds`; add early-finalization entry point
- `v3/orchestration/scoring_service.py` — May extend with holdout-aware scoring
- `v3/ports/state_store.py` — Add CRUD methods for `FinalSubmissionSnapshot`
- `v3/contracts/run.py` — `current_round`, `max_rounds` already present; Phase 28
  reads these for activation

### Port pattern references
- `v3/ports/state_store.py` — `StateStorePort` protocol pattern to follow
- `v3/ports/embedding.py` (or equivalent) — `EmbeddingPort` pattern for
  `HoldoutSplitPort` and `EvaluationPort` design

### Verification anchors
- `tests/test_phase16_convergence.py` — Existing convergence tests
- `tests/test_phase27_lifecycle.py` — Phase 27 lifecycle integration tests
- `tests/test_phase16_branch_lifecycle.py` — Branch lifecycle tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DAGService.get_frontier` (`v3/orchestration/dag_service.py`): Collects frontier
  (leaf) nodes for candidate pool assembly. Already used by share service.
- `ConvergenceService.shortlist` (`v3/orchestration/convergence_service.py`): Builds
  quality-ordered shortlists from active branch board. Candidate filtering logic
  can be adapted.
- `NodeMetrics` (`v3/contracts/exploration.py`): Already carries `validation_score`,
  `generalization_gap`, `overfitting_risk`, `complementarity_score`. Natural
  extension point for `holdout_mean` and `holdout_std`.
- `validate_merge_holdout` (`v3/algorithms/merge.py`): Explicitly labeled "Phase 28
  can replace this." Simple `merged_score >= best_single_score` comparison — the
  exact target for replacement.
- `OperatorGuidance` (Phase 24): Reusable contract and renderer for finalization
  summary presentation.
- `cosine_decay` (`v3/algorithms/decay.py`): Available if threshold computation
  needs budget-aware curves.
- `BranchDecisionKind.SHORTLIST` and `BranchDecisionKind.MERGE` — existing enum
  values for recording finalization decisions.

### Established Patterns
- Services depend on `StateStorePort` protocol — `HoldoutValidationService`,
  `HoldoutSplitPort`, and `EvaluationPort` should follow same pattern.
- All new contracts use Pydantic BaseModel with `ConfigDict(extra="forbid", frozen=True)`.
- Contracts in `v3/contracts/`, services in `v3/orchestration/`, algorithms in
  `v3/algorithms/`, ports in `v3/ports/`.
- Branch decisions recorded as `BranchDecisionSnapshot` — finalization decisions
  should use the same pattern.

### Integration Points
- `MultiBranchService.run_exploration_round` — add auto-finalization check after
  round increment when `current_round >= max_rounds`.
- `BranchMergeService.merge_with_complementarity` — replace `validate_merge_holdout`
  call with `HoldoutValidationService`.
- `DAGService.update_node_metrics` — update frontier nodes with holdout results.
- `rd_agent.py` — may need a finalization entry point for operator-triggered early
  finalization.

</code_context>

<specifics>
## Specific Ideas

- Phase 28 is the "private leaderboard" of the R&D-Agent loop — analogous to Kaggle's
  final evaluation on unseen data to prevent overfitting to the public validation set.
- The two-port design (HoldoutSplitPort + EvaluationPort) keeps V3 as a pure
  orchestration layer. The actual data splitting and model evaluation are injected
  by the caller, which could be a local pytest runner, a remote Kaggle API, or a mock.
- K=5 fold cross-validation provides robustness: the mean captures performance while
  the standard deviation captures stability. The primary-sort-by-mean + tiebreak-by-std
  ranking prefers solutions that are both good AND consistent.
- Quality threshold filtering (median cutoff) before K-fold evaluation is a
  cost-optimization: if you have 10 candidates, you evaluate ~5 × 5 folds = 25 calls
  instead of 10 × 5 = 50. The bottom half was unlikely to win anyway.
- `FinalSubmissionSnapshot` carries the full DAG ancestry chain so operators can trace
  exactly how the winning solution evolved from initial hypotheses through sharing,
  pruning, and merging.

</specifics>

<deferred>
## Deferred Ideas

### Future (beyond v1.3)
- Cross-run standardized ranking with Z-score normalization (requires comparable
  holdout sets across runs — fundamentally hard)
- Multi-checkpoint comparison across training history (requires checkpoint storage
  and replay infrastructure)
- Ensemble submission (combine Top-N candidates instead of selecting one)
- Visual ranking dashboard with fold-level score breakdowns
- Automated submission to external platforms (Kaggle API integration)
- Adaptive K selection based on candidate pool size and compute budget

</deferred>

---

*Phase: 28-aggregated-validation-with-holdout-calibration-and-standardized-ranking*
*Context gathered: 2026-03-24*
