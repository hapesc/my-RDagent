# Phase 29: Entry-layer service wiring - Research

**Researched:** 2026-03-24
**Domain:** Python dependency injection, V3 entrypoint wiring, integration test patterns
**Confidence:** HIGH

## Summary

Phase 29 is a pure wiring phase with zero algorithmic ambiguity. The services
(`HoldoutValidationService`, `BranchShareService`, `build_finalization_guidance`)
are already fully implemented and tested in isolation. The gap is exclusively at
`v3/entry/rd_agent.py:302-321` — the `MultiBranchService` constructor call does
not pass `holdout_validation_service` or `branch_share_service`, and
`build_finalization_guidance` is never called in any `v3/entry/` file.

The fix requires three coordinated changes: (1) instantiate `BranchShareService`
with its required `MemoryService` dependency before the `MultiBranchService`
constructor call, (2) instantiate `HoldoutValidationService` with its required
`dag_service`, `split_port`, and `evaluation_port` parameters and pass it to
`MultiBranchService`, and (3) after `run_exploration_round` returns, check
`explore_round.finalization_submission` and call `build_finalization_guidance` if
it is not `None`, embedding the guidance in the response payload.

The integration test for Phase 29 must exercise `rd_agent(...)` end-to-end with
stub ports and confirm that (a) `MultiBranchService` receives the services, (b)
auto-finalization triggers when `current_round >= max_rounds`, and (c) the
response payload contains `finalization_guidance`.

**Primary recommendation:** Wire in three surgical changes to `rd_agent.py` and
add one new integration test file `tests/test_phase29_entry_wiring.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| P28-HOLDOUT | K-fold holdout pipeline with HoldoutValidationService | Service implemented at `v3/orchestration/holdout_validation_service.py`; needs wiring into `rd_agent.py` MultiBranchService constructor |
| P28-ACTIVATE | Auto-activation when current_round >= max_rounds, plus explicit early-finalization entry | `MultiBranchService._try_finalize` already implements the logic; activation silently no-ops because `holdout_validation_service=None` in rd_agent.py |
| P28-SUBMIT | FinalSubmissionSnapshot creation and persistence | `HoldoutValidationService.finalize` creates and persists the snapshot; reachable once wired |
| P28-PRESENT | Operator finalization summary via OperatorGuidance | `build_finalization_guidance` in `operator_guidance.py` is defined and tested; never called in any entry file |
| P27-KERNEL | Interaction-kernel helpers for cross-branch sharing | `BranchShareService.compute_sharing_candidates` uses interaction kernel; service must be injected into MultiBranchService |
| P27-INJECT | Branch sharing injects global best + peer hypotheses | `BranchShareService.identify_global_best` + `compute_sharing_candidates`; silently no-ops without injection |
| GUIDE-05 | User receives concise current-state + reason + next-action | `build_finalization_guidance` generates the OperatorGuidance payload; needs to be included in the rd_agent response when finalization occurs |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test framework | Already installed; all phases use it |
| pydantic | (existing) | Data contracts | All V3 contracts use Pydantic BaseModel |
| Python stdlib | 3.12.12 | No new dependencies | Wiring only — no new packages needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `v3.ports.holdout_port.StubHoldoutSplitPort` | (existing) | Deterministic test stub | Phase 29 integration test |
| `v3.ports.holdout_port.StubEvaluationPort` | (existing) | Fixed-score test stub | Phase 29 integration test |

**Installation:**

No new packages required. All dependencies already exist in the project.

## Architecture Patterns

### How MultiBranchService dependency injection works

`MultiBranchService.__init__` accepts optional keyword-only arguments for all
advanced services:

```python
# v3/orchestration/multi_branch_service.py lines 49-76
class MultiBranchService:
    def __init__(
        self,
        *,
        state_store: StateStorePort,
        workspace_manager: BranchWorkspaceManager,
        branch_lifecycle_service: BranchLifecycleService,
        branch_board_service: BranchBoardService,
        selection_service: SelectionService,
        branch_merge_service: BranchMergeService,
        dispatcher: DispatchFn | None = None,
        dag_service: DAGService | None = None,
        prune_service: BranchPruneService | None = None,
        select_parents_service: SelectParentsService | None = None,
        branch_share_service: BranchShareService | None = None,         # <-- MISSING
        holdout_validation_service: HoldoutValidationService | None = None,  # <-- MISSING
    ) -> None:
