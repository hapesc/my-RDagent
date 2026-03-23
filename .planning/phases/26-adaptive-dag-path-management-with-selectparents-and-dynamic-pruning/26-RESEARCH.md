# Phase 26: Adaptive DAG path management with SelectParents and dynamic pruning - Research

**Researched:** 2026-03-23
**Domain:** DAG topology layer, parent selection service, multi-signal pruning, hypothesis diversity
**Confidence:** HIGH

## Summary

Phase 26 adds four interconnected capabilities to the V3 orchestration layer:
(1) an independent DAG topology layer (`DAGNodeSnapshot`, `DAGEdgeSnapshot`,
`DAGService`) that tracks parent-child relationships separately from the branch
lifecycle model; (2) a `SelectParentsService` that picks context-feeding parent
nodes based on validation quality, generalization gap, overfitting risk, and
budget-aware diversity weighting; (3) an upgrade to `BranchPruneService` and
`prune_branch_candidates` that uses multi-signal criteria with time-aware
cosine-decay thresholds; and (4) `HypothesisSpec` with `ApproachCategory` enum
for first-layer diversity enforcement via category constraints and Shannon
entropy scoring.

The codebase is well-structured for this extension. All existing contracts use
Pydantic 2 `BaseModel` with `ConfigDict(extra="forbid", frozen=True)`. Services
depend on the `StateStorePort` protocol. Branch decisions are recorded as
`BranchDecisionSnapshot`. The `ArtifactStateStore` is the filesystem-backed
implementation. The PUCT math in `v3/algorithms/puct.py` and its adapter in
`puct_selection_adapter.py` provide reusable softmax prior and ranking
infrastructure that `SelectParentsService` can build on.

**Primary recommendation:** Build in four waves -- contracts first (DAG +
BranchScore + RunSnapshot + HypothesisSpec), then algorithms (cosine decay,
multi-signal pruning), then services (DAGService, SelectParentsService, upgraded
BranchPruneService), then integration points (MultiBranchService auto-prune,
rd_agent HypothesisSpec wiring).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Create `SelectParentsService` as a separate service from `SelectionService`.
  `SelectionService` answers "which branch to advance next" (unchanged).
  `SelectParentsService` answers "which past nodes should feed context into a
  new iteration."
- Three-dimensional signal model for parent selection:
  1. Core quality: validation score, generalization_gap, overfitting_risk
  2. Strategic planning: budget_ratio from current_round/max_rounds with cosine
     decay diversity weight
  3. Complementarity: reserved for Phase 27
- Dynamic parent count: early K=3, iteration K=1, merge K=1 (Phase 27 overrides)
- Independent DAG Node layer separate from branch lifecycle model
- DAGNodeSnapshot, DAGEdgeSnapshot, DAGService with graph operations
- Phase 26 scope: only PARENT edges (SHARED/MERGED defined but unused)
- BranchScore extended with generalization_gap and overfitting_risk
- RunSnapshot extended with current_round and max_rounds (default 20)
- Dynamic pruning triggers automatically after each exploration round
- Multi-signal pruning: time-aware threshold, generalization stability,
  anti-overfitting (complementarity preservation deferred to Phase 27)
- min_active_branches = 2 safety constraint
- HypothesisSpec model with ApproachCategory fixed enum
- Category increment constraint: at most 1 branch per category in first layer
- diversity_score: Shannon entropy of category distribution

### Claude's Discretion
- Exact cosine decay formula parameters (amplitude, phase shift)
- Internal implementation of DAGService graph traversal algorithms
- How HypothesisSpec integrates with route_user_intent auto-hypothesis generation
- Whether to use a separate v3/algorithms/dag.py or keep graph logic in DAGService
- Error handling strategy when parent nodes are pruned before child completes

### Deferred Ideas (OUT OF SCOPE)
- Phase 27: SHARED/MERGED edge activation, global best injection, probabilistic
  sampling kernel, complementarity signal computation, merge-stage multi-parent
  selection, interaction kernel negative feedback
- Phase 28: DAG frontier candidate collection, holdout re-evaluation,
  standardized ranking, final submission selection
- Future: embedding-based similarity, virtual evaluation, interaction kernel,
  cross-run DAG connections, visual DAG rendering, problem-dimension alignment
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 26 does not map to existing v1 requirement IDs (all v1 requirements are
complete). Phase 26 defines new convergence-mechanism capabilities.

