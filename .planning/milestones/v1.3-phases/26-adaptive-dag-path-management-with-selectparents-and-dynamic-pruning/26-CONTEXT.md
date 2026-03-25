# Phase 26: Adaptive DAG path management with SelectParents and dynamic pruning - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the first layer of the R&D-Agent convergence mechanism: an independent
DAG topology layer over the existing branch model, a SelectParents service that
picks parent nodes based on validation quality / generalization / overfitting risk
/ budget-aware diversity weighting, dynamic pruning that triggers automatically
after each exploration round with time-aware multi-signal criteria, and first-layer
diversity enforcement via structured hypothesis categories and entropy constraints.

Phase 26 does NOT implement cross-branch communication (Phase 27), multi-trace
merge (Phase 27), or aggregated holdout validation (Phase 28). However, the DAG
layer, scoring extensions, and hypothesis model are designed to naturally extend
into those phases without breaking changes.

</domain>

<decisions>
## Implementation Decisions

### SelectParents — new independent service
- Create `SelectParentsService` as a separate service from `SelectionService`.
  - `SelectionService` answers "which branch to advance next" (unchanged).
  - `SelectParentsService` answers "which past nodes should feed context into a
    new iteration."
- Three-dimensional signal model for parent selection:
  1. **Core quality**: validation score (from `result_quality`), `generalization_gap`
     (validation vs training score difference — also considers convergence speed
     and feature representation robustness), `overfitting_risk` (composite of:
     cross-fold consistency, score trend direction, and presence of anomalously
     high scores that may indicate data leakage or extreme hyperparameter
     sensitivity).
  2. **Strategic planning**: `budget_ratio` derived from `current_round / max_rounds`
     on `RunSnapshot`. Diversity weight uses **cosine decay**: early rounds favor
     diversity, late rounds favor certainty. `max_rounds` defaults to 20.
  3. **Complementarity**: signal reserved for Phase 27 merge stage. Phase 26
     captures the field but does not compute it.
- Dynamic parent count based on task phase:
  - **Early stage** (budget_ratio < 0.3): multiple parents (default K=3) to
    maximize diversity.
  - **Iteration stage** (0.3 <= budget_ratio < 0.8): single best parent (K=1),
    greedy exploitation within a branch.
  - **Merge stage** (budget_ratio >= 0.8): multiple complementary parents —
    Phase 27 implements this; Phase 26 falls back to K=1.
- Parent info is used by downstream stages as:
  1. **Reasoning context**: parent experiment feedback (success/failure reasons)
     injected into the new iteration's hypothesis prompt.
  2. **Code base**: parent code artifacts as the starting point for implementation.
  3. **Performance benchmark**: parent scores as the baseline — a child node must
     improve over its parents to count as progress.

### DAG layer — independent graph topology
- Create an independent DAG Node layer, separate from the branch lifecycle model.
  Branch stays focused on execution state (active/superseded/completed); DAG
  tracks topology (parent-child, depth, path metrics).
- **DAGNodeSnapshot**: `node_id`, `run_id`, `branch_id`, `parent_node_ids: list[str]`,
  `depth: int`, `node_metrics: NodeMetrics` (validation_score, generalization_gap,
  overfitting_risk, diversity_score).
- **DAGEdgeSnapshot**: `source_node_id`, `target_node_id`, `edge_type` (PARENT,
  SHARED, MERGED), `weight: float`.
- **DAGService**: graph operations — `get_ancestors`, `get_descendants`,
  `get_frontier` (leaf nodes), `get_depth`, `compute_path`.
- Stored via `StateStorePort` (new methods for DAG CRUD).
- **Phase 26 scope**: only PARENT edges. SHARED and MERGED edge types are defined
  in the enum but not used until Phase 27.

### BranchScore extension
- Extend `BranchScore` with two new optional fields:
  - `generalization_gap: float = 0.0` — difference between validation and training
    scores. Higher = worse generalization.
  - `overfitting_risk: float = 0.0` — composite signal from score trend direction
    and cross-fold variance. Range [0, 1], higher = more risk.
- Existing `exploration_priority` and `result_quality` unchanged.
- `scoring_service.py` extended to compute these new signals when stage results
  provide training/validation split data.

### RunSnapshot extension
- Add `current_round: int = 0` and `max_rounds: int = 20` to `RunSnapshot`.
- `budget_ratio` computed as `current_round / max_rounds`.
- `MultiBranchService.run_exploration_round` increments `current_round` after each
  round completes.

### Dynamic pruning — automatic after each exploration round
- **Trigger**: `MultiBranchService.run_exploration_round` calls pruning
  automatically after dispatching and selecting.