```

Both parameters default to `None`. When `None`, the corresponding behavior is
silently skipped. Phase 29 must pass non-None instances.

### BranchShareService constructor

```python
# v3/orchestration/branch_share_service.py lines 43-55
class BranchShareService:
    def __init__(
        self,
        state_store: StateStorePort,
        memory_service: MemoryService,
        board_service: BranchBoardService | None = None,
        embedding_port: EmbeddingPort | None = None,
        dag_service: DAGService | None = None,
    ) -> None:
```

`MemoryService` is a required positional argument. `MemoryService` requires a
`MemoryStorePort` — use `ArtifactStateStore` which implements both
`StateStorePort` and `MemoryStorePort`. In `rd_agent.py`, the `state_store`
parameter is typed as `StateStorePort`; at runtime callers pass `ArtifactStateStore`.
Use `getattr(state_store, "_memory_store", None)` as a pattern, or construct
`MemoryService(state_store)` directly since `ArtifactStateStore` satisfies
`MemoryStorePort`.

Pattern used in tests:
```python
memory_service = MemoryService(state_store)
branch_share_service = BranchShareService(
    state_store,
    memory_service,
    board_service=board_service,
    dag_service=dag_service,
)
```

### HoldoutValidationService constructor

```python
# v3/orchestration/holdout_validation_service.py lines 17-27
class HoldoutValidationService:
    def __init__(
        self,
        *,
        state_store: StateStorePort,
        dag_service: DAGService,
        split_port: HoldoutSplitPort,
        evaluation_port: EvaluationPort,
    ) -> None:
```

`dag_service` is required (not Optional). In `rd_agent.py`, `dag_service` is
only constructed when `hypothesis_specs is not None`. The wiring must guard:
`HoldoutValidationService` should only be instantiated when `dag_service` is
not `None`.

For production, `split_port` defaults to `StratifiedKFoldSplitter()` and
`evaluation_port` defaults to a stub — the caller provides real ports. In the
entry layer, the function signature must accept these as optional parameters.

### Response payload pattern

The current multi-branch path returns:

```python
return {
    "structuredContent": {
        "run": run_snapshot.model_dump(mode="json"),
        "board": converge_round.board.model_dump(mode="json"),
        "mode": converge_round.board.mode.value,
        "recommended_next_step": converge_round.recommended_next_step,
        "selected_branch_id": converge_round.selected_branch_id,
        "dispatches": explore_round.dispatched_branch_ids,
        "merge_summary": converge_round.merge_summary,
    },
    "content": [...]
}
```

Phase 29 adds to `structuredContent`:
- `"finalization_guidance"`: `operator_guidance_to_dict(guidance)` when finalization occurred, else `None`
- `"finalization_submission"`: `explore_round.finalization_submission.model_dump(mode="json")` when not `None`, else `None`

### `build_finalization_guidance` call pattern

```python
# v3/orchestration/operator_guidance.py lines 99-130
def build_finalization_guidance(*, submission: FinalSubmissionSnapshot) -> OperatorGuidance:
    ...
```

The `ExploreRoundResult.finalization_submission` field is typed as
`FinalSubmissionSnapshot | None` (see `v3/contracts/tool_io.py:254`).

Call pattern:
```python
explore_round = multi_branch_service.run_exploration_round(...)
finalization_guidance = None
if explore_round.finalization_submission is not None:
    from v3.orchestration.operator_guidance import build_finalization_guidance
    fg = build_finalization_guidance(submission=explore_round.finalization_submission)
    finalization_guidance = operator_guidance_to_dict(fg)