| ID | Description | Research Support |
|----|-------------|-----------------|
| P26-DAG | Independent DAG topology layer with node/edge snapshots | DAGNodeSnapshot, DAGEdgeSnapshot contracts + DAGService + StateStorePort DAG CRUD |
| P26-SELECT | SelectParentsService with 3D signal model | New service using PUCT math patterns, BranchScore extensions |
| P26-PRUNE | Multi-signal dynamic pruning with cosine-decay threshold | Extended prune_branch_candidates + auto-trigger in MultiBranchService |
| P26-DIVERSITY | First-layer diversity via HypothesisSpec + category constraint | HypothesisSpec contract + ApproachCategory enum + entropy computation |
| P26-ROUND | Round tracking via RunSnapshot current_round/max_rounds | RunBoardSnapshot extension + MultiBranchService round increment |
| P26-SCORE | BranchScore extension with generalization_gap and overfitting_risk | BranchScore model extension + ScoringService computation |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Contract models with frozen/extra-forbid | Already used for all V3 contracts |
| pytest | 9.0.2 | Test framework | Already configured in pyproject.toml |
| hypothesis | 6.151.9 | Property-based testing | Already in test deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math (stdlib) | N/A | Cosine decay, Shannon entropy, softmax | All formula implementations |
| uuid (stdlib) | N/A | Decision/node ID generation | DAG node IDs, decision IDs |
| dataclasses (stdlib) | N/A | Frozen service return types | BranchRecommendation pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom DAG in-memory | networkx | Overkill -- project has no external graph dependency and DAG ops are simple BFS/DFS |
| Custom cosine decay | scipy | Unnecessary dependency -- math.cos is sufficient |
| Custom Shannon entropy | scipy.stats.entropy | Unnecessary dependency -- a 3-line formula is cleaner |

**Installation:**
```bash
# No new dependencies needed -- all required packages already installed
```

## Architecture Patterns

### Recommended Project Structure
```
v3/
├── contracts/
│   ├── exploration.py      # ADD: DAGNodeSnapshot, DAGEdgeSnapshot,
│   │                       #      NodeMetrics, EdgeType, HypothesisSpec,
│   │                       #      ApproachCategory
│   ├── branch.py           # EXTEND: BranchScore with generalization_gap,
│   │                       #         overfitting_risk
│   └── run.py              # EXTEND: RunBoardSnapshot with current_round,
│                           #         max_rounds
├── algorithms/
│   ├── prune.py            # EXTEND: multi-signal pruning with time-aware
│   │                       #         threshold
│   └── dag.py              # NEW: graph traversal algorithms (ancestors,
│                           #      descendants, frontier, depth, path)
├── orchestration/
│   ├── select_parents_service.py  # NEW: SelectParentsService
│   ├── dag_service.py             # NEW: DAGService (graph ops + state store)
│   ├── scoring_service.py         # EXTEND: generalization_gap, overfitting_risk
│   ├── branch_prune_service.py    # EXTEND: multi-signal criteria
│   └── multi_branch_service.py    # EXTEND: auto-prune + round counting
├── ports/
│   └── state_store.py      # EXTEND: DAG CRUD methods
└── entry/
    └── rd_agent.py          # EXTEND: HypothesisSpec integration
```

### Pattern 1: Separate Algorithm from Service (Established)
**What:** Pure algorithmic functions live in `v3/algorithms/`, services in
`v3/orchestration/` wrap them with state-store I/O.
**When to use:** Always for Phase 26 -- mirrors the prune.py/BranchPruneService
and puct.py/PuctSelectionAdapter patterns.
**Example:**
```python
# v3/algorithms/dag.py -- pure functions, no state store dependency
def get_ancestors(
    node_id: str,
    adjacency: dict[str, list[str]],
) -> list[str]:
    """BFS traversal to collect all ancestor node IDs."""
    visited: set[str] = set()
    queue = list(adjacency.get(node_id, []))
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency.get(current, []))
    return list(visited)
```

### Pattern 2: Pydantic Frozen Contracts (Established)
**What:** All new data models use `ConfigDict(extra="forbid", frozen=True)`.
**When to use:** Every new contract added in Phase 26.
**Example:**
```python
class NodeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity_score: float = Field(default=0.0, ge=0.0)
```