- **Multi-signal criteria** (replaces pure relative_threshold cutoff):
  1. Time-aware dynamic threshold via cosine decay: early rounds
     `relative_threshold ≈ 0.3` (loose), late rounds `≈ 0.7` (strict).
     Mirrors the SelectParents diversity weight curve.
  2. Generalization stability: branches with low `generalization_gap` and
     consistent cross-fold scores are protected even if absolute score is lower.
  3. Anti-overfitting: branches with high `overfitting_risk` AND declining score
     trend are pruned preferentially.
  4. **Complementarity preservation**: deferred to Phase 27. Phase 26 uses only
     signals 1-3.
- **Safety constraint**: `min_active_branches = 2`. Never prune below this.
- Upgrade existing `BranchPruneService` to support the new multi-signal criteria
  while remaining backward-compatible with the simple threshold mode.

### First-layer diversity — structured hypotheses + entropy constraint
- Upgrade `branch_hypotheses` from `list[str]` to `list[HypothesisSpec]`.
- **HypothesisSpec** model:
  - `label: str` — human-readable hypothesis name (e.g., "ResNet18 transfer")
  - `approach_category: ApproachCategory` — fixed enum
  - `target_challenge: str` — free-text description of the bottleneck addressed
    (e.g., "data imbalance", "feature engineering"). In Phase 26 this is
    informational; in future phases it enables problem-dimension alignment
    scoring to ensure branches attack distinct technical bottlenecks.
  - `rationale: str` — why this direction is worth exploring
- **ApproachCategory** fixed enum:
  `FEATURE_ENGINEERING`, `MODEL_ARCHITECTURE`, `DATA_AUGMENTATION`, `ENSEMBLE`,
  `LOSS_FUNCTION`, `TRAINING_STRATEGY`, `OTHER`.
- **Category increment constraint**: at most 1 branch per category in the first
  layer. If a new hypothesis has the same category as an existing branch, it is
  rejected or the user is warned.
- **diversity_score**: computed as the Shannon entropy of the category distribution
  across active first-layer branches. Stored in DAGNodeSnapshot.node_metrics.
- Phase 26 only implements category + entropy. Embedding-based semantic similarity,
  virtual evaluation (LLM novelty scoring), and interaction kernel negative feedback
  are deferred.

### Claude's Discretion
- Exact cosine decay formula parameters (amplitude, phase shift)
- Internal implementation of DAGService graph traversal algorithms
- How HypothesisSpec integrates with the existing route_user_intent auto-hypothesis
  generation (prompt engineering details)
- Whether to use a separate `v3/algorithms/dag.py` or keep graph logic in DAGService
- Error handling strategy when parent nodes are pruned before child completes

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase boundary and requirements
- `.planning/ROADMAP.md` — Phase 26 entry and v1.3 milestone context
- `.planning/REQUIREMENTS.md` — All v1 requirements complete; Phase 26 adds
  convergence mechanism capabilities
- `.planning/STATE.md` — Current continuity truth

### Prior phase decisions that still apply
- `.planning/phases/25-fix-qa-discovered-operator-guidance-and-multi-branch-ux-gaps/25-CONTEXT.md`
  — Multi-branch UX defaults, exploration mode, branch_hypotheses exposure,
  stage materialization, recovery_assessment rename. Phase 26 builds directly
  on these foundations.
- `.planning/phases/22-intent-routing-and-continuation-control/22-CONTEXT.md`
  — Locked routing fields and intent-first entry model
- `.planning/phases/23-preflight-and-state-truth-hardening/23-CONTEXT.md`
  — Locked preflight truth, blocked-vs-executable semantics

### Key source files to modify or extend
- `v3/orchestration/selection_service.py` — Existing PUCT-based selection (unchanged
  but referenced by new SelectParentsService)
- `v3/orchestration/scoring_service.py` — Extend with generalization_gap and
  overfitting_risk computation
- `v3/orchestration/branch_prune_service.py` — Upgrade to multi-signal pruning
- `v3/algorithms/prune.py` — Extend cutoff algorithm with time-aware threshold
- `v3/orchestration/multi_branch_service.py` — Add auto-prune trigger after
  exploration rounds, increment current_round
- `v3/contracts/exploration.py` — Add DAGNodeSnapshot, DAGEdgeSnapshot,
  HypothesisSpec, ApproachCategory, NodeMetrics
- `v3/contracts/branch.py` — Extend BranchScore with generalization_gap,
  overfitting_risk
- `v3/contracts/run.py` or equivalent — Add current_round, max_rounds to RunSnapshot
- `v3/ports/state_store.py` — Add DAG CRUD methods to StateStorePort
- `v3/entry/rd_agent.py` — Integrate HypothesisSpec into route_user_intent and
  rd_run_start