```

### Recommended Project Structure

No structural changes. Only file modifications:
```
v3/entry/rd_agent.py      # 3 changes: imports, instantiation, response payload
tests/
└── test_phase29_entry_wiring.py   # new integration test
```

### Anti-Patterns to Avoid

- **Constructing HoldoutValidationService when dag_service is None**: `HoldoutValidationService.__init__` requires a `DAGService` — guard with `if dag_service is not None` before instantiation.
- **Adding new function parameters without defaults**: `rd_agent(...)` must remain backward-compatible. Use default parameter values (`split_port: HoldoutSplitPort | None = None`, etc.) or construct defaults inside the function body.
- **Mutating existing test files**: Phase 29 adds one new test file. Do not modify existing Phase 28 or Phase 16 tests.
- **Calling `build_finalization_guidance` unconditionally**: Only call when `explore_round.finalization_submission is not None`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Holdout splitting | Custom K-fold splitter | `StratifiedKFoldSplitter` from `v3/ports/holdout_port.py` | Already implemented, tested |
| Stub evaluation | Custom test port | `StubEvaluationPort` / `StubHoldoutSplitPort` from `v3/ports/holdout_port.py` | Already exists for tests |
| Guidance formatting | Custom string builder | `build_finalization_guidance` + `operator_guidance_to_dict` from `operator_guidance.py` | Fully implemented |
| Interaction kernel | Custom scoring math | `BranchShareService.compute_sharing_candidates` | Implemented with softmax + cosine decay |

**Key insight:** All the hard logic is already written. Phase 29 is a composition
exercise, not an algorithm exercise.

## Common Pitfalls

### Pitfall 1: MemoryService dependency for BranchShareService

**What goes wrong:** `BranchShareService` constructor requires a `MemoryService`
instance as the second positional argument. If omitted or if `state_store` is
passed directly without a `MemoryService` wrapper, it raises `TypeError`.

**Why it happens:** `MemoryService` wraps a `MemoryStorePort` and is not the
same object as `StateStorePort`, even though `ArtifactStateStore` implements
both interfaces.

**How to avoid:** Construct `MemoryService` before `BranchShareService`:
```python
from v3.orchestration.memory_service import MemoryService
memory_service = MemoryService(state_store)
branch_share_service = BranchShareService(
    state_store, memory_service, board_service=board_service, dag_service=dag_service
)
```

**Warning signs:** `TypeError: BranchShareService.__init__() missing required argument: 'memory_service'`

### Pitfall 2: dag_service None guard for HoldoutValidationService

**What goes wrong:** `dag_service` is `None` when `hypothesis_specs` is `None`
(non-structured branch mode). `HoldoutValidationService.__init__` does not
accept `None` for `dag_service` — it will fail at runtime when `list_nodes` is
called.

**Why it happens:** The `rd_agent.py` pattern already guards other services
with `if hypothesis_specs is not None`. `HoldoutValidationService` must follow
the same guard.

**How to avoid:**
```python
holdout_validation_service = (
    HoldoutValidationService(
        state_store=state_store,
        dag_service=dag_service,
        split_port=split_port or StratifiedKFoldSplitter(),
        evaluation_port=evaluation_port or StubEvaluationPort(),
    )
    if dag_service is not None
    else None
)
```

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'list_nodes'`

### Pitfall 3: Missing imports in rd_agent.py

**What goes wrong:** `BranchShareService`, `HoldoutValidationService`,
`MemoryService`, `build_finalization_guidance`, `StratifiedKFoldSplitter`, and
port types are not currently imported in `rd_agent.py`. The linter and tests
will fail if imports are missing.

**Why it happens:** Phase 28 added these files but rd_agent.py was never
updated to import them.

**How to avoid:** Add all necessary imports at the top of `rd_agent.py` in one
pass. Cross-reference `multi_branch_service.py:35-41` for the import pattern.

**Warning signs:** `ImportError`, `NameError: name 'BranchShareService' is not defined`

