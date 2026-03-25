# Phase 31: Finalization State Interface Enhancement and Default External Ports - Research

**Researched:** 2026-03-25
**Domain:** Python StrEnum extension, port protocol pattern, lightweight embedding, CLI tool registration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Run lifecycle visibility — ExplorationMode extension**
- Extend `ExplorationMode` enum with `FINALIZED = "finalized"`.
- Run lifecycle now follows: `EXPLORATION → CONVERGENCE → FINALIZED`.
- `MultiBranchService._try_finalize()` writes `FINALIZED` to run snapshot automatically when holdout finalization succeeds.
- `BranchBoardSnapshot.mode` synchronizes to `FINALIZED` alongside the run snapshot — the entire board surface reflects finalization state.
- Minimal change: no extra fields (no `is_finalized`, no `final_submission_id`). `ExplorationMode.FINALIZED` + existing `FinalSubmissionSnapshot` is sufficient.

**Default port implementations — centralized defaults module**
- All default port implementations live in a new `v3/ports/defaults.py` (or `v3/ports/default_impls/` directory) — separate from the protocol definitions.
- **DefaultHoldoutSplitPort**: Real random shuffle + split of validation data into K folds. Replaces the opaque string-reference-only `StratifiedKFoldSplitter` as the production default.
- **DefaultEvaluationPort**: Parameterized implementation accepting `eval_fn: Callable` and `dataset_ref: str`. Reads fold partitions from the split port's output, runs `eval_fn` on the holdout partition. Does NOT re-implement split.
- **DefaultEmbeddingPort**: Research the lightest available embedding approach and integrate it. Researcher task to survey options (e.g., sentence-transformers MiniLM, TF-IDF vectors, hash-based). Pick the lightest that produces semantically meaningful vectors for interaction kernel scoring.

**rd_agent() entry behavior — graceful degradation**
- Remove the `ValueError` when `holdout_evaluation_port` is missing.
- When holdout port is absent: silently fall back to Phase 27 convergence path (shortlist + merge). Add `finalization_skipped: true` to `structuredContent` response so callers know holdout finalization was not performed.
- When holdout port is present: proceed with full holdout finalization as today.

**Embedding-absent sharing — agent-driven candidate selection**
- When `EmbeddingPort` is unavailable: degrade to agent-selected sharing candidates only. The agent determines which branches help the current branch and injects them via `branch_list` parameter in CLI tool calls.
- When `EmbeddingPort` is available: **hybrid retrieval** — union of interaction kernel computed candidates AND agent-selected candidates. Both pools merged, deduplicated.
- No `LLMJudgePort` needed. The agent IS the LLM judge. CLI tool surface accepts `branch_list` as an explicit sharing-candidates input parameter.

**State query convenience**
- Adding `FINALIZED` to `ExplorationMode` is sufficient. No extra helper, service, or computed property needed. Callers check `run.exploration_mode`.
- Exploration round progress ("exploring round 3/20") integrated into existing `OperatorGuidance` current_state text generation. No new structured field.

**Finalization entry explicitness**
- Add public `should_finalize(run_id) -> bool` method on `MultiBranchService`. Checks `current_round >= max_rounds` and holdout service availability.
- `_try_finalize()` stays private — internal to exploration round.
- `finalize_early()` stays public as-is.
- Both `should_finalize` and `finalize_early` exposed through CLI tool surface (rd-tool-catalog) so operators can query and trigger finalization from terminal.

### Claude's Discretion
- Exact `DefaultHoldoutSplitPort` shuffle and stratification strategy
- `DefaultEvaluationPort` error handling when eval_fn raises
- Exact CLI tool names and argument shapes for finalize commands
- Whether defaults module is a single file or a sub-package
- How `branch_list` parameter integrates into existing dispatch payload schema

### Deferred Ideas (OUT OF SCOPE)
- Cross-run finalization comparison (requires comparable holdout sets — hard)
- Visual finalization dashboard with interactive ranking table
- Adaptive K selection for holdout folds based on candidate pool size
- Ensemble submission (combine Top-N candidates instead of selecting one)
- Auto-retry finalization when transient port failures occur
- Finalization rollback (undo FINALIZED state and resume exploration)
</user_constraints>

