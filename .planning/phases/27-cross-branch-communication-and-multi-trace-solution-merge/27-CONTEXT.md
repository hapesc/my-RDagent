# Phase 27: Cross-branch communication and multi-trace solution merge - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement layers 2-3 of the R&D-Agent convergence mechanism: cross-branch
collaborative communication (global best injection + probabilistic sampling
exchange via interaction kernel) and multi-trace solution merge (complementary
component identification + LLM-driven unified synthesis + holdout validation).

Phase 27 activates the SHARED and MERGED edge types defined in Phase 26,
implements the complementarity signal reserved in SelectParents, adds pruning
signal 4 (functional preservation), and delivers a complete merge-to-validation
closed loop. Phase 28 is reduced to advanced optimization (rigorous parallel
validation, multi-checkpoint comparison, cross-run ranking).

</domain>

<decisions>
## Implementation Decisions

### Cross-branch sharing — global best injection
- **Injection timing**: After each branch independently generates hypotheses
  through the propose stage, before the candidate pool is finalized.
- **Global best definition**: The solution with the highest validation score and
  most robust performance across all parallel branches' experiment history.
- **Candidate pool structure** ($H_{cand}$): Three-part composition:
  1. $h_c$ — current branch's original hypotheses (local context)
  2. $h^*$ — global best solution extracted from cross-branch search
  3. $h_s$ — probabilistic sample set from other branches via interaction kernel
- **Adaptive processing**: LLM executes one of three actions (non-forced):
  - **Select**: Adopt global best directly if clearly superior
  - **Modify**: Extract specific advantages (e.g., a loss function) and integrate
    into current branch's solution while preserving branch-specific strengths
  - **Create**: Synthesize a novel improved hypothesis combining global experience
    with local exploration
- **Injection point**: Propose stage entry — candidate pool injected as prompt
  context for hypothesis generation.
- **Sharing records**: Dual recording — `BranchDecisionSnapshot(kind=SHARE)` for
  decision audit trail + DAG `SHARED` edge for topology traceability.

### Probabilistic interaction kernel
- **Interaction potential** formula:
  $U_{ij} = \alpha S_{ij} e^{-\gamma L} + \beta \tanh(\Delta_{ij})$
  - $S_{ij}$: Cosine similarity between hypothesis text embeddings (semantic
    relatedness — favors topically similar ideas)
  - $\Delta_{ij}$: Score difference (global best score minus current branch best
    score — favors higher-performing hypotheses)
  - $e^{-\gamma L}$: Time decay factor where $L$ = DAG node depth
    (`DAGNodeSnapshot.depth`). Early rounds: similarity matters for finding
    relevant inspiration. Late rounds: similarity weight decays rapidly, score
    information dominates, forcing convergence toward high-score solutions.
- **Weight normalization**: Softmax over $U_{ij}$ produces probability distribution
  $p_{ij} = \exp(U_{ij}) / \sum_k \exp(U_{ik})$
- **Sampling**: $h_s \sim \text{Categorical}(p_{ij})$
- **Sample count**: Dynamic K following budget_ratio three-stage pattern (aligned
  with SelectParents): early K=3 diverse exploration, mid K=1 focused, late K=2
  merge-oriented.
- **Embedding source**: External embedding service (e.g., OpenAI text-embedding-3)
  for hypothesis text vectorization.
- **Hyperparameters** $\alpha$, $\beta$, $\gamma$: Configurable with sensible
  defaults (e.g., $\alpha=0.5$, $\beta=0.3$, $\gamma=0.1$ as starting point).

### Anti-convergence (diversity preservation)
Four-layer intrinsic mechanism — no separate penalty term needed:
1. **Probabilistic sampling randomness**: Softmax + categorical sampling means
   different branches draw different references even from the same global pool.
2. **LLM adaptive processing**: Select/Modify/Create is non-deterministic; agents
   frequently choose Modify (extract one advantage, preserve branch identity).
3. **Time decay** $e^{-\gamma L}$: Early rounds allow similarity-driven sharing;
   late rounds shift to score-driven convergence. Branches converge on
   "performance outcomes" but can diverge on "implementation means."
4. **First-layer diversity** (Phase 26): Category uniqueness constraint +
   Shannon entropy already provide foundational separation.

### Complementarity quantification
Two core metrics working together:
1. **Component Class Coverage**: Each hypothesis component tagged with
   `ComponentClass` (DataLoadSpec, FeatureEng, Model, Ensemble, Workflow).
   Complementarity = distribution difference of high-score components across
   branches. Branch A excelling in FeatureEng + Branch B excelling in Model =
   maximum complementarity.
2. **Semantic Distance**: Reuses interaction kernel — complementarity proportional
   to $(1 - S_{ij})$. Higher semantic distance between two high-scoring branches
   = higher fusion potential.