### Verification anchors
- `tests/test_phase16_selection.py` — Existing selection tests
- `tests/test_phase16_convergence.py` — Existing convergence tests
- `tests/test_phase16_branch_lifecycle.py` — Branch lifecycle tests
- `tests/test_phase25_stage_materialization.py` — Stage materialization tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SelectionService` (`v3/orchestration/selection_service.py`): PUCT-based branch
  selection with BranchSelectionSignal and projected scores. SelectParentsService
  can reuse the scoring/projection infrastructure.
- `BranchPruneService` (`v3/orchestration/branch_prune_service.py`): existing
  pruning with BranchDecisionSnapshot recording. Upgrade in-place.
- `prune_branch_candidates` (`v3/algorithms/prune.py`): self-contained algorithm.
  Extend with time-aware threshold and generalization signals.
- `ScoringService` (`v3/orchestration/scoring_service.py`): `selection_potential`,
  `project_branch_score`, softmax prior. Extend with new signal computation.
- `BranchDecisionKind` enum already has FORK, SELECT, PRUNE, SHARE, SHORTLIST,
  MERGE — no new enum values needed for Phase 26 decisions.
- `BranchResolution` enum already has OPEN, PRUNED, SHORTLISTED, MERGED, REJECTED.
- `MultiBranchService.run_exploration_round` — natural injection point for
  auto-pruning and round counting.
- `PuctSelectionAdapter` and `v3/algorithms/puct.py` — PUCT math reusable for
  SelectParents ranking.

### Established Patterns
- Services depend on `StateStorePort` protocol — DAGService should follow same
  pattern.
- Branch decisions recorded as `BranchDecisionSnapshot` — parent selection
  decisions should use the same pattern (kind=SELECT with parent context).
- Contracts live in `v3/contracts/`, services in `v3/orchestration/`,
  algorithms in `v3/algorithms/`.
- All new contracts use Pydantic BaseModel with `ConfigDict(extra="forbid", frozen=True)`.

### Integration Points
- `MultiBranchService.run_exploration_round` — add auto-prune call and
  current_round increment.
- `rd_agent.py` route_user_intent — upgrade branch_hypotheses from strings to
  HypothesisSpec objects.
- `tool_catalog.py` rd_run_start spec — expose HypothesisSpec schema.
- `StageTransitionService` — when materializing next stage, create corresponding
  DAG node.

</code_context>

<specifics>
## Specific Ideas

- SelectParents is NOT "select next branch" — it is "which past results should
  feed into a new iteration's context." These are fundamentally different decisions
  serving different consumers.
- The DAG layer must be a first-class abstraction because Phases 27-28 need
  efficient graph traversal for cross-branch communication and aggregated validation.
- Cosine decay for both diversity weight (SelectParents) and pruning threshold
  creates a symmetric exploration→exploitation curve across the run lifecycle.
- HypothesisSpec with fixed categories is the Phase 26 implementation of diversity.
  The long-term vision includes embedding-based semantic similarity, virtual
  evaluation (LLM novelty scoring), and interaction kernel negative feedback —
  these should be achievable by extending HypothesisSpec and adding a
  DiversityService in future phases.

</specifics>

<deferred>
## Deferred Ideas

### Phase 27: Cross-branch communication + Multi-trace Merge
- SHARED edge type in DAG (cross-branch experience sharing)
- MERGED edge type in DAG (unified solution synthesis)
- Global best injection into branch context
- Probabilistic sampling kernel for cross-branch experience exchange
- Complementarity signal in SelectParents (component complementarity for merge)
- Merge-stage parent selection with multiple complementary parents
- Interaction kernel negative feedback for diversity enforcement

### Phase 28: Aggregated Validation and Holdout Calibration
- Collect top candidates from all exploration branches via DAG frontier traversal
- Create synthetic holdout set (90-10 split) for isolated re-evaluation
- Standardized ranking across all DAG leaf nodes
- Single-best submission selection
- Overfitting prevention through multi-checkpoint validation

### Future (beyond v1.3)
- Embedding-based semantic similarity for hypothesis diversity (requires embedding
  service integration)
- Virtual evaluation filtering: LLM novelty scoring before development stage
- Interaction kernel with adjustable potential energy for diversity enforcement
- Cross-run DAG connections (learning from previous runs)
- Visual DAG rendering for operator inspection
- Problem-dimension alignment scoring: quantify whether branches target distinct
  technical bottlenecks using `target_challenge` fields and systematic problem
  identification output

</deferred>

---

*Phase: 26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning*
*Context gathered: 2026-03-23*