---

## Summary

Phase 31 is a pure surface-hardening phase. All required capability already exists in the codebase — Phase 28 implemented the full holdout finalization pipeline, Phase 27 implemented interaction-kernel sharing. Phase 31 makes the state surface explicit (`FINALIZED` enum member), reduces entry friction (default port implementations in `v3/ports/defaults.py`), and degrades more gracefully (remove `ValueError` on missing holdout port, add `finalization_skipped`).

The work decomposes cleanly into four independent streams: (1) enum extension + mode write propagation, (2) defaults module with three port implementations, (3) entry-layer graceful degradation + `branch_list` parameter, and (4) CLI tool registration for `should_finalize` and `finalize_early`. None of these streams requires new contracts or architecture — only targeted additions and removals in existing files.

The lightest viable default embedding for hypothesis-text comparison is TF-IDF (zero external dependencies, produces semantically meaningful sparse vectors for short hypothesis labels). `sentence-transformers` with MiniLM is preferred when semantic similarity beyond keyword overlap is needed and the ~80MB download is acceptable; it is the correct production choice for V3's use case of comparing hypothesis labels.

**Primary recommendation:** Implement all four streams in a single phase plan wave structure. Start with `ExplorationMode.FINALIZED` (zero risk, unblocks all downstream tests), then defaults module, then entry-layer changes, then CLI tool registration. Keep `StratifiedKFoldSplitter` in `holdout_port.py` for backward-compatibility — add `DefaultHoldoutSplitPort` as new symbol in `defaults.py`.

---

## Standard Stack

### Core (already present in repo)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python StrEnum | stdlib 3.11+ | `ExplorationMode` extension | Already used; `StrEnum` is the project's enum base |
| Pydantic v2 | `^2.x` (repo-confirmed) | Contract frozen models | All V3 contracts use `ConfigDict(extra="forbid", frozen=True)` |
| `typing.Protocol` | stdlib | Port protocol definitions | All V3 ports use Protocol, not ABC |
| `collections.abc.Callable` | stdlib | `eval_fn` type annotation | Project convention for callable types |

### Embedding (DefaultEmbeddingPort)

| Option | Size | Quality | Dependency | Verdict |
|--------|------|---------|-----------|---------|
| TF-IDF (scikit-learn) | ~5MB (already in ML envs) | keyword similarity | `scikit-learn` | Use if sklearn available; no network |
| Hash bag-of-words | 0MB | character-level only | none | Too weak for hypothesis comparison |
| `sentence-transformers` MiniLM-L6 | ~80MB download | semantic similarity | `sentence-transformers` | Best quality; use when available |
| OpenAI embeddings API | 0MB local | highest quality | network + API key | Violates zero-external-service constraint |

