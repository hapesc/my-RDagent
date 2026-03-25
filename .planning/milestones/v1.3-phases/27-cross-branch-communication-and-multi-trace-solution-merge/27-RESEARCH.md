# Phase 27: Cross-branch communication and multi-trace solution merge - Research

**Researched:** 2026-03-23
**Domain:** Multi-branch convergence mechanism (layers 2-3): interaction kernel, global best injection, complementary merge
**Confidence:** HIGH

## Summary

Phase 27 builds directly on Phase 26's DAG topology, SelectParents, and pruning infrastructure. The codebase already has placeholder contracts (EdgeType.SHARED/MERGED, BranchDecisionKind.SHARE/MERGE), existing services (BranchShareService, BranchMergeService, DAGService), and algorithm helpers (cosine_decay, softmax_prior in scoring_service) that Phase 27 upgrades from simple heuristics to the full probabilistic interaction kernel + LLM-driven synthesis pipeline.

The core technical challenge is NOT greenfield -- it is upgrading six existing services in a coordinated way while preserving backward compatibility with Phase 16/26 tests. The interaction kernel formula, ComponentClass tagging, and merge synthesis are all new algorithms, but they plug into well-defined extension points.

**Primary recommendation:** Implement in dependency order: (1) ComponentClass contract + tagging, (2) probabilistic interaction kernel + embedding port, (3) global best injection into MultiBranchService, (4) pruning signal 4, (5) SelectParents complementarity, (6) LLM-driven merge synthesis + holdout validation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Global best injection**: After propose stage, before candidate pool finalized. Three-part candidate pool ($h_c$, $h^*$, $h_s$). LLM Select/Modify/Create adaptive processing.
- **Interaction kernel**: $U_{ij} = \alpha S_{ij} e^{-\gamma L} + \beta \tanh(\Delta_{ij})$ with Softmax normalization + categorical sampling. Dynamic K (early=3, mid=1, late=2).
- **Anti-convergence**: Four-layer intrinsic mechanism, NOT a separate penalty term.
- **Complementarity**: Two metrics -- ComponentClass coverage + semantic distance $(1-S_{ij})$. ApproachCategory x ComponentClass two-dimensional model.
- **SelectParents merge stage**: When budget_ratio >= 0.8, seek non-overlapping component parents (not K=1 fallback).
- **Pruning signal 4**: Functional preservation -- exempt branches with unique components absent from higher-scoring branches.
- **Multi-trace merge**: Trigger at budget_ratio >= 0.8. LLM-driven Select/Modify/Create synthesis. Conflict resolution by Valid Score or LLM adaptation. MERGED edges in DAG. Basic holdout validation.
- **Sharing records**: Dual recording -- BranchDecisionSnapshot(kind=SHARE) + DAG SHARED edge.
- **Embedding source**: External embedding service (e.g., OpenAI text-embedding-3).

### Claude's Discretion
- Exact hyperparameter defaults for alpha, beta, gamma
- ComponentClass tagging implementation (LLM vs heuristic)
- EmbeddingPort abstraction design
- Error handling when parent nodes pruned during merge prep
- Holdout split ratio and validation methodology (basic version)
- MergeAdapter protocol evolution for LLM-driven synthesis

### Deferred Ideas (OUT OF SCOPE)
- Phase 28: Advanced parallel validation, multi-checkpoint comparison, cross-run ranking
- Future: Embedding-based DiversityService, virtual evaluation filtering, cross-run DAG, visual DAG rendering, problem-dimension alignment scoring
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | (existing) | Immutable contracts with ConfigDict(extra="forbid", frozen=True) | Project convention |
| numpy | (existing or add) | Softmax computation, vector ops for interaction kernel | Standard numerical |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai | (external) | text-embedding-3 for hypothesis vectorization | Behind EmbeddingPort abstraction |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| numpy softmax | Pure math.exp loop | numpy cleaner for batch ops but adds dependency; pure Python acceptable for small branch counts (<50) |

**Note:** The codebase already uses `math.exp` for softmax in `scoring_service.py::_softmax_prior`. Follow the same pure-Python pattern for consistency unless batch sizes demand numpy.

