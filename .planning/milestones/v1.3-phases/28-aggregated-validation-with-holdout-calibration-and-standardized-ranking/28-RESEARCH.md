# Phase 28: Aggregated Validation with Holdout Calibration and Standardized Ranking - Research

**Researched:** 2026-03-24
**Domain:** Holdout cross-validation pipeline, abstract evaluation ports, standardized ranking
**Confidence:** HIGH

## Summary

Phase 28 is the "private leaderboard" layer of the R&D-Agent convergence mechanism.
It replaces the Phase 27 proxy gate (`validate_merge_holdout`) with a rigorous
K-fold holdout validation pipeline that prevents overfitting to the primary
validation set. The implementation is entirely within the existing V3 codebase:
no new external libraries are needed. All work involves new Pydantic contracts,
two new Protocol ports, one new orchestration service, and surgical modifications
to three existing files.

The codebase already has all the building blocks: `DAGService.get_frontier` for
candidate collection, `NodeMetrics` for score storage, `OperatorGuidance` for
operator presentation, and the `StateStorePort` Protocol pattern for persistence.
The architecture is a clean port-and-service decomposition: `HoldoutSplitPort`
produces fold specs, `EvaluationPort` evaluates candidates on folds, and
`HoldoutValidationService` orchestrates the pipeline. The design is deliberately
abstract so V3 remains a pure orchestration layer -- the actual data splitting
and model evaluation are injected by callers.

**Primary recommendation:** Implement as 4-5 focused plans: (1) contracts and
ports, (2) holdout validation service with ranking, (3) activation triggers and
proxy replacement, (4) operator presentation and final submission, (5) integration
tests. Each plan produces independently testable artifacts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Holdout set construction via abstract `HoldoutSplitPort` protocol returning
  `list[FoldSpec]` (K=5 folds). Default implementation: `StratifiedKFoldSplitter`.
- Two independent ports: `HoldoutSplitPort` (once per finalization) and
  `EvaluationPort` (once per candidate per fold).
- `validate_merge_holdout` completely replaced by `HoldoutValidationService`.
  All call sites in `BranchMergeService` updated.
- Dual-mode activation: auto when `current_round >= max_rounds`, plus explicit
  early-finalization entry point.
- Candidate pool: frontier nodes + MERGED nodes, filtered by median
  `validation_score` quality threshold.
- Ranking: primary sort by mean holdout score (higher better), tiebreak by std
  across folds (lower better). Single-run scope only.
- Extend `NodeMetrics` with `holdout_mean: float` and `holdout_std: float`
  (backward-compatible 0.0 defaults).
- New `FinalSubmissionSnapshot` contract with `winner_node_id`, `winner_branch_id`,
  `holdout_mean`, `holdout_std`, full ranked list, and DAG ancestry chain.
- Operator presentation via existing `OperatorGuidance` contract and renderer.

### Claude's Discretion
- Exact `FoldSpec` data model fields beyond train/holdout references
- `StratifiedKFoldSplitter` internal stratification strategy
- `EvaluationPort` protocol signature details (sync vs async, timeout handling)
- How `MultiBranchService` integrates the auto-finalization trigger
- Error handling when all candidates fail holdout evaluation
- Exact quality threshold computation (median vs percentile)

### Deferred Ideas (OUT OF SCOPE)
- Cross-run standardized ranking with Z-score normalization
- Multi-checkpoint comparison across training history
- Ensemble submission (combine Top-N instead of selecting one)
- Visual ranking dashboard with fold-level score breakdowns
- Automated submission to external platforms (Kaggle API integration)
- Adaptive K selection based on candidate pool size and compute budget
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 28 does not have formally assigned requirement IDs in REQUIREMENTS.md yet
(listed as TBD). Based on the CONTEXT.md decisions and success criteria, the
following functional requirements must be addressed:

| ID | Description | Research Support |
|----|-------------|-----------------|
| P28-HOLDOUT | K-fold holdout validation pipeline with abstract split and evaluation ports | Port pattern from `EmbeddingPort`/`StateStorePort`; `StratifiedKFoldSplitter` default impl |
| P28-RANK | Standardized ranking by mean holdout score with std tiebreak | Pure algorithm in `v3/algorithms/`; `NodeMetrics` extension for persistence |
| P28-COLLECT | Candidate collection from frontier + MERGED nodes with quality threshold filter | `DAGService.get_frontier` + `list_dag_nodes` already available |
| P28-ACTIVATE | Dual activation: auto `current_round >= max_rounds` + explicit early-finalization | `MultiBranchService.run_exploration_round` round increment point identified |
| P28-REPLACE | Replace `validate_merge_holdout` proxy with `HoldoutValidationService` | Single call site in `BranchMergeService.merge_with_complementarity` |
| P28-SUBMIT | `FinalSubmissionSnapshot` contract with ancestry traceability | `DAGService.get_ancestors` for chain; new contract in `v3/contracts/exploration.py` |
| P28-PRESENT | Operator finalization summary via `OperatorGuidance` | Existing renderer in `v3/orchestration/operator_guidance.py` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2,<3 | All new contracts (`FoldSpec`, `FinalSubmissionSnapshot`, `CandidateRankEntry`) | Already the contract foundation for every V3 model |
| Python typing.Protocol | stdlib | `HoldoutSplitPort` and `EvaluationPort` abstract ports | Established port pattern (`StateStorePort`, `EmbeddingPort`, `ExecutionPort`) |
| statistics (stdlib) | 3.11+ | `mean()` and `stdev()` for fold score aggregation | No external dependency needed for basic statistics |
| uuid (stdlib) | 3.11+ | ID generation for snapshots | Matches existing `uuid4().hex[:12]` pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.4.0 | Unit and integration tests | All test files |
| dataclasses | stdlib | `FoldSpec` if kept lightweight | Only if FoldSpec is a simple data carrier instead of Pydantic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| statistics.stdev | numpy.std | numpy is an unnecessary dependency; statistics is stdlib |
| Pydantic for FoldSpec | dataclass | FoldSpec is opaque to V3 -- dataclass is lighter but breaks the "all contracts are Pydantic" convention |

**Installation:**
```bash
# No new dependencies. All stdlib + existing pydantic.
pip install -e ".[test]"
```

**Version verification:** All dependencies are already in pyproject.toml. No new
packages to install.

## Architecture Patterns

### Recommended Project Structure
```
v3/
├── contracts/
│   └── exploration.py          # Extend NodeMetrics; add FinalSubmissionSnapshot,
│                                # CandidateRankEntry, FoldSpec
├── ports/
│   └── holdout_port.py         # NEW: HoldoutSplitPort + EvaluationPort protocols,
│                                # StratifiedKFoldSplitter, StubEvaluationPort
├── algorithms/
│   ├── merge.py                # Remove validate_merge_holdout
│   └── holdout.py              # NEW: rank_candidates(), compute_holdout_scores(),
│                                # filter_by_quality_threshold()
├── orchestration/
│   ├── holdout_validation_service.py  # NEW: HoldoutValidationService
│   ├── multi_branch_service.py        # Add auto-finalization trigger
│   ├── branch_merge_service.py        # Replace validate_merge_holdout call
│   └── operator_guidance.py           # Add finalization guidance builder
└── ...

tests/
├── test_phase28_holdout_ports.py       # Port contract tests
├── test_phase28_ranking.py             # Ranking algorithm tests
├── test_phase28_holdout_service.py     # Service orchestration tests
├── test_phase28_activation.py          # Trigger and proxy replacement tests
└── test_phase28_integration.py         # Full lifecycle integration test
```