**Decision guidance (Claude's Discretion area):** Implement `DefaultEmbeddingPort` using **TF-IDF as the no-dependency fallback** with a constructor parameter to inject a sentence-transformers model when available. This gives zero-friction default with upgrade path. The CONTEXT.md constraint is "zero external service dependency" and "< 100MB model size" — both satisfied by TF-IDF.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | repo-present | TF-IDF vector math, cosine similarity | DefaultEmbeddingPort inner computation |
| `random` | stdlib | DefaultHoldoutSplitPort shuffle | Deterministic with seed for testing |
| `uuid` | stdlib | Port implementation IDs | Consistent with existing port patterns |

**Installation:** No new dependencies required. TF-IDF can be implemented with stdlib `collections.Counter` and `math` if scikit-learn is not available. The planner should NOT add new `pyproject.toml` dependencies unless sentence-transformers is chosen.

---

## Architecture Patterns

### Existing Pattern: Port Protocols in `v3/ports/`

Protocol definitions live in `v3/ports/{name}_port.py`. Stub implementations (test-only) co-locate with protocols. Default implementations (production defaults) move to `v3/ports/defaults.py`.

```
v3/ports/
├── holdout_port.py       # HoldoutSplitPort, EvaluationPort, StubHoldoutSplitPort, StubEvaluationPort
├── embedding_port.py     # EmbeddingPort, EmbeddingUnavailableError, StubEmbeddingPort
├── state_store.py        # StateStorePort protocol
└── defaults.py           # NEW: DefaultHoldoutSplitPort, DefaultEvaluationPort, DefaultEmbeddingPort
```

Note: `StratifiedKFoldSplitter` stays in `holdout_port.py` — backward-compatible. `DefaultHoldoutSplitPort` is a new name in `defaults.py`.

### Existing Pattern: StrEnum for ExplorationMode

`ExplorationMode` is in `v3/contracts/exploration.py`. It is a `StrEnum`. Adding `FINALIZED = "finalized"` is a one-line change. All models using `ExplorationMode` as a field type (`BranchBoardSnapshot.mode`, `RunBoardSnapshot.exploration_mode`, `BranchDecisionSnapshot.mode`, `MergeOutcomeSnapshot.mode`, `BranchBoardRef.mode`) will accept the new value automatically because the field is typed as `ExplorationMode`, which is validated by Pydantic.

```python
# Source: v3/contracts/exploration.py (current)
class ExplorationMode(StrEnum):
    EXPLORATION = "exploration"
    CONVERGENCE = "convergence"
    # ADD:
    FINALIZED = "finalized"
```

### Pattern: Mode Write on Finalization

The finalization mode write happens in two places:
1. `MultiBranchService._try_finalize()` — auto-finalization when budget exhausted
2. `MultiBranchService.finalize_early()` — operator-triggered

Both currently return `FinalSubmissionSnapshot | None` or `FinalSubmissionSnapshot`. After writing the submission, they must also write `FINALIZED` to:
- `RunBoardSnapshot.exploration_mode`
- `BranchBoardSnapshot.mode` (via `BranchBoardService.get_board` + `model_copy`)

```python
# Pattern: how to write FINALIZED mode to RunBoardSnapshot
run = self._state_store.load_run_snapshot(run_id)
if run is not None:
    self._state_store.write_run_snapshot(
        run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})
    )
```

The `BranchBoardSnapshot` is built by `BranchBoardService.get_board()` from live branch data — it does not persist independently. Therefore the board's `mode` field must be set at read time by checking the run's `exploration_mode`. Research finding: `BranchBoardService.get_board()` currently uses `ExplorationMode.EXPLORATION` as the board mode. It must be updated to read the run's current `exploration_mode` and propagate it.

### Pattern: Graceful Degradation in rd_agent()

Current code raises `ValueError` when `hypothesis_specs` is provided but `holdout_evaluation_port` is `None` (lines 333-338 of `v3/entry/rd_agent.py`). The locked decision removes this guard:

```python
# BEFORE (to be removed):
if hypothesis_specs is not None and holdout_evaluation_port is None:
    raise ValueError(...)

# AFTER: no guard. holdout_validation_service will be None when evaluation_port is None.
# The _try_finalize() path already handles None holdout_validation_service gracefully.
```

The `finalization_skipped` flag goes into `structuredContent`:
```python
# In the rd_agent() multi-branch return dict:
"finalization_skipped": explore_round.finalization_submission is None and holdout_evaluation_port is None,
```

### Pattern: branch_list in ExploreRoundRequest

`ExploreRoundRequest` (in `v3/contracts/tool_io.py`) needs a new optional field:

```python
class ExploreRoundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str = Field(min_length=1)
    hypotheses: list[str] = Field(default_factory=list)
    hypothesis_specs: list[HypothesisSpec] | None = None
    auto_prune: bool = Field(default=True)
    branch_list: list[str] = Field(default_factory=list)  # ADD: agent-injected sharing candidates
```

`BranchShareService.compute_sharing_candidates()` signature must accept the agent-injected list and return the union after deduplication.

### Pattern: CLI Tool Registration

New tools follow the exact `_ToolSpec` dataclass pattern in `v3/entry/tool_catalog.py`. Two new tools:

1. `rd_should_finalize` — inspection category, calls `MultiBranchService.should_finalize(run_id)`
2. `rd_finalize_early` — primitives category, calls `MultiBranchService.finalize_early(run_id=...)`

These tools require `MultiBranchService` as a dependency, which is currently not a registered dependency type in `call_cli_tool`. Research finding: existing tools pass either `service` (RunBoardService) or `state_store` as dependencies. The new finalization tools need access to `MultiBranchService`. **Options:**
- Register a new dependency key `multi_branch_service`
- Or expose `should_finalize` and `finalize_early` as standalone functions that accept a `StateStorePort` + read the run snapshot directly

The second option avoids changing `call_cli_tool`'s dependency injection surface. Since `should_finalize` only reads state (`current_round >= max_rounds` + holdout service availability), it can be implemented as a pure read from `state_store`.

### Recommended Project Structure (Phase 31 additions)

```
v3/ports/
└── defaults.py           # NEW: DefaultHoldoutSplitPort, DefaultEvaluationPort, DefaultEmbeddingPort

v3/contracts/
└── exploration.py        # MODIFY: add FINALIZED to ExplorationMode

v3/orchestration/
├── multi_branch_service.py   # MODIFY: should_finalize(), _try_finalize() mode write, finalize_early() mode write
├── operator_guidance.py      # MODIFY: round progress in current_state text
└── branch_share_service.py   # MODIFY: hybrid retrieval, branch_list parameter

v3/entry/
├── rd_agent.py           # MODIFY: remove ValueError, add finalization_skipped, branch_list passthrough
└── tool_catalog.py       # MODIFY: add rd_should_finalize + rd_finalize_early tool specs

tests/
└── test_phase31_*.py     # NEW: one file per logical stream
```

### Anti-Patterns to Avoid

- **Don't add `is_finalized: bool` field to RunBoardSnapshot.** The locked decision is explicit: `ExplorationMode.FINALIZED` is sufficient. Adding a redundant field creates dual-truth.
- **Don't move `StratifiedKFoldSplitter` out of `holdout_port.py`.** Backward compatibility — existing callers import it from there.
- **Don't add `final_submission_id` to RunBoardSnapshot.** Out of scope per locked decisions.
- **Don't use ABC for new default port implementations.** Project pattern is `Protocol` for interfaces; concrete classes implement informally.
- **Don't raise on missing `branch_list`.** It must be optional with `default_factory=list`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text similarity for hypothesis labels | Custom cosine sim over raw strings | Existing `cosine_similarity` in `v3/algorithms/complementarity.py` | Already implemented and tested |
| Softmax normalization for sampling | Custom softmax | Existing `compute_interaction_potential` + `sample_branches` in `v3/algorithms/interaction_kernel.py` | Phase 27 helpers are already there |
| K-fold partition logic | Custom list slicing | `DefaultHoldoutSplitPort` using `random.sample` with `random.seed` | Standard fold split is 5 lines |
| Embedding dimension normalization | Manual L2 norm | numpy `linalg.norm` | Existing pattern in `cosine_similarity` |

**Key insight:** Phase 31's value is surface clarity, not new algorithm work. All computation is already implemented in Phase 26-28. The planner should not create tasks for algorithm development.

---

## Common Pitfalls

### Pitfall 1: BranchBoardSnapshot.mode Not Propagating FINALIZED

**What goes wrong:** `_try_finalize()` writes `FINALIZED` to `RunBoardSnapshot.exploration_mode` but the board snapshot returned in `ExploreRoundResult.board` still shows `EXPLORATION` because `BranchBoardService.get_board()` constructs the mode from a hardcoded default.

**Why it happens:** `BranchBoardService.get_board()` builds `BranchBoardSnapshot` independently from the run snapshot. If it does not read `run.exploration_mode`, the board surface lags behind.

**How to avoid:** In `BranchBoardService.get_board()`, load the run snapshot and use `run.exploration_mode` as the board's `mode` field. Fall back to `ExplorationMode.EXPLORATION` if run is not found.

**Warning signs:** Test asserts `board.mode == ExplorationMode.FINALIZED` but finds `EXPLORATION` after finalization.

### Pitfall 2: Pydantic `frozen=True` Blocks model_copy on StrEnum Fields

**What goes wrong:** `run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})` silently fails or raises if the field type annotation doesn't accept the new enum member.

**Why it happens:** Non-issue in this case — Pydantic accepts new `StrEnum` members automatically. But if any `Literal` type annotation was used instead of `ExplorationMode`, the new value would fail validation.

**How to avoid:** Verify `RunBoardSnapshot.exploration_mode` is annotated as `ExplorationMode | None`, not a `Literal`. It currently is (confirmed from source).

### Pitfall 3: call_cli_tool Dependency Injection for New Tools

**What goes wrong:** Registering `rd_should_finalize` with `dependency_names=("multi_branch_service",)` but `call_cli_tool` callers never pass `multi_branch_service` — the dependency was never registered as a known key.

**Why it happens:** Existing callers of `call_cli_tool` only pass `service` (RunBoardService) or `state_store`. New tools requiring `MultiBranchService` break existing call sites.

**How to avoid:** Implement `should_finalize` as a state-read-only function that accepts `state_store: StateStorePort` — then register with `dependency_names=("state_store",)`. For `finalize_early`, it DOES need `MultiBranchService`. The planner must decide: either add `multi_branch_service` as a new dependency key (requires updating all `call_cli_tool` callers to pass it), or implement `finalize_early` as a tool that calls `HoldoutValidationService.finalize()` directly with `state_store` + `dag_service` dependencies (matching existing injection patterns).

**Recommendation:** Create a thin `rd_should_finalize` handler that reads `RunBoardSnapshot.current_round` and `RunBoardSnapshot.max_rounds` from `state_store`. Create `rd_finalize_early` with dependency `("service",)` where `service` is already `RunBoardService` — but `finalize_early` needs `HoldoutValidationService`. The cleanest path: expose `MultiBranchService` as an optional dependency key and pass it explicitly from the caller, OR refactor `finalize_early` CLI handler to construct `HoldoutValidationService` from injected ports.

### Pitfall 4: DefaultHoldoutSplitPort Produces String Refs, Not Real Data

**What goes wrong:** Implementing `DefaultHoldoutSplitPort.split()` to return `FoldSpec` objects where `train_ref` and `holdout_ref` are still opaque strings (like the existing `StratifiedKFoldSplitter`), defeating the purpose.

**Why it happens:** `FoldSpec.train_ref` and `holdout_ref` are typed as `str`, so it's easy to just produce new string references without actual data.

**How to avoid:** The CONTEXT.md decision says "Real random shuffle + split of validation data into K folds." This means `DefaultHoldoutSplitPort` must accept actual data (e.g., a dataset reference or path) at construction time, shuffle it with `random.shuffle`, and store actual partition references that `DefaultEvaluationPort` can read. The fold references must be resolvable, not opaque.

**Warning signs:** `DefaultEvaluationPort.evaluate()` receives a `FoldSpec` with `holdout_ref` it cannot resolve.

### Pitfall 5: branch_list Merging Creates Duplicates in Dispatch Payload

**What goes wrong:** Agent-injected `branch_list` and kernel-computed candidates are merged in `compute_sharing_candidates()`, but the deduplication step in `_compute_sharing()` in `MultiBranchService` runs separately, resulting in duplicate entries in the payload.

**How to avoid:** Single deduplication point: after merging kernel candidates and `branch_list`, apply `list(dict.fromkeys(...))` once. The existing pattern in `_compute_sharing()` already does this — just extend it to include the `branch_list` pool.

---

## Code Examples

Verified patterns from the current codebase:

### ExplorationMode Extension
```python
# Source: v3/contracts/exploration.py (current pattern, to be extended)
class ExplorationMode(StrEnum):
    """Operator-visible multi-branch mode."""
    EXPLORATION = "exploration"
    CONVERGENCE = "convergence"
    FINALIZED = "finalized"  # ADD THIS
```

### Mode Write After Finalization (_try_finalize pattern)
```python
# Source: v3/orchestration/multi_branch_service.py (to be extended)
def _try_finalize(self, run_id: str) -> FinalSubmissionSnapshot | None:
    run = self._state_store.load_run_snapshot(run_id)
    if run is not None:
        new_round = run.current_round + 1
        self._state_store.write_run_snapshot(run.model_copy(update={"current_round": new_round}))
        if new_round >= run.max_rounds and self._holdout_validation_service is not None:
            try:
                submission = self._holdout_validation_service.finalize(run_id=run_id)
                # ADD: write FINALIZED mode
                updated_run = self._state_store.load_run_snapshot(run_id)
                if updated_run is not None:
                    self._state_store.write_run_snapshot(
                        updated_run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})
                    )
                return submission
            except (ValueError, KeyError):
                return None
    return None
```

### DefaultHoldoutSplitPort Skeleton
```python
# Source: v3/ports/defaults.py (NEW file, following holdout_port.py Protocol)
import random
from v3.ports.holdout_port import FoldSpec, HoldoutSplitPort

class DefaultHoldoutSplitPort:
    """Production K-fold splitter with real random shuffle."""

    def __init__(self, k: int = 5, seed: int | None = None) -> None:
        self._k = k
        self._seed = seed

    def split(self, *, run_id: str) -> list[FoldSpec]:
        rng = random.Random(self._seed)
        # fold_index is enough for DefaultEvaluationPort to resolve partitions
        indices = list(range(self._k))
        rng.shuffle(indices)
        return [
            FoldSpec(
                fold_index=index,
                train_ref=f"{run_id}-default-train-{index}",
                holdout_ref=f"{run_id}-default-holdout-{index}",
            )
            for index in range(self._k)
        ]
```

### Graceful Degradation in rd_agent()
```python
# Source: v3/entry/rd_agent.py (current ValueError block to REMOVE)
# REMOVE these lines:
if hypothesis_specs is not None and holdout_evaluation_port is None:
    raise ValueError(...)

# The holdout_validation_service assignment already handles None gracefully:
holdout_validation_service = (
    HoldoutValidationService(...)
    if hypothesis_specs is not None and dag_service is not None and holdout_evaluation_port is not None
    else None
)
# Add to structuredContent return:
"finalization_skipped": explore_round.finalization_submission is None,
```

### should_finalize Public Method
```python
# Source: v3/orchestration/multi_branch_service.py (ADD)
def should_finalize(self, run_id: str) -> bool:
    """Query whether the run is ready for finalization."""
    run = self._state_store.load_run_snapshot(run_id)
    if run is None:
        return False
    return run.current_round >= run.max_rounds and self._holdout_validation_service is not None
```

### Hybrid Retrieval in compute_sharing_candidates
```python
# Source: v3/orchestration/branch_share_service.py (to be extended)
# After kernel-computed candidates are assembled, merge with agent_branch_list:
def compute_sharing_candidates(
    self,
    *,
    run_id: str,
    target_branch_id: str,
    current_round: int,
    budget_ratio: float,
    agent_branch_list: list[str] | None = None,  # ADD parameter
) -> list[str]:
    kernel_candidates = ...  # existing logic
    # Merge: kernel union agent, deduplicated, excluding target
    all_candidates = [*kernel_candidates, *(agent_branch_list or [])]
    return list(dict.fromkeys(c for c in all_candidates if c != target_branch_id))
```

### Round Progress in OperatorGuidance
```python
# Source: v3/orchestration/operator_guidance.py (to be extended)
# In build_finalization_guidance or a new helper:
def _round_progress_text(current_round: int, max_rounds: int) -> str:
    return f"exploring round {current_round}/{max_rounds}"

# Add to current_state in guidance builders:
current_state = f"Current state: ... {_round_progress_text(run.current_round, run.max_rounds)}."
```

---

## State of the Art

| Old Approach | Current Approach | Phase | Impact |
|--------------|------------------|-------|--------|
| `StratifiedKFoldSplitter` as default (opaque string refs) | `DefaultHoldoutSplitPort` (real shuffle) | Phase 31 | Callers get resolvable fold partitions |
| `StubEmbeddingPort` (zeros) | `DefaultEmbeddingPort` (TF-IDF or MiniLM) | Phase 31 | Sharing kernel produces meaningful similarity scores |
| `ValueError` on missing holdout port | Silent fallback + `finalization_skipped: true` | Phase 31 | Reduces setup friction for callers without holdout |
| `ExplorationMode` without terminal state | `ExplorationMode.FINALIZED` | Phase 31 | Callers can reliably detect run completion |
| No public finalization readiness query | `should_finalize(run_id) -> bool` | Phase 31 | Operators can probe before triggering |

---

## Open Questions

1. **BranchShareService.compute_sharing_candidates signature change**
   - What we know: The method is called from `MultiBranchService._compute_sharing()`, which has access to `ExploreRoundRequest.branch_list`.
   - What's unclear: Whether `branch_list` arrives via `ExploreRoundRequest` (requiring contract change) or as a separate parameter to `_compute_sharing()`.
   - Recommendation: Add `branch_list: list[str] = Field(default_factory=list)` to `ExploreRoundRequest`. Pass it through `_compute_sharing()` to `compute_sharing_candidates()`. This keeps the interface consistent without new plumbing.

2. **DefaultEmbeddingPort: TF-IDF vs sentence-transformers**
   - What we know: TF-IDF requires no external dependencies; sentence-transformers requires `~80MB` download.
   - What's unclear: Whether the project environment has `scikit-learn` already (it likely does given the ML context, but not confirmed).
   - Recommendation: Implement `DefaultEmbeddingPort` using Python stdlib `collections.Counter` + `math.log` for TF-IDF. No `scikit-learn` dependency. The interaction kernel only needs a cosine similarity of reasonable quality — TF-IDF over hypothesis labels is sufficient for the use case.

3. **CLI tool dependency injection for finalize_early**
   - What we know: `call_cli_tool` currently resolves `service` (RunBoardService) and `state_store` (StateStorePort) as dependency keys.
   - What's unclear: Whether to add `multi_branch_service` as a new dependency key or make `finalize_early` read from lower-level ports.
   - Recommendation: Add a new dependency key `multi_branch_service` to `call_cli_tool`. This is the clean path. Update `rd_agent.py` to pass the constructed `multi_branch_service` when calling finalization tools. The planner should create this as a distinct task.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_phase31*.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

Phase 31 has no formal requirement IDs (TBD per REQUIREMENTS.md). The behaviors map to test coverage as follows:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `ExplorationMode.FINALIZED` exists and is a valid StrEnum member | unit | `uv run pytest tests/test_phase31_enum.py -x` | Wave 0 |
| `_try_finalize()` writes FINALIZED mode to run snapshot on success | unit | `uv run pytest tests/test_phase31_mode_write.py -x` | Wave 0 |
| `finalize_early()` writes FINALIZED mode to run snapshot | unit | `uv run pytest tests/test_phase31_mode_write.py -x` | Wave 0 |
| `BranchBoardSnapshot.mode` reflects FINALIZED after finalization | unit | `uv run pytest tests/test_phase31_board_mode.py -x` | Wave 0 |
| `DefaultHoldoutSplitPort.split()` returns K FoldSpecs | unit | `uv run pytest tests/test_phase31_defaults.py -x` | Wave 0 |
| `DefaultEvaluationPort.evaluate()` calls eval_fn and returns float | unit | `uv run pytest tests/test_phase31_defaults.py -x` | Wave 0 |
| `DefaultEmbeddingPort.embed()` returns non-zero vectors | unit | `uv run pytest tests/test_phase31_defaults.py -x` | Wave 0 |
| `rd_agent()` does not raise when `holdout_evaluation_port=None` with `hypothesis_specs` | unit | `uv run pytest tests/test_phase31_entry.py -x` | Wave 0 |
| `structuredContent` includes `finalization_skipped: True` when port absent | unit | `uv run pytest tests/test_phase31_entry.py -x` | Wave 0 |
| `should_finalize()` returns True when `current_round >= max_rounds` | unit | `uv run pytest tests/test_phase31_service.py -x` | Wave 0 |
| `compute_sharing_candidates()` merges kernel + agent branch_list | unit | `uv run pytest tests/test_phase31_sharing.py -x` | Wave 0 |
| Hybrid retrieval deduplicates correctly | unit | `uv run pytest tests/test_phase31_sharing.py -x` | Wave 0 |
| `rd_should_finalize` CLI tool registered in catalog | unit | `uv run pytest tests/test_phase31_tools.py -x` | Wave 0 |
| `rd_finalize_early` CLI tool registered in catalog | unit | `uv run pytest tests/test_phase31_tools.py -x` | Wave 0 |
| Round progress appears in OperatorGuidance current_state text | unit | `uv run pytest tests/test_phase31_guidance.py -x` | Wave 0 |
| Full regression: existing Phase 28-29 tests still pass | integration | `uv run pytest tests/test_phase28*.py tests/test_phase29*.py -x -q` | Yes (22 passing) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_phase31*.py -x -q`
- **Per wave merge:** `uv run pytest -x -q` (full suite, 369 tests currently)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All `test_phase31_*.py` files are new and must be created before implementation:

- [ ] `tests/test_phase31_enum.py` — covers ExplorationMode.FINALIZED
- [ ] `tests/test_phase31_mode_write.py` — covers _try_finalize + finalize_early mode propagation
- [ ] `tests/test_phase31_board_mode.py` — covers BranchBoardSnapshot.mode sync
- [ ] `tests/test_phase31_defaults.py` — covers DefaultHoldoutSplitPort, DefaultEvaluationPort, DefaultEmbeddingPort
- [ ] `tests/test_phase31_entry.py` — covers rd_agent() graceful degradation + finalization_skipped
- [ ] `tests/test_phase31_service.py` — covers should_finalize() public method
- [ ] `tests/test_phase31_sharing.py` — covers hybrid retrieval + branch_list merging
- [ ] `tests/test_phase31_tools.py` — covers CLI tool registration for should_finalize + finalize_early
- [ ] `tests/test_phase31_guidance.py` — covers round progress in OperatorGuidance text

---

## Sources

### Primary (HIGH confidence)
- Source code analysis: `v3/contracts/exploration.py` — ExplorationMode as StrEnum with two members; direct extension point confirmed
- Source code analysis: `v3/contracts/run.py` — `RunBoardSnapshot.exploration_mode: ExplorationMode | None`, accepts any ExplorationMode member
- Source code analysis: `v3/orchestration/multi_branch_service.py` — `_try_finalize()` and `finalize_early()` patterns; neither writes FINALIZED mode today
- Source code analysis: `v3/entry/rd_agent.py` — lines 333-338 contain the `ValueError` to remove; `holdout_evaluation_port` is the trigger
- Source code analysis: `v3/ports/holdout_port.py` — `StratifiedKFoldSplitter` produces opaque string refs; `FoldSpec` contract is fixed
- Source code analysis: `v3/ports/embedding_port.py` — `StubEmbeddingPort` returns zeros; `EmbeddingUnavailableError` is the degradation signal
- Source code analysis: `v3/orchestration/branch_share_service.py` — `compute_sharing_candidates()` returns empty list when `self._embedding_port is None`
- Source code analysis: `v3/entry/tool_catalog.py` — `_ToolSpec` pattern; dependency keys are `"service"` and `"state_store"` today
- Test run: `uv run pytest tests/test_phase28*.py tests/test_phase29*.py` — 22 tests pass; baseline is green

### Secondary (MEDIUM confidence)
- `v3/contracts/tool_io.py` — `ExploreRoundRequest` has `extra="forbid"` so `branch_list` must be added explicitly before use
- `v3/orchestration/operator_guidance.py` — `build_finalization_guidance()` and `build_stage_operator_guidance()` patterns for text construction

### Tertiary (LOW confidence)
- DefaultEmbeddingPort TF-IDF implementation: standard technique, no external verification needed for stdlib approach; LOW confidence only because no test of quality vs. sentence-transformers in this codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already present; no new dependencies required
- Architecture: HIGH — patterns confirmed directly from source; no inference needed
- Pitfalls: HIGH — three of five pitfalls identified from direct code reading (BranchBoardSnapshot mode lag, ValueError removal, deduplication); two from pattern analysis (StrEnum Pydantic compatibility, dependency injection)

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable codebase, no fast-moving external dependencies)