### Pattern 3: Cosine Decay for Exploration-Exploitation Balance
**What:** Use cosine annealing to smoothly transition from diversity-favoring
(early) to certainty-favoring (late) behavior across the run lifecycle.
**When to use:** Both SelectParents diversity weight AND pruning threshold.
**Example:**
```python
import math

def cosine_decay(budget_ratio: float, *, high: float = 0.7, low: float = 0.3) -> float:
    """Cosine decay from high to low as budget_ratio goes from 0 to 1.

    budget_ratio = current_round / max_rounds
    At budget_ratio=0: returns high (favor diversity / loose pruning)
    At budget_ratio=1: returns low (favor certainty / strict pruning)
    """
    return low + 0.5 * (high - low) * (1.0 + math.cos(math.pi * budget_ratio))
```

### Pattern 4: BranchDecisionSnapshot for All Decisions (Established)
**What:** Every significant action (select, prune, fork, share) records a
`BranchDecisionSnapshot` through the state store.
**When to use:** SelectParents decisions should use kind=SELECT with parent
context in the rationale field.

### Pattern 5: Protocol Extension for StateStorePort (Established)
**What:** New storage methods are added to the `StateStorePort` Protocol, then
implemented in `ArtifactStateStore`.
**When to use:** DAG CRUD methods (write_dag_node, load_dag_node,
list_dag_nodes_for_run, write_dag_edge, list_dag_edges_for_node).

### Anti-Patterns to Avoid
- **Mutating BranchScore in-place:** BranchScore is frozen. Always use
  `model_copy(update={...})` to create a new instance with the extended fields.
- **Coupling DAG layer to branch lifecycle:** The DAG layer tracks topology
  (parent-child, depth, path metrics). Branch tracks execution state
  (active/superseded/completed). These must remain independent.
- **Hard-coding pruning thresholds:** The cosine decay parameters should be
  configurable, not hardcoded constants scattered through the code.
- **Breaking backward compatibility:** The existing `prune_branch_candidates`
  signature must remain callable with just `candidates` and
  `relative_threshold`. The new multi-signal mode should be opt-in via
  additional keyword arguments.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Softmax prior computation | Custom softmax | Reuse `_softmax_prior` from scoring_service.py | Already handles numerical stability (max subtraction) |
| Branch filtering by status | Custom query | Reuse existing pattern from SelectionService.select_next_branch | Same status/recovery filtering logic |
| Decision recording | Custom persistence | Reuse BranchDecisionSnapshot + state_store.write_branch_decision | Established recording pattern |
| Board refresh | Custom board construction | Reuse BranchBoardService.get_board | Already produces BranchBoardSnapshot |
| ID generation | Custom schemes | Use f"decision-{kind}-{uuid4().hex[:12]}" pattern | Matches existing ID patterns |

**Key insight:** Phase 26 extends existing patterns rather than inventing new
ones. The selection/pruning/scoring services already demonstrate how to: filter
eligible branches, compute signals, record decisions, and refresh board state.
SelectParentsService and DAGService should follow the same structure.

## Common Pitfalls

### Pitfall 1: Breaking BranchScore Backward Compatibility
**What goes wrong:** Adding required fields to BranchScore breaks all existing
tests and code that constructs BranchScore without the new fields.
**Why it happens:** BranchScore is constructed in dozens of places across tests
and services.
**How to avoid:** Make `generalization_gap` and `overfitting_risk` optional with
defaults: `generalization_gap: float = 0.0`, `overfitting_risk: float = 0.0`.
**Warning signs:** Existing tests fail with "field required" validation errors.

### Pitfall 2: Breaking RunBoardSnapshot Backward Compatibility
**What goes wrong:** Adding required fields to RunBoardSnapshot breaks all
existing run creation paths.
**Why it happens:** RunBoardSnapshot is created in run_board_service and dozens
of test fixtures.
**How to avoid:** Make `current_round: int = 0` and `max_rounds: int = 20` both
optional with defaults. This way all existing code continues to work.
**Warning signs:** Tests fail on RunBoardSnapshot construction.

### Pitfall 3: Pruning Below min_active_branches
**What goes wrong:** Multi-signal pruning prunes all but one branch, leaving
insufficient diversity.
**Why it happens:** Multiple pruning signals can each independently recommend
pruning, and without a global guard they compound.
**How to avoid:** Enforce `min_active_branches = 2` as a hard floor check AFTER
computing prune candidates but BEFORE executing prune operations. Count
remaining active branches before each prune commit.
**Warning signs:** Runs collapse to single-branch mode prematurely.

### Pitfall 4: Circular Parent References in DAG
**What goes wrong:** A node references itself or creates a cycle in parent_node_ids.
**Why it happens:** Incorrect wiring when creating DAG nodes, especially during
multi-parent scenarios.
**How to avoid:** Validate at DAGNodeSnapshot creation time that `node_id` is not
in `parent_node_ids`. In DAGService, validate no cycles exist using ancestors
check before persisting.
**Warning signs:** Infinite loops in get_ancestors/get_descendants.