Two dimensions work together:
- `ApproachCategory` (Phase 26) = branch exploration direction (FC-Planning).
  Determines "what core challenge are we researching."
- `ComponentClass` (Phase 27, new) = solution internal structure (FC-Reasoning
  Pipeline). Marks "which pipeline stage is being modified."

### SelectParents upgrade for merge stage
- When `budget_ratio >= 0.8` (merge stage), SelectParents explicitly seeks
  non-overlapping component parents instead of falling back to K=1.
- If the first selected parent is strong in "Model optimization", the system
  prioritizes candidates with "FeatureEng" breakthroughs for the second parent.
- Both ApproachCategory and ComponentClass fed to LLM for parent selection
  reasoning.

### Pruning signal 4 — functional preservation
- Before pruning a low-score branch, check if it contains unique successful
  components not present in the current global best path.
- If a branch has a novel component (e.g., a unique loss function) absent from
  all higher-scoring branches, exempt it from pruning to preserve its value as
  a future "merge fragment."
- Extends Phase 26's multi-signal pruning (signals 1-3) with signal 4.

### Multi-trace merge mechanism
- **Trigger**: Final stage of exploration cycle when `budget_ratio >= 0.8`.
  Sequence: Draft → Improvement → Final Merge → Submit.
- **Complementary identification**: Analyze each branch's feedback history to
  identify strengths across dimensions. System searches branches with different
  ApproachCategory and examines their high-score ComponentClass entries.
- **LLM-driven synthesis** (three atomic operations):
  - **Select**: Retain the most robust, complementary solutions from different
    traces.
  - **Modify**: Adapt successful patterns from other traces (e.g., an efficient
    `AsymmetricLoss`) to the current task context with code-level rewriting.
  - **Create**: Synthesize a new unified code version integrating complementary
    component advantages.
- **Weakness elimination**: Input each branch's failure analysis and success
  feedback from Memory Context. LLM actively discards components that caused
  overfitting or code errors, keeping only validated "success fragments."
- **Conflict resolution**: When two branches modify the same ComponentClass,
  select the more robust one by Valid Score, or LLM attempts Modify adaptation.
- **DAG representation**: Merged result creates a new DAGNodeSnapshot with MERGED
  edges connecting all source branch nodes. Full topology traceability preserved.
- **Holdout validation**: Merged candidate solutions re-evaluated on a synthetic
  holdout set. Only the most robust solution survives. (Phase 28 adds advanced
  parallel validation and multi-checkpoint comparison on top of this.)

### Claude's Discretion
- Exact hyperparameter default values for $\alpha$, $\beta$, $\gamma$
- Internal implementation of ComponentClass tagging (LLM prompt engineering vs
  heuristic classification)
- EmbeddingPort abstraction design for external embedding service integration
- Error handling when parent nodes are pruned during merge preparation
- Exact holdout split ratio and validation methodology (Phase 27 basic version)
- How MergeAdapter protocol evolves to support LLM-driven synthesis

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase boundary and constraints
- `.planning/ROADMAP.md` — Phase 27 entry, success criteria, and Phase 26
  constraints that Phase 27 must honor
- `.planning/REQUIREMENTS.md` — v1.3 convergence requirements context
- `.planning/STATE.md` — Current continuity truth

### Phase 26 decisions (direct dependencies)
- `.planning/phases/26-adaptive-dag-path-management-with-selectparents-and-dynamic-pruning/26-CONTEXT.md`
  — DAG layer design, SelectParents three-dimensional signal model (complementarity
  reserved), dynamic pruning signals 1-3, first-layer diversity via HypothesisSpec,
  BranchScore extensions, round tracking. Phase 27 builds directly on all of these.

### Key source files to modify or extend
- `v3/contracts/exploration.py` — Add ComponentClass enum; existing EdgeType.SHARED
  and EdgeType.MERGED already defined
- `v3/orchestration/select_parents_service.py` — Upgrade merge-stage parent
  selection to use complementarity (currently falls back to K=1)
- `v3/orchestration/branch_share_service.py` — Existing InteractionKernel and
  assess/apply pattern; upgrade to probabilistic interaction kernel
- `v3/orchestration/branch_merge_service.py` — Current shortlist + SimpleTraceMerger;
  upgrade to complementary analysis + LLM-driven synthesis
- `v3/algorithms/merge.py` — MergeAdapter protocol and SimpleTraceMerger; extend
  for LLM-driven Select/Modify/Create synthesis
- `v3/orchestration/dag_service.py` — DAG graph operations (ancestors, descendants,
  frontier); used for cross-branch discovery and merge node creation
- `v3/orchestration/multi_branch_service.py` — Coordinates exploration/convergence
  rounds; add global best injection trigger and merge stage orchestration
- `v3/orchestration/scoring_service.py` — Has compute_generalization_signals;
  extend with complementarity scoring
- `v3/orchestration/branch_prune_service.py` — Add signal 4 (functional
  preservation) to multi-signal pruning