### Pattern 1: Two-Port Separation (HoldoutSplitPort + EvaluationPort)
**What:** Separate the split-once operation from the evaluate-per-fold operation.
**When to use:** Always -- these have fundamentally different lifecycles and
cardinalities.
**Example:**
```python
# v3/ports/holdout_port.py
# Follows the exact pattern of EmbeddingPort (v3/ports/embedding_port.py)

from __future__ import annotations
from typing import Protocol
from pydantic import BaseModel, ConfigDict, Field

class FoldSpec(BaseModel):
    """Opaque fold descriptor produced by HoldoutSplitPort."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    fold_index: int = Field(ge=0)
    train_ref: str = Field(min_length=1)   # Opaque path/identifier
    holdout_ref: str = Field(min_length=1)  # Opaque path/identifier

class HoldoutSplitPort(Protocol):
    """Called once per finalization to produce K fold specs."""
    def split(self, *, run_id: str) -> list[FoldSpec]: ...

class EvaluationPort(Protocol):
    """Called once per candidate per fold to evaluate holdout performance."""
    def evaluate(
        self, *, candidate_node_id: str, fold: FoldSpec
    ) -> float: ...
```

### Pattern 2: Service-Over-Port Orchestration
**What:** `HoldoutValidationService` depends on `HoldoutSplitPort`,
`EvaluationPort`, `DAGService`, and `StateStorePort` -- orchestrating
the full evaluation pipeline.
**When to use:** Same constructor-injection pattern as `BranchMergeService`.
**Example:**
```python
class HoldoutValidationService:
    def __init__(
        self,
        *,
        state_store: StateStorePort,
        dag_service: DAGService,
        split_port: HoldoutSplitPort,
        evaluation_port: EvaluationPort,
    ) -> None:
        self._state_store = state_store
        self._dag_service = dag_service
        self._split_port = split_port
        self._evaluation_port = evaluation_port

    def finalize(self, *, run_id: str) -> FinalSubmissionSnapshot:
        # 1. Collect candidates (frontier + MERGED nodes)
        # 2. Filter by median quality threshold
        # 3. Split holdout via split_port
        # 4. Evaluate each candidate on each fold
        # 5. Rank by mean holdout score, tiebreak by std
        # 6. Persist holdout_mean/holdout_std on NodeMetrics
        # 7. Build and return FinalSubmissionSnapshot
        ...
```

### Pattern 3: Immutable Contract Extension (NodeMetrics)
**What:** Add `holdout_mean` and `holdout_std` with backward-compatible defaults.
**When to use:** Extending existing frozen Pydantic models.
**Example:**
```python
class NodeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # Existing fields...
    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    generalization_gap: float = Field(default=0.0)
    overfitting_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    diversity_score: float = Field(default=0.0, ge=0.0)
    complementarity_score: float = Field(default=0.0, ge=0.0)
    # Phase 28 additions
    holdout_mean: float = Field(default=0.0, ge=0.0)
    holdout_std: float = Field(default=0.0, ge=0.0)
```

### Pattern 4: Activation via Round Check
**What:** Auto-finalization triggers inside `run_exploration_round` after
round increment, when `current_round >= max_rounds`.
**When to use:** End of exploration budget.
**Example:**
```python
# In MultiBranchService.run_exploration_round, after round increment:
run = self._state_store.load_run_snapshot(request.run_id)
if run is not None:
    new_round = run.current_round + 1
    self._state_store.write_run_snapshot(
        run.model_copy(update={"current_round": new_round})
    )
    if new_round >= run.max_rounds and self._holdout_service is not None:
        return self._trigger_finalization(request.run_id, result)
```

### Anti-Patterns to Avoid
- **Coupling evaluation logic into V3:** V3 is the orchestration layer. Actual
  model training, data splitting, and score computation belong behind ports.
  Never put sklearn/pandas/numpy imports in V3 code.
- **Mutating NodeMetrics in-place:** NodeMetrics is frozen. Always use
  `node.model_copy(update={...})` via `DAGService.update_node_metrics`.
- **Cross-run score comparison:** Each run has its own holdout data. Scores from
  different runs are non-comparable. Never build cross-run rankings.
- **Skipping quality threshold filter:** Evaluating all candidates on all folds
  is O(N*K). The median filter halves the constant factor. Don't skip it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mean and std computation | Custom aggregation loops | `statistics.mean()`, `statistics.stdev()` | stdlib, edge cases handled (division by zero, single element) |