## Architecture Patterns

### Recommended Project Structure
```
v3/
├── contracts/
│   └── exploration.py          # Add ComponentClass enum, InteractionPotential, MergeCandidate
├── algorithms/
│   ├── decay.py                # Existing cosine_decay (reuse for kernel time decay)
│   ├── interaction_kernel.py   # NEW: U_ij computation, softmax, categorical sampling
│   ├── complementarity.py      # NEW: ComponentClass coverage + semantic distance
│   ├── merge.py                # EXTEND: MergeAdapter -> LLM Select/Modify/Create
│   └── prune.py                # EXTEND: Add signal 4 (functional preservation)
├── orchestration/
│   ├── branch_share_service.py # UPGRADE: Probabilistic kernel replaces simple similarity
│   ├── branch_merge_service.py # UPGRADE: Complementary analysis + LLM synthesis
│   ├── branch_prune_service.py # EXTEND: Pass ComponentClass data for signal 4
│   ├── select_parents_service.py # EXTEND: Complementarity dimension scoring
│   ├── multi_branch_service.py # EXTEND: Global best injection + merge orchestration
│   ├── dag_service.py          # EXTEND: SHARED/MERGED edge creation helpers
│   └── scoring_service.py      # EXTEND: Complementarity scoring
├── ports/
│   └── embedding_port.py       # NEW: Protocol for external embedding service
```

### Pattern 1: Pure Algorithm + Service Wrapper
**What:** Stateless algorithm functions in `v3/algorithms/`, stateful orchestration in `v3/orchestration/`
**When to use:** Always -- established codebase pattern
**Example:**
```python
# v3/algorithms/interaction_kernel.py (pure, testable)
def compute_interaction_potential(
    similarity: float,
    score_delta: float,
    depth: int,
    *,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.1,
) -> float:
    time_decay = math.exp(-gamma * depth)
    return alpha * similarity * time_decay + beta * math.tanh(score_delta)

def softmax_sample(potentials: list[float], k: int) -> list[int]:
    # Softmax -> categorical sampling, return k indices
    ...
```

### Pattern 2: Port Protocol for External Dependencies
**What:** External embedding behind a Protocol so tests use stubs
**When to use:** For EmbeddingPort (external API dependency)
**Example:**
```python
# v3/ports/embedding_port.py
class EmbeddingPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

# Stub for tests
class StubEmbeddingPort:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 256 for _ in texts]
```

### Pattern 3: Incremental Contract Extension
**What:** Add new fields with backward-compatible defaults to existing Pydantic models
**When to use:** ComponentClass in NodeMetrics, complementarity in scoring
**Example:**
```python
# Extend NodeMetrics with optional complementarity_score
class NodeMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    # ... existing fields ...
    complementarity_score: float = Field(default=0.0, ge=0.0)  # NEW Phase 27
```

### Anti-Patterns to Avoid
- **Mutating existing service state:** All services use StateStorePort -- never cache mutable state internally
- **Embedding calls in hot loops:** Batch embedding requests, cache per-round
- **Tight coupling to OpenAI:** Must use EmbeddingPort protocol; never import openai directly in algorithms/orchestration
- **Breaking Phase 26 tests:** All new fields must have backward-compatible defaults

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Softmax normalization | Custom overflow-prone exp | Subtract max trick (already in _softmax_prior) | Numerical stability |
| Cosine similarity | Manual dot product | Use the interaction kernel's embedding vectors with standard formula | Edge cases (zero vectors) |
| Categorical sampling | Custom random selection | `random.choices(population, weights=probs, k=K)` | Standard library, correct weighted sampling |
| Time decay | New decay function | Reuse `math.exp(-gamma * depth)` inline or wrap cosine_decay | Consistency with existing decay.py |

## Common Pitfalls

### Pitfall 1: Softmax Numerical Overflow
**What goes wrong:** Large U_ij values cause exp() overflow
**Why it happens:** Unbounded alpha * similarity * time_decay + beta * tanh(delta)
**How to avoid:** Always subtract max(U_ij) before exp(). The codebase already does this in `_softmax_prior`.
**Warning signs:** NaN or Inf in kernel weights