- `v3/algorithms/decay.py` — Cosine decay; reuse for interaction kernel time decay

### Verification anchors
- `tests/test_phase16_selection.py` — Existing selection tests
- `tests/test_phase16_convergence.py` — Existing convergence tests
- `tests/test_phase16_branch_lifecycle.py` — Branch lifecycle tests
- `tests/test_phase25_stage_materialization.py` — Stage materialization tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BranchShareService` (`v3/orchestration/branch_share_service.py`): Already has
  `InteractionKernel` dataclass (source/target/similarity) and assess/apply share
  pattern via memory. Upgrade to probabilistic kernel with full $U_{ij}$ computation.
- `BranchMergeService` (`v3/orchestration/branch_merge_service.py`): Shortlist-based
  merge with quality gap check + `SimpleTraceMerger`. Upgrade to complementary
  analysis + LLM-driven synthesis.
- `MergeAdapter` protocol (`v3/algorithms/merge.py`): `merge(traces, task_summary,
  scenario_name) -> MergeDesign`. Extend for Select/Modify/Create operations.
- `DAGService` (`v3/orchestration/dag_service.py`): Full graph operations —
  `create_node`, `get_ancestors`, `get_descendants`, `get_frontier`,
  `update_node_metrics`. Infrastructure for cross-branch discovery and merge nodes.
- `SelectParentsService` (`v3/orchestration/select_parents_service.py`): Three-
  dimensional scoring with complementarity dimension empty. Phase 27 fills it.
- `BranchDecisionKind.SHARE` and `BranchDecisionKind.MERGE` — already defined.
- `EdgeType.SHARED` and `EdgeType.MERGED` — defined in contracts, unused.
- `cosine_decay` in `v3/algorithms/decay.py` — reusable for kernel time decay.
- `MemoryService` — existing memory infrastructure for failure/success record
  retrieval during merge weakness elimination.

### Established Patterns
- Services depend on `StateStorePort` protocol — new services (e.g.,
  InteractionKernelService, ComponentAnalysisService) should follow this pattern.
- Branch decisions recorded as `BranchDecisionSnapshot` — sharing and merge
  decisions reuse existing kind=SHARE and kind=MERGE.
- Contracts in `v3/contracts/`, services in `v3/orchestration/`, algorithms in
  `v3/algorithms/`. All new contracts use Pydantic BaseModel with
  `ConfigDict(extra="forbid", frozen=True)`.

### Integration Points
- `MultiBranchService.run_exploration_round` — inject global best + $h_s$ into
  dispatched branch payloads as propose-stage context.
- `SelectParentsService._score_candidates` — add complementarity dimension using
  ComponentClass coverage + semantic distance.
- `BranchPruneService` multi-signal criteria — add signal 4 (functional
  preservation check via ComponentClass uniqueness).
- `MultiBranchService.run_convergence_round` — upgrade to orchestrate full merge
  pipeline: complementary identification → LLM synthesis → holdout validation.
- `DAGService.create_node` — create MERGED-edge nodes for merge results.

</code_context>

<specifics>
## Specific Ideas

- The interaction kernel is inspired by statistical physics — potential energy
  metaphor with Softmax normalization produces a natural exploration/exploitation
  balance.
- Anti-convergence is NOT a separate mechanism but an emergent property of the
  four-layer design (probabilistic sampling + LLM creativity + time decay +
  first-layer diversity).
- "Good solution" is redefined from "high total score" to "possessing uniquely
  valuable modules" — this drives both pruning protection and merge parent
  selection.
- The ApproachCategory (branch direction) × ComponentClass (solution structure)
  two-dimensional model is central: branches explore different challenges while
  solutions contain components across multiple pipeline stages. Merge identifies
  cross-dimension complementarity.
- Code fusion is NOT text-level merge — it's LLM-driven "expert consultation"
  where the model understands component semantics and produces logically coherent
  adapted code.
- Conflicts between branches modifying the same ComponentClass are resolved by
  Valid Score selection OR LLM Modify adaptation — conflicts are "optimization
  opportunities."

</specifics>

<deferred>
## Deferred Ideas

### Phase 28: Advanced Validation Optimization (reduced scope)
- More rigorous parallel re-evaluation in isolated environments
- Multi-checkpoint comparison across training history
- Cross-run standardized ranking
- Phase 27 provides basic holdout validation; Phase 28 adds depth

### Future (beyond v1.3)
- Embedding-based semantic similarity as a first-class DiversityService
  (currently uses external embedding via interaction kernel)
- Virtual evaluation filtering: LLM novelty scoring before development stage
- Cross-run DAG connections (learning from previous runs)
- Visual DAG rendering for operator inspection
- Problem-dimension alignment scoring using target_challenge fields

</deferred>

---

*Phase: 27-cross-branch-communication-and-multi-trace-solution-merge*
*Context gathered: 2026-03-23*