| DAG ancestry chain | Custom parent traversal | `DAGService.get_ancestors(node_id, run_id)` | Already tested, handles cycles |
| Frontier collection | Custom leaf detection | `DAGService.get_frontier(run_id)` | Already used by share service, tested |
| Operator presentation | New rendering surface | `OperatorGuidance` + `render_operator_guidance_text` | Established Phase 24 pattern, no new tool surface needed |
| Quality-ordered list | Custom sort | `sorted(candidates, key=lambda c: (-c.holdout_mean, c.holdout_std))` | Python's stable sort handles this trivially |
| ID generation | Custom schemes | `f"...-{uuid4().hex[:12]}"` | Matches every existing snapshot ID pattern |
| Candidate node filtering | Manual graph queries | `DAGService.list_nodes(run_id)` with in-memory filter | Already persisted and loadable |

**Key insight:** Phase 28 adds exactly one new computational concept (K-fold
holdout evaluation) and one new persistence concept (`FinalSubmissionSnapshot`).
Everything else is wiring and reuse.

## Common Pitfalls

### Pitfall 1: Breaking Backward Compatibility on NodeMetrics
**What goes wrong:** Adding `holdout_mean`/`holdout_std` without defaults breaks
every existing serialized DAG node and every test that constructs `NodeMetrics()`.
**Why it happens:** Pydantic v2 frozen models with `extra="forbid"` will reject
unknown fields, but missing required fields cause validation errors on load.
**How to avoid:** Always add new fields with `Field(default=0.0)`. Run the full
existing test suite after the extension to verify no regressions.
**Warning signs:** `ValidationError` on `NodeMetrics` construction in Phase 26/27 tests.

### Pitfall 2: Circular Import from Port Dependencies
**What goes wrong:** `HoldoutValidationService` imports from `contracts/exploration.py`
which might import from the port module.
**Why it happens:** The port file defines `FoldSpec` (a contract) alongside the
protocol. If exploration.py needs FoldSpec, circular imports occur.
**How to avoid:** Keep `FoldSpec` in the port module (`v3/ports/holdout_port.py`),
NOT in `contracts/exploration.py`. The service imports from both ports and contracts
independently. `FinalSubmissionSnapshot` goes in `contracts/exploration.py` since
it is a persistence contract, not a port-scoped type.
**Warning signs:** `ImportError: cannot import name` at module load time.

### Pitfall 3: stdev() with Single Element
**What goes wrong:** `statistics.stdev([0.85])` raises `StatisticsError` because
stdev requires at least 2 data points.
**Why it happens:** After quality threshold filtering, a candidate pool might have
only 1 survivor.
**How to avoid:** Guard with `stdev(scores) if len(scores) > 1 else 0.0`. Or use
`pstdev` (population std) which works with 1 element but returns 0.0.
**Warning signs:** `StatisticsError: stdev requires at least two data points`.

### Pitfall 4: MERGED Nodes Missing from Frontier
**What goes wrong:** MERGED nodes created by Phase 27 have parent edges, so they
might not appear in the frontier if they also have children.
**Why it happens:** `get_frontier` returns leaf nodes -- nodes with no children.
A MERGED node that later spawns a child would not be in the frontier.
**How to avoid:** Candidate collection should be `frontier_nodes UNION
merged_nodes_without_children`, or simply rely on the CONTEXT.md decision that
candidates are "Frontier nodes plus MERGED nodes" -- collect both sets and deduplicate.
**Warning signs:** Integration test where MERGED node is missing from candidate pool.

### Pitfall 5: Forgetting to Update __all__ Exports
**What goes wrong:** New contracts/ports are defined but not exported, causing
`ImportError` from downstream modules.
**Why it happens:** Every module in V3 uses explicit `__all__`.
**How to avoid:** Add every new public name to `__all__` in the same commit.
**Warning signs:** `ImportError` when importing from package.