### Pitfall 5: StateStorePort Protocol Not Updated
**What goes wrong:** DAGService calls methods that don't exist on the Protocol,
causing AttributeError at runtime.
**Why it happens:** Adding methods to ArtifactStateStore without updating the
Protocol class.
**How to avoid:** Always add methods to StateStorePort Protocol FIRST, then
implement in ArtifactStateStore. Run type checks.
**Warning signs:** AttributeError or Protocol compliance failures.

### Pitfall 6: Category Constraint Breaks Empty-State Boot
**What goes wrong:** The "at most 1 branch per category" constraint rejects
the initial hypothesis set because no categories exist yet.
**Why it happens:** Constraint enforcement that doesn't distinguish initial
seeding from subsequent additions.
**How to avoid:** The category constraint applies within a run's first layer
only. During initial seeding (the first `run_exploration_round`), validate
uniqueness within the provided list but don't compare against a non-existent
prior state.
**Warning signs:** First exploration round with 3 hypotheses of different
categories fails to create branches.

### Pitfall 7: Cosine Decay Asymmetry
**What goes wrong:** SelectParents diversity weight and pruning threshold use
different decay curves, creating conflicting signals (e.g., diversity weight
says "be diverse" while pruning says "prune aggressively").
**Why it happens:** Independent implementation of the decay formula with
different parameters.
**How to avoid:** Extract a single `cosine_decay` utility function and use it
in both places with symmetric parameters. The CONTEXT explicitly requires:
"Mirrors the SelectParents diversity weight curve."
**Warning signs:** In mid-run, branches are simultaneously encouraged by
selection and pruned by pruning.

## Code Examples

### BranchScore Extension
```python
# v3/contracts/branch.py
class BranchScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exploration_priority: float = Field(ge=0.0)
    result_quality: float = Field(ge=0.0)
    rationale: str = Field(min_length=1)
    # Phase 26 extensions -- defaults preserve backward compatibility
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)
```

### RunBoardSnapshot Extension
```python
# v3/contracts/run.py
class RunBoardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # ... existing fields ...
    # Phase 26 extensions
    current_round: int = Field(default=0, ge=0)
    max_rounds: int = Field(default=20, ge=1)
```

### DAGNodeSnapshot and DAGEdgeSnapshot
```python
# v3/contracts/exploration.py

class EdgeType(StrEnum):
    PARENT = "parent"
    SHARED = "shared"   # Phase 27
    MERGED = "merged"   # Phase 27

class NodeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity_score: float = Field(default=0.0, ge=0.0)

class DAGNodeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    parent_node_ids: list[str] = Field(default_factory=list)
    depth: int = Field(default=0, ge=0)
    node_metrics: NodeMetrics = Field(default_factory=NodeMetrics)

class DAGEdgeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    edge_type: EdgeType = EdgeType.PARENT
    weight: float = Field(default=1.0, ge=0.0)
```

### HypothesisSpec and ApproachCategory
```python
# v3/contracts/exploration.py

class ApproachCategory(StrEnum):
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_ARCHITECTURE = "model_architecture"
    DATA_AUGMENTATION = "data_augmentation"
    ENSEMBLE = "ensemble"
    LOSS_FUNCTION = "loss_function"
    TRAINING_STRATEGY = "training_strategy"
    OTHER = "other"

class HypothesisSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    approach_category: ApproachCategory
    target_challenge: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
```

### Cosine Decay Utility
```python
# v3/algorithms/decay.py or inline in a shared location
import math

def cosine_decay(
    budget_ratio: float,
    *,
    high: float = 0.7,
    low: float = 0.3,
) -> float:
    """Smooth transition from high (early) to low (late) via cosine annealing."""
    clamped = max(0.0, min(1.0, budget_ratio))
    return low + 0.5 * (high - low) * (1.0 + math.cos(math.pi * clamped))
```

### Multi-Signal Pruning Extension
```python
# v3/algorithms/prune.py -- extended signature
def prune_branch_candidates(
    candidates: list[tuple[str, float]],
    *,
    score_threshold: float | None = None,
    relative_threshold: float | None = 0.5,
    # Phase 26 extensions
    generalization_gaps: dict[str, float] | None = None,
    overfitting_risks: dict[str, float] | None = None,
    budget_ratio: float | None = None,
    min_active_branches: int = 1,
) -> list[str]:
    """Extended pruning with multi-signal criteria.

    When budget_ratio is provided, relative_threshold is overridden by
    cosine_decay(budget_ratio). When generalization/overfitting signals
    are provided, they modulate per-branch prune decisions.
    """
    ...
```