### Pitfall 4: ExploreRoundResult.finalization_submission vs ConvergeRoundResult

**What goes wrong:** `finalization_submission` is on `ExploreRoundResult` (from
`run_exploration_round`), not `ConvergeRoundResult` (from `run_convergence_round`).
Reading from the wrong result object yields `AttributeError`.

**Why it happens:** Auto-finalization triggers inside `_try_finalize` which is
called at the end of `run_exploration_round`. Convergence is a separate round.

**How to avoid:** Check `explore_round.finalization_submission`, not
`converge_round`.

### Pitfall 5: Response payload key collision

**What goes wrong:** Adding `"finalization_guidance"` to `structuredContent`
breaks existing tests that assert the exact keys in the response dict, if those
tests use `==` comparison on the full dict.

**Why it happens:** `test_phase16_rd_agent.py` asserts on `structuredContent`
keys. Adding new optional keys with `None` default values is safe as long as
existing assertions are key-presence checks, not full-dict equality.

**How to avoid:** Use `.get()` or `in` assertions in tests. Set
`finalization_guidance=None` and `finalization_submission=None` as defaults
so existing assertions do not fail.

## Code Examples

Verified patterns from existing codebase:

### Current rd_agent.py MultiBranchService construction (line 302-321)

```python
# Source: v3/entry/rd_agent.py:302-321 (CURRENT — missing wiring)
multi_branch_service = MultiBranchService(
    state_store=state_store,
    workspace_manager=workspace_manager,
    branch_lifecycle_service=BranchLifecycleService(...),
    branch_board_service=board_service,
    selection_service=SelectionService(state_store=state_store),
    branch_merge_service=BranchMergeService(...),
    dispatcher=dispatcher,
    dag_service=dag_service,
    prune_service=prune_service,
    select_parents_service=select_parents_service,
    # branch_share_service=None (missing)
    # holdout_validation_service=None (missing)
)
```

### How Phase 28 integration tests construct the full service graph (reference)

```python
# Source: tests/test_phase28_integration.py:130-158
holdout_service = HoldoutValidationService(
    state_store=state_store,
    dag_service=dag_service,
    split_port=StubHoldoutSplitPort(k=5),
    evaluation_port=_ScoreByBranchPort(branch_scores, state_store),
)
multi_branch_service = MultiBranchService(
    state_store=state_store,
    workspace_manager=workspace_manager,
    branch_lifecycle_service=BranchLifecycleService(...),
    branch_board_service=board_service,
    selection_service=SelectionService(state_store=state_store),
    branch_merge_service=merge_service,
    dispatcher=lambda payload: payload,
    dag_service=dag_service,
    select_parents_service=_LatestNodeParentSelector(dag_service),
    holdout_validation_service=holdout_service,
)
```

### build_finalization_guidance call and response embedding

```python
# Source: tests/test_phase28_integration.py:284-293
guidance = build_finalization_guidance(submission=submission)
rendered = render_operator_guidance_text(guidance)
assert "finalization complete" in guidance.current_state.lower()
assert submission.winner_node_id in guidance.current_state
```

### ExploreRoundResult.finalization_submission field