### Pitfall 6: MergeDesign.holdout_score Field Orphaning
**What goes wrong:** After removing `validate_merge_holdout`, the
`MergeDesign.holdout_score` field becomes meaningless but is still set by
`LLMTraceMerger`.
**Why it happens:** Phase 28 replaces the holdout gate but not the merge
contract itself.
**How to avoid:** Keep `MergeDesign.holdout_score` as-is (it's still useful
for merge-stage scoring). Only remove `validate_merge_holdout` the function.
The `BranchMergeService.merge_with_complementarity` should call
`HoldoutValidationService` instead of the old proxy function.
**Warning signs:** Tests that assert on `holdout_score` in MergeDesign still pass.

## Code Examples

Verified patterns from the existing codebase:

### Stub Port for Testing (follows EmbeddingPort pattern)
```python
# Source: v3/ports/embedding_port.py pattern
class StubHoldoutSplitPort:
    """Deterministic stub for tests."""
    def __init__(self, k: int = 5) -> None:
        self._k = k

    def split(self, *, run_id: str) -> list[FoldSpec]:
        return [
            FoldSpec(
                fold_index=i,
                train_ref=f"train-fold-{i}",
                holdout_ref=f"holdout-fold-{i}",
            )
            for i in range(self._k)
        ]


class StubEvaluationPort:
    """Returns a fixed score per candidate for deterministic testing."""
    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self._scores = scores or {}

    def evaluate(self, *, candidate_node_id: str, fold: FoldSpec) -> float:
        return self._scores.get(candidate_node_id, 0.5)
```

### FinalSubmissionSnapshot Contract
```python
# Source: follows CandidateSummarySnapshot / MergeOutcomeSnapshot pattern
class CandidateRankEntry(BaseModel):
    """Single entry in the ranked candidate list."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    holdout_mean: float = Field(ge=0.0)
    holdout_std: float = Field(ge=0.0)

class FinalSubmissionSnapshot(BaseModel):
    """Persisted finalization result with full ranking and traceability."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    submission_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    winner_node_id: str = Field(min_length=1)
    winner_branch_id: str = Field(min_length=1)
    holdout_mean: float = Field(ge=0.0)
    holdout_std: float = Field(ge=0.0)
    ranked_candidates: list[CandidateRankEntry] = Field(default_factory=list)
    ancestry_chain: list[str] = Field(default_factory=list)
```

### Candidate Collection Algorithm
```python
# Source: DAGService.get_frontier + list_nodes pattern
def collect_candidates(
    dag_service: DAGService,
    state_store: StateStorePort,
    run_id: str,
) -> list[DAGNodeSnapshot]:
    """Collect frontier + MERGED nodes, deduplicated."""
    all_nodes = dag_service.list_nodes(run_id)
    frontier_ids = dag_service.get_frontier(run_id)
    edges = state_store.list_dag_edges(run_id)
    merged_target_ids = {
        edge.target_node_id
        for edge in edges
        if edge.edge_type == EdgeType.MERGED
    }
    candidate_ids = frontier_ids | merged_target_ids
    return [node for node in all_nodes if node.node_id in candidate_ids]
```

### Quality Threshold Filter
```python
# Source: CONTEXT.md decision -- median of validation_score
import statistics

def filter_by_quality_threshold(
    candidates: list[DAGNodeSnapshot],
) -> list[DAGNodeSnapshot]:
    """Filter candidates below median validation_score."""
    if len(candidates) <= 1:
        return candidates
    scores = [c.node_metrics.validation_score for c in candidates]
    threshold = statistics.median(scores)
    return [c for c in candidates if c.node_metrics.validation_score >= threshold]
```

### Ranking Algorithm
```python
import statistics

def rank_candidates(
    candidate_scores: dict[str, list[float]],
) -> list[tuple[str, float, float]]:
    """Rank by mean holdout score (desc), tiebreak by std (asc)."""
    entries = []
    for node_id, fold_scores in candidate_scores.items():
        mean = statistics.mean(fold_scores)
        std = statistics.stdev(fold_scores) if len(fold_scores) > 1 else 0.0
        entries.append((node_id, mean, std))
    entries.sort(key=lambda e: (-e[1], e[2]))
    return entries
```