### Pitfall 2: Empty Embedding Cache on First Round
**What goes wrong:** Interaction kernel needs embeddings but no hypotheses exist yet
**Why it happens:** Round 0 has no prior hypothesis text to embed
**How to avoid:** Skip cross-branch sharing on round 0 (only local hypotheses). Guard with `if run.current_round == 0: return []`
**Warning signs:** KeyError on branch lookup during sharing

### Pitfall 3: Pruned Parent During Merge Prep
**What goes wrong:** Selected merge parent was pruned between selection and synthesis
**Why it happens:** Pruning runs after exploration round; merge prep may reference stale nodes
**How to avoid:** Re-validate parent node existence before merge. Fall back to next-best candidate.
**Warning signs:** KeyError loading branch snapshot for merge source

### Pitfall 4: ComponentClass Tagging Inconsistency
**What goes wrong:** Same code tagged differently across rounds, breaking complementarity
**Why it happens:** LLM-based tagging is non-deterministic
**How to avoid:** Prefer heuristic keyword-based classification with LLM fallback. Cache tags per branch.
**Warning signs:** Complementarity scores oscillating between rounds

### Pitfall 5: Circular MERGED Edges
**What goes wrong:** Merge result re-selected as merge input in same cycle
**Why it happens:** Frontier query returns merge node alongside source nodes
**How to avoid:** Exclude nodes created in the current merge round from merge candidate pool
**Warning signs:** Infinite merge loop, stack overflow in DAG traversal

## Code Examples

### Interaction Kernel Computation
```python
# v3/algorithms/interaction_kernel.py
import math
import random

def compute_interaction_potential(
    similarity: float,
    score_delta: float,
    depth: int,
    *,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.1,
) -> float:
    time_decay = math.exp(-gamma * depth)
    return alpha * similarity * time_decay + beta * math.tanh(score_delta)


def softmax_weights(potentials: list[float]) -> list[float]:
    if not potentials:
        return []
    max_u = max(potentials)
    exps = [math.exp(u - max_u) for u in potentials]
    total = sum(exps)
    if total == 0.0:
        return [1.0 / len(potentials)] * len(potentials)
    return [e / total for e in exps]


def sample_branches(
    potentials: list[float],
    branch_ids: list[str],
    k: int,
) -> list[str]:
    weights = softmax_weights(potentials)
    selected = random.choices(branch_ids, weights=weights, k=k)
    return list(dict.fromkeys(selected))  # deduplicate preserving order
```

### ComponentClass Enum and Coverage
```python
# In v3/contracts/exploration.py
class ComponentClass(StrEnum):
    DATA_LOAD = "data_load"
    FEATURE_ENG = "feature_eng"
    MODEL = "model"
    ENSEMBLE = "ensemble"
    WORKFLOW = "workflow"

# v3/algorithms/complementarity.py
def component_coverage_distance(
    branch_a_components: dict[str, float],  # ComponentClass -> best score
    branch_b_components: dict[str, float],
) -> float:
    all_classes = set(branch_a_components) | set(branch_b_components)
    if not all_classes:
        return 0.0
    complementary = 0
    for cls in all_classes:
        a_score = branch_a_components.get(cls, 0.0)
        b_score = branch_b_components.get(cls, 0.0)
        if (a_score > 0.7) != (b_score > 0.7):  # one strong, one weak
            complementary += 1
    return complementary / len(all_classes)
```

### Pruning Signal 4
```python
# Extension to v3/algorithms/prune.py
def has_unique_components(
    branch_id: str,
    branch_components: dict[str, set[str]],  # branch_id -> set of ComponentClass
    global_best_components: set[str],
) -> bool:
    branch_comps = branch_components.get(branch_id, set())
    unique = branch_comps - global_best_components
    return len(unique) > 0
```

## State of the Art