```python
# Source: v3/contracts/tool_io.py:254
finalization_submission: FinalSubmissionSnapshot | None = None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `validate_merge_holdout` proxy (simple score comparison) | `HoldoutValidationService` K-fold | Phase 28 | Phase 28 already replaced the proxy in merge.py |
| MultiBranchService with no holdout wiring | MultiBranchService with injected holdout service | Phase 29 (this phase) | Auto-finalization becomes reachable through public entry |
| No cross-branch sharing at public entry | BranchShareService injected | Phase 29 (this phase) | P27 sharing activates through rd_agent |

## Open Questions

1. **Default split_port and evaluation_port for production use**
   - What we know: Tests use `StubHoldoutSplitPort` and `StubEvaluationPort`. Production needs real implementations.
   - What's unclear: Whether `rd_agent(...)` should accept `split_port` and `evaluation_port` as parameters, or always use `StratifiedKFoldSplitter` + `StubEvaluationPort` as the default.
   - Recommendation: Add `holdout_split_port` and `holdout_evaluation_port` optional parameters to `rd_agent(...)` with defaults of `StratifiedKFoldSplitter()` and `StubEvaluationPort()`. This keeps the function signature backward-compatible while allowing callers to inject real ports.

2. **EmbeddingPort for BranchShareService**
   - What we know: `BranchShareService.__init__` accepts `embedding_port: EmbeddingPort | None = None`. When `None`, `compute_sharing_candidates` returns empty list (safe fallback).
   - What's unclear: Whether Phase 29 should also wire an `EmbeddingPort`.
   - Recommendation: Pass `embedding_port=None` at the entry layer. The interaction-kernel peer sampling requires an embedding port, but it already has a safe `return []` fallback when unavailable. Phase 29 does not need to add an embedding provider — that is a future enhancement.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml |
| Quick run command | `.venv/bin/pytest tests/test_phase29_entry_wiring.py -x -q` |
| Full suite command | `.venv/bin/pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| P28-HOLDOUT | HoldoutValidationService injected into MultiBranchService via rd_agent | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_multi_branch_service_receives_holdout_service -x` | ❌ Wave 0 |
| P28-ACTIVATE | Auto-finalization triggers when current_round >= max_rounds through rd_agent entry | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_auto_finalization_triggers_through_entry -x` | ❌ Wave 0 |
| P28-SUBMIT | FinalSubmissionSnapshot in response payload when finalization occurs | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_finalization_submission_in_response -x` | ❌ Wave 0 |
| P28-PRESENT | finalization_guidance in response payload with correct OperatorGuidance content | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_finalization_guidance_in_response -x` | ❌ Wave 0 |
| P27-KERNEL | BranchShareService injected and sharing candidates computed | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_branch_share_service_injected -x` | ❌ Wave 0 |
| P27-INJECT | Global best injection activates through public entry | integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_global_best_injection_through_entry -x` | ❌ Wave 0 |
| GUIDE-05 | Full E2E flow: rd_agent → exploration → holdout finalization → winner | e2e integration | `.venv/bin/pytest tests/test_phase29_entry_wiring.py::test_e2e_rd_agent_to_winner -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_phase29_entry_wiring.py -x -q`
- **Per wave merge:** `.venv/bin/pytest tests/test_phase28_integration.py tests/test_phase29_entry_wiring.py tests/test_phase16_rd_agent.py -x -q`
- **Phase gate:** `.venv/bin/pytest tests/ -x -q` before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase29_entry_wiring.py` — covers all 7 requirements; no conftest changes needed (existing ArtifactStateStore + StubHoldoutSplitPort + StubEvaluationPort are sufficient)

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `v3/entry/rd_agent.py` — confirmed missing wiring at lines 302-321
- Direct code inspection: `v3/orchestration/multi_branch_service.py` — confirmed parameter signatures and `_try_finalize` logic
- Direct code inspection: `v3/orchestration/operator_guidance.py` — confirmed `build_finalization_guidance` exists but is not imported in `rd_agent.py`
- Direct code inspection: `v3/orchestration/holdout_validation_service.py` — confirmed constructor requires `dag_service`
- Direct code inspection: `v3/orchestration/branch_share_service.py` — confirmed `MemoryService` is required
- Direct code inspection: `v3/contracts/tool_io.py:254` — confirmed `ExploreRoundResult.finalization_submission` field
- Direct test inspection: `tests/test_phase28_integration.py` — confirmed service construction pattern and working finalization lifecycle

### Secondary (MEDIUM confidence)
- `.planning/v1.3-MILESTONE-AUDIT.md` — Audit findings confirm exact file + line numbers for missing wiring

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all services exist and are tested
- Architecture: HIGH — code directly inspected; exact lines identified; no ambiguity
- Pitfalls: HIGH — derived from direct code inspection of constructor signatures

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain; only internal code changes would invalidate)