### Activation Trigger Integration Point
```python
# In MultiBranchService.run_exploration_round, after line 265:
# self._state_store.write_run_snapshot(
#     run.model_copy(update={"current_round": run.current_round + 1})
# )
# ADD:
# if (run.current_round + 1) >= run.max_rounds and self._holdout_service is not None:
#     finalization = self._holdout_service.finalize(run_id=request.run_id)
#     # Attach finalization result to ExploreRoundResult
```

### StateStorePort Extension for FinalSubmissionSnapshot
```python
# Add to StateStorePort protocol:
def write_final_submission(
    self, submission: FinalSubmissionSnapshot
) -> ArtifactRecord: ...

def load_final_submission(
    self, run_id: str
) -> FinalSubmissionSnapshot | None: ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `validate_merge_holdout` simple comparison | K-fold holdout validation pipeline | Phase 28 | Merge acceptance now statistically grounded |
| Single validation_score ranking | Mean holdout + std tiebreak | Phase 28 | Prevents overfitting to primary validation set |
| No finalization contract | `FinalSubmissionSnapshot` | Phase 28 | Full traceability from winner back to initial hypothesis |
| Manual convergence judgment | Auto-finalization at budget exhaustion | Phase 28 | Operator can let the loop self-terminate |

**Deprecated/outdated:**
- `validate_merge_holdout` in `v3/algorithms/merge.py`: Replaced by
  `HoldoutValidationService`. Function removed; tests updated.

## Open Questions

1. **EvaluationPort: sync vs async?**
   - What we know: All existing ports (`EmbeddingPort`, `ExecutionPort`,
     `StateStorePort`) are synchronous protocols.
   - What's unclear: Real-world holdout evaluation (e.g., training a model
     on a fold) is inherently slow. Should `EvaluationPort.evaluate` be async?
   - Recommendation: Keep synchronous for V1 consistency. An async wrapper
     can be added later without breaking the protocol (callers just `await`
     a sync function). The stub ports for testing are inherently fast.

2. **Timeout handling for EvaluationPort**
   - What we know: No existing port has timeout semantics.
   - What's unclear: What happens if an evaluation hangs?
   - Recommendation: Leave timeout to the port implementation, not the
     protocol. Document that implementations should be bounded.

3. **FinalSubmissionSnapshot persistence**
   - What we know: `StateStorePort` needs `write_final_submission` and
     `load_final_submission` methods.
   - What's unclear: Should it be a new protocol method or a generic
     write method?
   - Recommendation: Follow the explicit-method pattern used for every
     other snapshot type. Add two methods to `StateStorePort`.

4. **Quality threshold: median vs percentile**
   - What we know: CONTEXT.md says "median validation_score of the pool".
   - What's unclear: Is median always the right cutoff? With 3 candidates,
     median filters only 1.
   - Recommendation: Use median as the CONTEXT.md locked decision specifies.
     Claude's discretion area notes "median vs percentile" but median is
     the simpler and more predictable choice.

5. **MergeDesign.holdout_score after replacement**
   - What we know: Field remains on the dataclass; `LLMTraceMerger` sets it.
   - What's unclear: Should the field be deprecated?
   - Recommendation: Keep it. It's still useful for merge-time scoring. The
     replacement only affects the gate function, not the score source.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.4.0 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_phase28*.py -x` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P28-HOLDOUT | HoldoutSplitPort and EvaluationPort protocol compliance | unit | `pytest tests/test_phase28_holdout_ports.py -x` | Wave 0 |