### Shannon Entropy for Diversity
```python
import math

def category_entropy(category_counts: dict[str, int]) -> float:
    """Shannon entropy over approach category distribution."""
    total = sum(category_counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in category_counts.values():
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy
```

### SelectParentsService Core Logic
```python
# v3/orchestration/select_parents_service.py
@dataclass(frozen=True)
class ParentRecommendation:
    parent_node_ids: list[str]
    rationale: str
    budget_ratio: float
    diversity_weight: float

class SelectParentsService:
    def __init__(self, state_store: StateStorePort) -> None:
        self._state_store = state_store

    def select_parents(
        self,
        *,
        run_id: str,
        branch_id: str,
        max_parents: int | None = None,
    ) -> ParentRecommendation:
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        budget_ratio = run.current_round / max(run.max_rounds, 1)
        diversity_weight = cosine_decay(budget_ratio)

        # Determine K based on budget phase
        if max_parents is not None:
            k = max_parents
        elif budget_ratio < 0.3:
            k = 3  # Early: multiple parents for diversity
        else:
            k = 1  # Iteration/Merge: single best parent

        # ... score and rank candidate parent nodes ...
```

### DAG CRUD Methods for StateStorePort
```python
# v3/ports/state_store.py -- Protocol extension
class StateStorePort(Protocol):
    # ... existing methods ...

    # Phase 26: DAG CRUD
    def write_dag_node(self, node: "DAGNodeSnapshot") -> ArtifactRecord: ...
    def load_dag_node(self, node_id: str) -> "DAGNodeSnapshot | None": ...
    def list_dag_nodes(self, run_id: str) -> "list[DAGNodeSnapshot]": ...
    def write_dag_edge(self, edge: "DAGEdgeSnapshot") -> ArtifactRecord: ...
    def list_dag_edges(self, run_id: str) -> "list[DAGEdgeSnapshot]": ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single relative_threshold pruning | Multi-signal pruning with cosine decay | Phase 26 | Pruning adapts to run lifecycle stage |
| No parent tracking | DAG topology with parent selection | Phase 26 | Enables context-aware iteration building |
| branch_hypotheses: list[str] | HypothesisSpec with ApproachCategory | Phase 26 | Structured diversity enforcement |
| BranchScore: 2 fields | BranchScore: 4 fields | Phase 26 | Richer generalization/overfitting signals |
| No round tracking | current_round/max_rounds on RunSnapshot | Phase 26 | Budget-aware exploration/exploitation |

**Deprecated/outdated:**
- Plain string hypotheses in `branch_hypotheses: list[str]` -- being replaced by
  `list[HypothesisSpec]`. The `rd_agent` function and `ExploreRoundRequest` must
  be updated to accept both formats during transition.

## Open Questions

1. **Backward compatibility for ExploreRoundRequest.hypotheses**
   - What we know: Currently `hypotheses: list[str]`. Phase 26 introduces
     `HypothesisSpec` objects. The `ExploreRoundRequest` must accept both.
   - What's unclear: Whether to use a Union type, a separate field, or convert
     strings to HypothesisSpec at the boundary.
   - Recommendation: Add `hypothesis_specs: list[HypothesisSpec] | None = None`
     as a new optional field. When present, use specs; when absent, fall back to
     string hypotheses with `ApproachCategory.OTHER`. This preserves full
     backward compatibility.

2. **DAG node creation timing**
   - What we know: DAG nodes should be created when a new iteration starts.
   - What's unclear: Exactly which service/method creates the DAG node --
     `StageTransitionService.publish_stage_start`, `MultiBranchService`, or
     `BranchLifecycleService.fork_branch`.
   - Recommendation: `MultiBranchService.run_exploration_round` is the natural
     injection point since it already orchestrates branch creation and dispatch.
     Create a DAG node immediately after forking/dispatching each branch.

3. **How to handle pruned parent nodes**
   - What we know: A child node references parent_node_ids. Parents can be
     pruned before the child completes.
   - What's unclear: Should the child's parent references be cleaned up, or
     should the DAG preserve historical connections?
   - Recommendation: Preserve historical connections. The DAG is a topology
     record, not a liveness indicator. Pruned branches keep their DAG nodes;
     only the branch status changes. This aligns with the separation between
     DAG (topology) and branch (lifecycle).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + hypothesis 6.151.9 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_phase26_*.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P26-DAG | DAGNodeSnapshot/DAGEdgeSnapshot creation and graph traversal | unit | `uv run pytest tests/test_phase26_dag.py -x` | No -- Wave 0 |
| P26-SELECT | SelectParentsService picks parents with correct K for budget phase | unit | `uv run pytest tests/test_phase26_select_parents.py -x` | No -- Wave 0 |
| P26-PRUNE | Multi-signal pruning respects cosine decay and min_active_branches | unit | `uv run pytest tests/test_phase26_pruning.py -x` | No -- Wave 0 |
| P26-DIVERSITY | HypothesisSpec category constraint rejects duplicates, entropy computed | unit | `uv run pytest tests/test_phase26_diversity.py -x` | No -- Wave 0 |
| P26-ROUND | RunBoardSnapshot tracks current_round, auto-incremented after round | unit | `uv run pytest tests/test_phase26_round_tracking.py -x` | No -- Wave 0 |
| P26-SCORE | BranchScore carries generalization_gap and overfitting_risk | unit | `uv run pytest tests/test_phase26_scoring.py -x` | No -- Wave 0 |
| P26-COMPAT | Existing tests still pass with extended contracts | integration | `uv run pytest tests/test_phase16_*.py tests/test_phase25_*.py -x` | Yes |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_phase26_*.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase26_dag.py` -- covers P26-DAG: DAG node/edge CRUD, graph traversal (ancestors, descendants, frontier), cycle prevention
- [ ] `tests/test_phase26_select_parents.py` -- covers P26-SELECT: parent selection K=3/K=1 by budget phase, scoring by quality+generalization+overfitting
- [ ] `tests/test_phase26_pruning.py` -- covers P26-PRUNE: cosine-decay threshold, multi-signal prune decisions, min_active_branches guard
- [ ] `tests/test_phase26_diversity.py` -- covers P26-DIVERSITY: HypothesisSpec validation, category uniqueness constraint, Shannon entropy
- [ ] `tests/test_phase26_round_tracking.py` -- covers P26-ROUND: current_round increment, budget_ratio computation
- [ ] `tests/test_phase26_scoring.py` -- covers P26-SCORE: generalization_gap and overfitting_risk on BranchScore, backward compat with default=0.0

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all source files listed in 26-CONTEXT.md canonical_refs
- `v3/contracts/branch.py` -- BranchScore current structure (lines 24-32)
- `v3/contracts/run.py` -- RunBoardSnapshot current structure (lines 38-60)
- `v3/contracts/exploration.py` -- BranchDecisionKind, BranchResolution enums
- `v3/algorithms/prune.py` -- Current prune_branch_candidates algorithm
- `v3/algorithms/puct.py` -- PUCT math and softmax prior
- `v3/orchestration/selection_service.py` -- SelectionService patterns
- `v3/orchestration/scoring_service.py` -- BranchSelectionSignal, score projection
- `v3/orchestration/branch_prune_service.py` -- BranchPruneService patterns
- `v3/orchestration/multi_branch_service.py` -- MultiBranchService.run_exploration_round
- `v3/orchestration/artifact_state_store.py` -- ArtifactStateStore filesystem persistence
- `v3/ports/state_store.py` -- StateStorePort protocol
- `v3/entry/rd_agent.py` -- rd_agent entrypoint and route_user_intent
- `v3/entry/tool_catalog.py` -- Tool catalog spec structure
- `tests/test_phase16_selection.py` -- Existing selection test patterns
- `tests/test_phase16_convergence.py` -- Existing convergence test patterns
- `pyproject.toml` -- pydantic>=2, pytest>=7.4.0, hypothesis>=6.0.0

### Secondary (MEDIUM confidence)
- Cosine annealing is a standard ML learning rate schedule -- the adaptation to
  exploration/exploitation budget weighting is a direct analogy
- Shannon entropy for category distribution diversity is textbook information
  theory

### Tertiary (LOW confidence)
- None -- all findings verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- follows established service/algorithm/contract patterns exactly
- Pitfalls: HIGH -- identified from actual code structure and Pydantic model constraints
- Contracts: HIGH -- verified frozen/extra-forbid pattern, backward-compat defaults needed
- Algorithms: HIGH -- cosine decay and Shannon entropy are well-understood math

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable internal architecture, no external API dependencies)