| Old Approach (Phase 16) | Current Approach (Phase 27) | Impact |
|--------------------------|----------------------------|--------|
| Fixed similarity threshold (>= 0.6) for sharing | Probabilistic interaction kernel with time decay | Natural exploration/exploitation balance |
| Shortlist + quality gap merge gate | Complementary component analysis + LLM synthesis | Merge leverages diverse branch strengths |
| K=1 fallback at merge stage | K=2+ complementary parent selection | Better merge inputs |
| 3-signal pruning | 4-signal pruning (+ functional preservation) | Preserves unique merge fragments |
| Simple text merge (SimpleTraceMerger) | LLM-driven Select/Modify/Create | Semantically coherent code fusion |

## Open Questions

1. **Embedding Dimension and Caching Strategy**
   - What we know: Need text-embedding-3 for hypothesis vectorization
   - What's unclear: Whether to cache embeddings in StateStorePort or in-memory per round
   - Recommendation: In-memory cache per round (embeddings are transient computation, not persisted state). Add optional `embedding_cache` field to run context.

2. **ComponentClass Tagging: Heuristic vs LLM**
   - What we know: Need deterministic-enough tagging for complementarity stability
   - What's unclear: Whether keyword heuristics are sufficient
   - Recommendation: Start with keyword heuristic (regex on code structure -- imports, class names). LLM fallback for ambiguous cases. This is Claude's discretion area.

3. **Holdout Validation Methodology**
   - What we know: Phase 27 needs basic holdout; Phase 28 adds rigor
   - What's unclear: Exact split ratio, whether to use synthetic holdout or real data partition
   - Recommendation: Simple 80/20 train/holdout split. Score merged candidate on holdout. Accept if holdout_score > best_single_branch_holdout_score. Defer cross-validation to Phase 28.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml (existing) |
| Quick run command | `python -m pytest tests/test_phase27_*.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P27-KERNEL | Interaction kernel computes U_ij correctly with softmax + sampling | unit | `pytest tests/test_phase27_interaction_kernel.py -x` | Wave 0 |
| P27-INJECT | Global best + h_s injected into candidate pool | unit | `pytest tests/test_phase27_global_injection.py -x` | Wave 0 |
| P27-COMPONENT | ComponentClass tagging + coverage distance | unit | `pytest tests/test_phase27_complementarity.py -x` | Wave 0 |
| P27-SELECT | SelectParents merge-stage complementary selection | unit | `pytest tests/test_phase27_select_parents.py -x` | Wave 0 |
| P27-PRUNE4 | Signal 4 functional preservation in pruning | unit | `pytest tests/test_phase27_prune_signal4.py -x` | Wave 0 |
| P27-MERGE | LLM-driven merge synthesis + MERGED edges + holdout | integration | `pytest tests/test_phase27_merge_synthesis.py -x` | Wave 0 |
| P27-E2E | Full round with sharing + pruning + merge | integration | `pytest tests/test_phase27_integration.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_phase27_*.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `tests/test_phase27_interaction_kernel.py` -- covers P27-KERNEL
- [ ] `tests/test_phase27_complementarity.py` -- covers P27-COMPONENT
- [ ] `tests/test_phase27_global_injection.py` -- covers P27-INJECT
- [ ] `tests/test_phase27_select_parents.py` -- covers P27-SELECT
- [ ] `tests/test_phase27_prune_signal4.py` -- covers P27-PRUNE4
- [ ] `tests/test_phase27_merge_synthesis.py` -- covers P27-MERGE
- [ ] `tests/test_phase27_integration.py` -- covers P27-E2E
- [ ] `v3/ports/embedding_port.py` -- StubEmbeddingPort for all tests

## Sources

### Primary (HIGH confidence)
- Direct code reading of all 8 source files listed in CONTEXT.md canonical_refs
- Phase 26 contracts and services (verified in codebase)
- 27-CONTEXT.md locked decisions

### Secondary (MEDIUM confidence)
- Softmax numerical stability: standard ML practice (subtract-max trick)
- `random.choices` for categorical sampling: Python stdlib docs

### Tertiary (LOW confidence)
- None -- all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project or standard Python
- Architecture: HIGH - follows established codebase patterns exactly
- Pitfalls: HIGH - derived from direct code analysis of existing services

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable internal codebase patterns)