| P28-HOLDOUT | StratifiedKFoldSplitter produces K=5 folds | unit | `pytest tests/test_phase28_holdout_ports.py::test_default_splitter_produces_5_folds -x` | Wave 0 |
| P28-RANK | Rank by mean desc, std asc tiebreak | unit | `pytest tests/test_phase28_ranking.py -x` | Wave 0 |
| P28-RANK | Single-candidate edge case (std=0) | unit | `pytest tests/test_phase28_ranking.py::test_single_candidate_std_zero -x` | Wave 0 |
| P28-COLLECT | Frontier + MERGED nodes collected | unit | `pytest tests/test_phase28_holdout_service.py::test_candidate_collection -x` | Wave 0 |
| P28-COLLECT | Quality threshold filters below median | unit | `pytest tests/test_phase28_holdout_service.py::test_quality_threshold_filter -x` | Wave 0 |
| P28-ACTIVATE | Auto-finalization at max_rounds | integration | `pytest tests/test_phase28_activation.py::test_auto_finalization_at_budget -x` | Wave 0 |
| P28-ACTIVATE | Early finalization entry point | integration | `pytest tests/test_phase28_activation.py::test_early_finalization -x` | Wave 0 |
| P28-REPLACE | validate_merge_holdout removed, HoldoutValidationService used | integration | `pytest tests/test_phase28_activation.py::test_proxy_replacement -x` | Wave 0 |
| P28-SUBMIT | FinalSubmissionSnapshot persisted with ancestry | integration | `pytest tests/test_phase28_holdout_service.py::test_final_submission_ancestry -x` | Wave 0 |
| P28-PRESENT | Operator guidance rendered for finalization | unit | `pytest tests/test_phase28_holdout_service.py::test_operator_presentation -x` | Wave 0 |
| P28-E2E | Full lifecycle: explore rounds -> finalize -> ranked submission | integration | `pytest tests/test_phase28_integration.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_phase28*.py -x`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase28_holdout_ports.py` -- covers P28-HOLDOUT
- [ ] `tests/test_phase28_ranking.py` -- covers P28-RANK
- [ ] `tests/test_phase28_holdout_service.py` -- covers P28-COLLECT, P28-SUBMIT, P28-PRESENT
- [ ] `tests/test_phase28_activation.py` -- covers P28-ACTIVATE, P28-REPLACE
- [ ] `tests/test_phase28_integration.py` -- covers P28-E2E

*(All test files are new. Existing test infrastructure (pytest config, ArtifactStateStore test helper, tmp_path fixture) fully covers the testing needs.)*

## Sources

### Primary (HIGH confidence)
- `v3/contracts/exploration.py` -- NodeMetrics, DAGNodeSnapshot, EdgeType, existing contract patterns
- `v3/ports/state_store.py` -- StateStorePort protocol pattern
- `v3/ports/embedding_port.py` -- EmbeddingPort/StubEmbeddingPort pattern (template for new ports)
- `v3/orchestration/dag_service.py` -- get_frontier, get_ancestors, update_node_metrics, list_nodes
- `v3/orchestration/branch_merge_service.py` -- validate_merge_holdout call site (line 185)
- `v3/orchestration/multi_branch_service.py` -- run_exploration_round round increment (line 265)
- `v3/algorithms/merge.py` -- validate_merge_holdout function (line 102)
- `v3/contracts/operator_guidance.py` -- OperatorGuidance contract
- `v3/orchestration/operator_guidance.py` -- render_operator_guidance_text, build_stage_guidance_response
- `v3/contracts/run.py` -- RunBoardSnapshot.current_round, max_rounds fields
- `tests/test_phase27_integration.py` -- Full lifecycle test pattern with _build_phase27_context
- `tests/test_phase27_merge_synthesis.py` -- Merge test patterns with _CapturingMerger

### Secondary (MEDIUM confidence)
- `28-CONTEXT.md` -- All locked decisions and design rationale

### Tertiary (LOW confidence)
- None. All findings verified against source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib + existing pydantic, zero new dependencies
- Architecture: HIGH -- follows established port/service/contract patterns verified in source
- Pitfalls: HIGH -- all pitfalls derived from actual code patterns and constraint analysis
- Validation: HIGH -- test framework fully configured, test patterns established in Phase 27

**Research date:** 2026-03-24
**Valid until:** Indefinite (no external dependencies, all findings verified against project source)
