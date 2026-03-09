# FC-1/4/5/6 Implementation: Integration Wiring & Enforcement

## TL;DR

> **Quick Summary**: Wire the already-built FC-1/4/5/6 submodules (InteractionKernel, StratifiedSplitter, HypothesisSelector, Planner budget, CoSTEER debug mode) into the main execution pipeline. The code exists — the work is "last mile" integration: making producers feed consumers, making configs actually take effect, and making all 3 scenario ProposalEngines consume context+plan instead of discarding them.
>
> **Deliverables**:
> - FC-1: Planner generates step-level time budgets; StepExecutor applies them as soft defaults
> - FC-4: MemoryService uses InteractionKernel for ranking; ProposalEngines consume context+plan
> - FC-5: Runners respect debug_mode config; Coders consume CoSTEER feedback; timing extrapolation
> - FC-6: StratifiedSplitter auto-called in build_context; leaderboard populated; ValidationSelector in loop
> - README FC table: all 6 components marked "Implemented"
> - Targeted behavioral tests for all 4 FCs
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 5 waves
> **Critical Path**: T1 → T4/T5/T6 → T10/T13 → T14 → T16/T17

---

## Context

### Original Request
User requested completion of FC-1, FC-4, FC-5, FC-6 — the four remaining "Partial" framework components in the README. These must become "Implemented" to match the R&D-Agent paper's full specification.

### Interview Summary
**Key Discussions**:
- All submodule code already exists (InteractionKernel, StratifiedSplitter, etc.) — work is integration wiring
- ProposalEngines in ALL 3 scenarios discard context, plan, and parent_ids — this is THE blocker
- Plan budget = soft hint in seconds; explicit user step_overrides always win
- Debug mode opt-in per scenario via `supports_debug_sampling` flag
- No new vector databases — use existing TF-IDF/InteractionKernel
- Protocol signatures in `plugins/contracts.py` must NOT change

**Research Findings**:
- `data_science/plugin.py:108-110` discards context/plan with `_ = context; _ = parent_ids; _ = plan`
- `quant/plugin.py:107-109` same pattern
- `synthetic_research/plugin.py` same pattern
- `engine.py:106` passes `history_summary={}` — planner has no history
- ContextPack at `data_models.py:430` lacks metadata fields (branch_id, source, timestamp)
- InteractionKernel at `memory_service/interaction_kernel.py` is COMPLETE but unused
- StratifiedSplitter at `evaluation_service/stratified_splitter.py` is COMPLETE but uncalled

### Metis Review
**Identified Gaps** (all addressed in this plan):
1. All 3 ProposalEngines discard context+plan → T6 fixes all 3
2. ContextPack lacks branch/source metadata → T1 extends it
3. LoopEngine feeds empty history_summary → T13 wires it
4. Existing tests are permissive (assert "returns dict") → T14 adds behavioral assertions
5. Budget semantics unclear → Resolved: soft hint in seconds, step_overrides win
6. Task intake for FC-6 undefined → Resolved: build_context() calls StratifiedSplitter

---

## Work Objectives

### Core Objective
Wire all existing FC-1/4/5/6 submodules into the main execution pipeline so that data flows from producers to consumers and configurations actually take effect at runtime.

### Concrete Deliverables
- Extended ContextPack with optional metadata (backward compatible)
- PlanningStrategy with budget_allocation field
- All 3 ProposalEngines consuming context, plan, parent_ids
- MemoryService.query_context() using InteractionKernel for ranking
- StepExecutor applying plan budget as soft timeout default
- Runners respecting debug_mode config
- CoSTEER timing extrapolation from debug runs
- StratifiedSplitter auto-called in scenario build_context()
- Leaderboard populated on evaluate_run()
- ValidationSelector integrated in LoopEngine
- LoopEngine feeding real history_summary to planner
- Behavioral tests for all 4 FCs
- README and paper_gap_analysis.md updated

### Definition of Done
- [ ] All 739+ tests pass (`python3 -m pytest tests -q`)
- [ ] README FC table shows all 6 as "Implemented"
- [ ] E2E test scripts still pass (all 3 scenarios)
- [ ] New targeted FC tests pass with behavioral assertions

### Must Have
- InteractionKernel actually scoring and ranking in query_context()
- ProposalEngines using context highlights and plan guidance in LLM prompts
- StratifiedSplitter called automatically (not manually)
- Plan budget applied as soft default in StepExecutor
- debug_mode respected by Runners when flag is True
- Backward compatibility — existing configs/runs must not break

### Must NOT Have (Guardrails)
- NO changes to 6 Protocol signatures in `plugins/contracts.py`
- NO new vector databases or embedding services
- NO async/multi-worker architecture
- NO FC-2/FC-3/MCTS refactoring
- NO runtime mock fallbacks
- Plan budget MUST NOT override explicit user step_overrides
- Debug mode MUST NOT change behavior when debug_mode=False
- NO NetworkX, no asyncio
- NO excessive comments, over-abstraction, or AI slop

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, 739 tests)
- **Automated tests**: YES (Tests-after) — add targeted behavioral tests after implementation
- **Framework**: pytest

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Library/Module**: Use Bash (python3 REPL) — Import, call functions, compare output
- **Integration**: Use Bash (pytest) — Run specific test files, verify pass/fail
- **E2E**: Use Bash (scripts) — Run e2e scripts, verify full loop completion

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — schemas, contracts, data models):
├── Task 1: Extend data models + schemas [quick]
├── Task 2: Define FC contract table + document producer→consumer→fallback [quick]
└── Task 3: Extend Runner protocol with debug_config support [quick]

Wave 2 (Core FC implementations — MAX PARALLEL):
├── Task 4: FC-1 Planner generates step-level time budgets [unspecified-high]
├── Task 5: FC-4 MemoryService.query_context() uses InteractionKernel [unspecified-high]
├── Task 6: FC-4 All 3 ProposalEngines consume context+plan [deep]
├── Task 7: FC-5 Runners respect debug_mode config [quick]
└── Task 8: FC-5 Coder consumes _costeer_feedback in prompt [quick]

Wave 3 (Pipeline integration):
├── Task 9: FC-6 StratifiedSplitter auto-call + leaderboard [unspecified-high]
├── Task 10: FC-1 StepExecutor applies plan budget as soft timeout [unspecified-high]
├── Task 11: FC-5 CoSTEER timing extrapolation from debug runs [unspecified-high]
└── Task 12: FC-6 ValidationSelector in LoopEngine [unspecified-high]

Wave 4 (Cross-FC wiring + tests):
├── Task 13: Cross-FC integration wiring + LoopEngine history_summary [deep]
├── Task 14: Targeted regression tests for all 4 FCs [unspecified-high]
└── Task 15: Edge case handling [quick]

Wave 5 (Documentation + final):
├── Task 16: Update README FC table + paper_gap_analysis.md [writing]
└── Task 17: Final full test suite run + commit and push [quick]

Wave FINAL (Independent review — 4 parallel):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real QA — run targeted tests (unspecified-high)
└── F4: Scope fidelity check (deep)

Critical Path: T1 → T4/T5/T6 → T10/T13 → T14 → T16 → T17 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| T1 | — | T4, T5, T6, T9, T13 |
| T2 | — | T6 (reference) |
| T3 | — | T7 |
| T4 | T1 | T10, T13 |
| T5 | T1 | T13 |
| T6 | T1, T2 | T13, T14 |
| T7 | T3 | T11, T14 |
| T8 | — | T11, T14 |
| T9 | T1 | T12, T14 |
| T10 | T4 | T13, T14 |
| T11 | T7, T8 | T14 |
| T12 | T9 | T14 |
| T13 | T4, T5, T6, T10 | T14 |
| T14 | T6, T7, T9, T10, T11, T12, T13 | T16 |
| T15 | T13 | T14 |
| T16 | T14 | T17 |
| T17 | T16 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `quick`, T2 `quick`, T3 `quick`
- **Wave 2**: 5 tasks — T4 `unspecified-high`, T5 `unspecified-high`, T6 `deep`, T7 `quick`, T8 `quick`
- **Wave 3**: 4 tasks — T9-T12 all `unspecified-high`
- **Wave 4**: 3 tasks — T13 `deep`, T14 `unspecified-high`, T15 `quick`
- **Wave 5**: 2 tasks — T16 `writing`, T17 `quick`
- **FINAL**: 4 tasks — F1 `oracle`, F2 `unspecified-high`, F3 `unspecified-high`, F4 `deep`

---

## TODOs

### Wave 1 — Foundation (schemas, contracts, data models)

- [ ] 1. Extend data models + schemas for FC-1/4/5/6

  **What to do**:
  - Extend `ContextPack` in `data_models.py:430` with optional metadata fields:
    - `branch_id: Optional[str] = None` — source branch for cross-branch context
    - `source_type: Optional[str] = None` — "memory" | "cross_branch" | "plan"
    - `timestamp: Optional[float] = None` — when context was generated
    - All fields optional with defaults → backward compatible
  - Add `budget_allocation: Optional[Dict[str, float]] = None` field to `PlanningStrategy` in `llm/schemas.py`
    - Keys are step names ("proposal", "coding", "running", "feedback"), values are seconds
    - The LLM prompt in `llm/prompts.py` `planning_strategy_prompt()` must include budget_allocation in the JSON output spec
  - Add `DebugConfig` dataclass to `data_models.py`:
    ```python
    @dataclass
    class DebugConfig:
        debug_mode: bool = False
        sample_fraction: float = 0.1
        max_epochs: int = 2
        supports_debug_sampling: bool = True  # per-scenario opt-in
    ```
  - Verify existing tests still pass after schema changes

  **Must NOT do**:
  - Do NOT change Protocol signatures in `plugins/contracts.py`
  - Do NOT remove any existing fields from ContextPack or PlanningStrategy

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small schema extensions to existing dataclasses, no complex logic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No UI involved

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: T4, T5, T6, T9, T13
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `data_models.py:430-435` — Current ContextPack with items, highlights, scored_items (extend this)
  - `data_models.py:421-428` — PlanningContext dataclass (follow same pattern for DebugConfig)

  **API/Type References**:
  - `llm/schemas.py` — PlanningStrategy dataclass (add budget_allocation field here)
  - `llm/prompts.py` — planning_strategy_prompt() function (update JSON output spec to include budget_allocation)

  **External References**:
  - None needed — pure Python dataclass extensions

  **WHY Each Reference Matters**:
  - `data_models.py:430` — This is THE file where ContextPack lives. You must read it to understand existing fields before extending.
  - `llm/schemas.py` — PlanningStrategy is parsed from LLM JSON output. The budget_allocation field must match what the prompt asks for.
  - `llm/prompts.py` — The prompt text must be updated to tell the LLM to include budget_allocation in its response.

  **Acceptance Criteria**:
  - [ ] `python3 -c "from data_models import ContextPack, DebugConfig; c = ContextPack(); d = DebugConfig(); print('OK')"` → prints "OK"
  - [ ] `python3 -c "from llm.schemas import PlanningStrategy"` → no import error
  - [ ] `python3 -m pytest tests/ -q -x` → all 739+ tests pass (backward compat verified)

  **QA Scenarios**:

  ```
  Scenario: ContextPack backward compatibility
    Tool: Bash (python3)
    Preconditions: Current codebase with schema changes applied
    Steps:
      1. python3 -c "from data_models import ContextPack; c = ContextPack(); assert c.items == []; assert c.branch_id is None; print('PASS')"
      2. python3 -c "from data_models import ContextPack; c = ContextPack(branch_id='b1', source_type='memory'); assert c.branch_id == 'b1'; print('PASS')"
    Expected Result: Both print "PASS" — old code works unchanged, new fields are usable
    Failure Indicators: ImportError or AttributeError on new fields
    Evidence: .sisyphus/evidence/task-1-contextpack-compat.txt

  Scenario: DebugConfig defaults
    Tool: Bash (python3)
    Preconditions: DebugConfig added to data_models.py
    Steps:
      1. python3 -c "from data_models import DebugConfig; d = DebugConfig(); assert d.debug_mode == False; assert d.sample_fraction == 0.1; print('PASS')"
    Expected Result: Print "PASS" — defaults are safe (debug off by default)
    Failure Indicators: AssertionError on default values
    Evidence: .sisyphus/evidence/task-1-debugconfig-defaults.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(models): extend ContextPack, PlanningStrategy, and DebugConfig for FC-1/4/5/6`
  - Files: `data_models.py`, `llm/schemas.py`, `llm/prompts.py`
  - Pre-commit: `python3 -m pytest tests/ -q -x`

- [ ] 2. Define FC contract table (producer → consumer → fallback)

  **What to do**:
  - Create a markdown reference table in `dev_doc/fc_contract_table.md` documenting:
    - For each FC (1, 4, 5, 6): what module PRODUCES the data, what module CONSUMES it, what the FALLBACK is when producer returns empty/None
    - Example row: `FC-4 | MemoryService.query_context() | ProposalEngine.propose(context=) | ContextPack() with empty items`
  - This is a REFERENCE DOCUMENT for T6 and T13 — ensures all wiring is correct
  - Include the exact function signatures and parameter names

  **Must NOT do**:
  - Do NOT write any code in this task — documentation only
  - Do NOT modify any source files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure documentation task, no code changes
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: T6 (reference)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `plugins/contracts.py` — All 6 Protocol definitions (ProposalEngine, Coder, Runner, FeedbackAnalyzer, ScenarioPlugin, CommonUsefulnessGate)
  - `core/loop/engine.py:90-130` — LoopEngine.run() orchestration showing data flow between steps
  - `core/loop/step_executor.py:80-120` — StepExecutor showing how it calls each step

  **API/Type References**:
  - `memory_service/service.py:119-157` — query_context() signature and return type
  - `planner/service.py:50-80` — generate_plan() and generate_strategy() signatures
  - `evaluation_service/service.py:40-80` — evaluate_run() signature

  **WHY Each Reference Matters**:
  - `contracts.py` — The AUTHORITATIVE source for what each plugin step accepts and returns
  - `engine.py` — Shows the ACTUAL call order and what gets passed between steps
  - Each service file — Shows the ACTUAL producer function signatures

  **Acceptance Criteria**:
  - [ ] File `dev_doc/fc_contract_table.md` exists with complete table for FC-1, FC-4, FC-5, FC-6
  - [ ] Each row has: FC | Producer | Consumer | Fallback | Data Type

  **QA Scenarios**:

  ```
  Scenario: Contract table completeness
    Tool: Bash (grep)
    Preconditions: fc_contract_table.md written
    Steps:
      1. grep -c "FC-1" dev_doc/fc_contract_table.md  → at least 2 rows
      2. grep -c "FC-4" dev_doc/fc_contract_table.md  → at least 2 rows
      3. grep -c "FC-5" dev_doc/fc_contract_table.md  → at least 2 rows
      4. grep -c "FC-6" dev_doc/fc_contract_table.md  → at least 2 rows
    Expected Result: Each FC has at least 2 producer→consumer mappings documented
    Failure Indicators: Missing FC section or zero rows
    Evidence: .sisyphus/evidence/task-2-contract-table.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `docs(fc): add FC contract table documenting producer→consumer→fallback for FC-1/4/5/6`
  - Files: `dev_doc/fc_contract_table.md`

- [ ] 3. Extend Runner with debug_config support

  **What to do**:
  - In each scenario's Runner implementation, add awareness of `DebugConfig`:
    - `scenarios/data_science/plugin.py` — DataScienceRunner
    - `scenarios/quant/plugin.py` — QuantRunner
    - `scenarios/synthetic_research/plugin.py` — SyntheticResearchRunner
  - Each Runner's `run()` method should accept debug config via the `scenario: ScenarioContext` parameter (which already has a config dict)
  - Add `debug_config` to `ScenarioContext.config` dict in `app/runtime.py` `build_runtime()` where ScenarioContext is constructed
  - When `debug_mode=True` and `supports_debug_sampling=True`:
    - data_science Runner: reduce dataset to `sample_fraction` (e.g., 10% of rows)
    - quant Runner: reduce date range or sample stocks
    - synthetic_research Runner: no-op (flag `supports_debug_sampling=False`)
  - When `debug_mode=False`: ZERO behavior change — must be completely transparent

  **Must NOT do**:
  - Do NOT change the `Runner` Protocol signature in `plugins/contracts.py`
  - Do NOT add parameters to `run()` — use `scenario.config["debug_config"]`
  - Do NOT change behavior when `debug_mode=False`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small conditional logic additions to existing Runner classes
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: T7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py` — DataScienceRunner.run() (find the method, see how it accesses scenario.config)
  - `scenarios/quant/plugin.py` — QuantRunner.run()
  - `scenarios/synthetic_research/plugin.py` — SyntheticResearchRunner.run()
  - `app/runtime.py:200-250` — build_runtime() where ScenarioContext is assembled

  **API/Type References**:
  - `plugins/contracts.py` — Runner Protocol (DO NOT change, just read for reference)
  - `app/config.py` — debug_mode, debug_sample_fraction, debug_max_epochs config flags (already exist)

  **WHY Each Reference Matters**:
  - Runner implementations — You need to see HOW each Runner currently works to add debug logic without breaking it
  - `runtime.py` — This is WHERE ScenarioContext.config is populated, so debug_config must be injected here
  - `config.py` — The debug flags already exist here, they just need to be read and passed through

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass (debug_mode=False path unchanged)
  - [ ] ScenarioContext.config contains "debug_config" key after build_runtime()

  **QA Scenarios**:

  ```
  Scenario: Debug mode OFF — zero behavior change
    Tool: Bash (python3)
    Preconditions: Runner code updated, debug_mode=False (default)
    Steps:
      1. Run existing test suite: python3 -m pytest tests/ -q -x
      2. All tests must pass with zero changes in behavior
    Expected Result: 739+ tests pass, identical to before
    Failure Indicators: Any test failure that wasn't failing before
    Evidence: .sisyphus/evidence/task-3-debug-off-tests.txt

  Scenario: Debug config propagation
    Tool: Bash (python3)
    Preconditions: build_runtime() updated to include debug_config
    Steps:
      1. python3 -c "from data_models import DebugConfig; d = DebugConfig(debug_mode=True); assert d.debug_mode == True; print('PASS')"
    Expected Result: DebugConfig can be created with debug_mode=True
    Evidence: .sisyphus/evidence/task-3-debug-config-propagation.txt
  ```

  **Commit**: YES (groups with Wave 1)
  - Message: `feat(models): extend ContextPack, PlanningStrategy, and Runner protocol for FC-1/4/5/6`
  - Files: `scenarios/*/plugin.py`, `app/runtime.py`
  - Pre-commit: `python3 -m pytest tests/ -q -x`

### Wave 2 — Core FC Implementations (MAX PARALLEL)

- [ ] 4. FC-1 Planner generates step-level time budgets

  **What to do**:
  - In `planner/service.py`, modify `_build_budget_allocation()` to return step-level seconds instead of exploration/exploitation ratios
  - The planner should use `generate_strategy()` to produce a `PlanningStrategy` that includes `budget_allocation` (Dict[str, float] mapping step names to seconds)
  - Update `llm/prompts.py` `planning_strategy_prompt()` to instruct the LLM to output budget_allocation in its JSON response
  - The LLM should allocate time based on: total_budget (from run config), number of steps, complexity hints from task_summary
  - Default total budget: use `run_session.config.get("total_budget_sec", 600)` — 10 minutes default
  - If LLM returns no budget or invalid budget, fall back to equal distribution across 4 steps
  - In `engine.py`, change line 106 from `history_summary={}` to pass actual history from previous iterations (this connects to T13, but the planner side should be ready to receive it)

  **Must NOT do**:
  - Do NOT make budget allocation mandatory — it's an optional enhancement
  - Do NOT break existing planner tests
  - Plan budget MUST NOT override explicit user step_overrides (this is enforced in T10)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding LLM prompt engineering + planner service internals
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7, 8)
  - **Blocks**: T10, T13
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `planner/service.py:90-130` — _build_budget_allocation() current implementation (returns ratios, needs to return seconds)
  - `planner/service.py:50-80` — generate_strategy() (calls LLM, parses PlanningStrategy)

  **API/Type References**:
  - `llm/schemas.py` — PlanningStrategy (now has budget_allocation field from T1)
  - `llm/prompts.py` — planning_strategy_prompt() (update output spec)

  **Test References**:
  - `tests/test_fc1_planning.py` — Existing planner tests (must still pass)

  **WHY Each Reference Matters**:
  - `planner/service.py` — THE file being modified. Must understand current _build_budget_allocation() to change it correctly.
  - `llm/schemas.py` — The PlanningStrategy dataclass defines what fields the LLM JSON is parsed into.
  - `llm/prompts.py` — The prompt text determines what the LLM actually outputs.

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/test_fc1_planning.py -q` → PASS
  - [ ] `python3 -c "from planner.service import Planner"` → no import error
  - [ ] PlanningStrategy.budget_allocation is populated after generate_strategy() call

  **QA Scenarios**:

  ```
  Scenario: Planner produces budget allocation
    Tool: Bash (python3)
    Preconditions: Planner service updated, LLM schemas extended
    Steps:
      1. python3 -c "from llm.schemas import PlanningStrategy; ps = PlanningStrategy.__new__(PlanningStrategy); ps.budget_allocation = {'proposal': 120, 'coding': 180}; assert ps.budget_allocation['proposal'] == 120; print('PASS')"
    Expected Result: PlanningStrategy accepts and stores budget_allocation
    Evidence: .sisyphus/evidence/task-4-budget-allocation.txt

  Scenario: Planner fallback on empty budget
    Tool: Bash (python3)
    Preconditions: Planner handles None budget gracefully
    Steps:
      1. python3 -c "from llm.schemas import PlanningStrategy; ps = PlanningStrategy.__new__(PlanningStrategy); ps.budget_allocation = None; assert ps.budget_allocation is None; print('PASS')"
    Expected Result: None budget is acceptable (falls back to equal distribution)
    Evidence: .sisyphus/evidence/task-4-budget-fallback.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Message: `feat(fc-1456): wire InteractionKernel, plan budget, debug mode, and StratifiedSplitter into pipeline`
  - Files: `planner/service.py`, `llm/prompts.py`
  - Pre-commit: `python3 -m pytest tests/test_fc1_planning.py -q`

- [ ] 5. FC-4 MemoryService.query_context() uses InteractionKernel for ranking

  **What to do**:
  - In `memory_service/service.py`, modify `query_context()` (lines 119-157) to:
    1. After SQL LIKE filtering retrieves candidate hypotheses, pass them through InteractionKernel for scoring
    2. Import and instantiate InteractionKernel from `memory_service/interaction_kernel.py`
    3. Call `kernel.compute_scores(candidates, query_hypothesis)` to get relevance scores
    4. Sort candidates by kernel score descending
    5. Populate ContextPack.scored_items with (hypothesis_text, kernel_score) tuples
    6. Populate ContextPack.highlights with top-K hypothesis summaries
  - Also wire `HypothesisSelector.adaptive_select()` from `memory_service/hypothesis_selector.py`:
    1. After kernel ranking, call `adaptive_select(scored_candidates, budget)` to pick the best subset
    2. This respects the exploration/exploitation balance from the planner
  - Handle the cross-branch case: call `get_cross_branch_hypotheses()` (already exists in service.py) and merge those into the candidate pool before kernel scoring
  - Set ContextPack.source_type = "memory" for within-branch, "cross_branch" for cross-branch items

  **Must NOT do**:
  - Do NOT add new vector databases or embedding services — use existing TF-IDF in InteractionKernel
  - Do NOT change MemoryService.__init__() signature
  - Do NOT make InteractionKernel mandatory — if it fails, fall back to unranked results

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration logic requiring understanding of InteractionKernel API + SQL query results
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7, 8)
  - **Blocks**: T13
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `memory_service/service.py:119-157` — Current query_context() implementation (SQL LIKE only, no ranking)
  - `memory_service/service.py:160-190` — get_cross_branch_hypotheses() (already exists, needs to be called)

  **API/Type References**:
  - `memory_service/interaction_kernel.py:1-155` — COMPLETE InteractionKernel with compute_scores(), formula: U_ij = α·S_ij·e^{-γL} + β·tanh(Δ_ij)
  - `memory_service/hypothesis_selector.py:76-111` — adaptive_select() method signature and return type
  - `data_models.py:430-435` — ContextPack (now extended with metadata from T1)

  **Test References**:
  - `tests/test_fc4_interaction_kernel.py` — InteractionKernel unit tests (reference for how to call it)
  - `tests/test_fc4_hypothesis_selector.py` — HypothesisSelector unit tests
  - `tests/test_memory_service.py` — MemoryService integration tests

  **WHY Each Reference Matters**:
  - `service.py:119` — THE function being modified. You must understand current flow (SQL → return) to insert kernel scoring.
  - `interaction_kernel.py` — The kernel is COMPLETE code. Read it to understand its API (what it takes, what it returns).
  - `hypothesis_selector.py` — adaptive_select() determines WHICH scored items to include. Understand its budget parameter.

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/test_memory_service.py -q` → PASS
  - [ ] `python3 -m pytest tests/test_fc4_interaction_kernel.py -q` → PASS
  - [ ] query_context() returns ContextPack with scored_items when hypotheses exist

  **QA Scenarios**:

  ```
  Scenario: query_context returns scored items
    Tool: Bash (pytest)
    Preconditions: MemoryService wired with InteractionKernel
    Steps:
      1. python3 -m pytest tests/test_memory_service.py -q -x
      2. Verify scored_items in ContextPack is non-empty when hypotheses exist
    Expected Result: Tests pass, scored_items populated
    Evidence: .sisyphus/evidence/task-5-memory-scored.txt

  Scenario: query_context fallback on kernel failure
    Tool: Bash (python3)
    Preconditions: InteractionKernel might fail (e.g., empty corpus)
    Steps:
      1. Create MemoryService with empty history, call query_context()
      2. Verify it returns empty ContextPack without crashing
    Expected Result: Returns ContextPack(items=[], highlights=[], scored_items=[])
    Evidence: .sisyphus/evidence/task-5-kernel-fallback.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `memory_service/service.py`
  - Pre-commit: `python3 -m pytest tests/test_memory_service.py tests/test_fc4_interaction_kernel.py -q`

- [ ] 6. FC-4 All 3 ProposalEngines consume context + plan

  **What to do**:
  - This is the MOST CRITICAL task. All 3 scenario ProposalEngines currently DISCARD context, plan, and parent_ids.
  - **data_science/plugin.py** (DataScienceProposalEngine.propose, line ~108):
    - Remove `_ = context; _ = parent_ids; _ = plan`
    - Extract context.highlights and context.scored_items
    - Inject them into the LLM prompt as "relevant prior findings" section
    - Use plan.guidance (if plan is not None) as strategic direction in the prompt
    - Use parent_ids to reference parent branch hypotheses for continuity
  - **quant/plugin.py** (QuantProposalEngine.propose, line ~107):
    - Same pattern as data_science but for factor mining domain
    - Context highlights become "previously tested factors and their outcomes"
    - Plan guidance becomes "factor exploration strategy"
  - **synthetic_research/plugin.py** (SyntheticResearchProposalEngine.propose):
    - Same pattern but for research brief domain
    - Context becomes "prior research findings"
  - For ALL 3: the LLM prompt should include a section like:
    ```
    ## Prior Context (from memory)
    {formatted context.highlights}
    
    ## Strategic Guidance (from planner)  
    {plan.guidance if plan else "No specific guidance"}
    ```
  - Use the FC contract table from T2 as reference for what data flows where

  **Must NOT do**:
  - Do NOT change the `ProposalEngine` Protocol signature in `plugins/contracts.py`
  - Do NOT change the method signature of `propose()` — just USE the parameters that are already passed
  - Do NOT make context/plan mandatory — handle None gracefully (empty context = no prior findings section)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Must modify 3 files consistently, requires understanding LLM prompt construction in each scenario
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7, 8)
  - **Blocks**: T13, T14
  - **Blocked By**: T1, T2

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:100-150` — DataScienceProposalEngine.propose() (the lines that discard context)
  - `scenarios/quant/plugin.py:100-150` — QuantProposalEngine.propose() (same pattern)
  - `scenarios/synthetic_research/plugin.py` — SyntheticResearchProposalEngine.propose() (same pattern)

  **API/Type References**:
  - `data_models.py:430-435` — ContextPack (items, highlights, scored_items, + new metadata)
  - `data_models.py` — Plan dataclass (has .guidance field)
  - `plugins/contracts.py` — ProposalEngine Protocol (read-only, DO NOT modify)

  **Test References**:
  - `tests/` — Search for existing ProposalEngine tests to verify nothing breaks

  **External References**:
  - `dev_doc/fc_contract_table.md` (from T2) — Reference for what data should flow into propose()

  **WHY Each Reference Matters**:
  - Each scenario's plugin.py — THE files being modified. The `_ = context` lines must be replaced with actual usage.
  - `data_models.py` — Defines ContextPack and Plan structure. You need to know what fields to extract.
  - `contracts.py` — Read-only reference to verify you're not accidentally changing the Protocol.

  **Acceptance Criteria**:
  - [ ] `grep -r "_ = context" scenarios/` → returns NO matches (all discards removed)
  - [ ] `grep -r "_ = plan" scenarios/` → returns NO matches
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] Each ProposalEngine.propose() uses context.highlights in its LLM prompt

  **QA Scenarios**:

  ```
  Scenario: ProposalEngines no longer discard context
    Tool: Bash (grep)
    Preconditions: All 3 ProposalEngines updated
    Steps:
      1. grep -rn "_ = context" scenarios/ — should return empty
      2. grep -rn "_ = plan" scenarios/ — should return empty  
      3. grep -rn "_ = parent_ids" scenarios/ — should return empty
    Expected Result: Zero matches — no more discarded parameters
    Failure Indicators: Any grep match means a ProposalEngine still discards data
    Evidence: .sisyphus/evidence/task-6-no-discards.txt

  Scenario: Context injected into LLM prompt
    Tool: Bash (python3)
    Preconditions: DataScienceProposalEngine updated
    Steps:
      1. Read data_science/plugin.py and verify context.highlights appears in prompt construction
      2. Verify plan.guidance is referenced in prompt (with None guard)
    Expected Result: LLM prompt includes prior context and strategic guidance sections
    Evidence: .sisyphus/evidence/task-6-prompt-injection.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `scenarios/data_science/plugin.py`, `scenarios/quant/plugin.py`, `scenarios/synthetic_research/plugin.py`
  - Pre-commit: `python3 -m pytest tests/ -q -x`

- [ ] 7. FC-5 Runners respect debug_mode config

  **What to do**:
  - In each scenario's Runner.run() method, read `scenario.config.get("debug_config")` (injected by T3)
  - When DebugConfig.debug_mode is True AND supports_debug_sampling is True:
    - **data_science Runner**: Subsample input data to `sample_fraction` of rows before execution
    - **quant Runner**: Reduce the date range or number of symbols used for backtest
    - **synthetic_research Runner**: No-op (supports_debug_sampling=False for this scenario)
  - When debug_mode is False: ZERO changes to current behavior
  - Also add `max_epochs` enforcement: if Runner controls iteration count (like training epochs), cap at DebugConfig.max_epochs in debug mode
  - Log a message when debug mode activates: `logger.info("Debug mode: sampling %d%% of data", sample_fraction * 100)`

  **Must NOT do**:
  - Do NOT change Runner Protocol in contracts.py
  - Do NOT change any behavior when debug_mode=False
  - Do NOT apply debug sampling to synthetic_research scenario

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple conditional logic in existing Runner methods
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 8)
  - **Blocks**: T11, T14
  - **Blocked By**: T3

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py` — DataScienceRunner.run() (find current data loading logic to add sampling)
  - `scenarios/quant/plugin.py` — QuantRunner.run() (find backtest data loading)

  **API/Type References**:
  - `data_models.py` — DebugConfig dataclass (from T1)
  - `app/config.py` — debug_mode, debug_sample_fraction, debug_max_epochs flags

  **WHY Each Reference Matters**:
  - Runner implementations — Need to find WHERE data is loaded to insert sampling before it
  - DebugConfig — Need to know exact field names and defaults

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass (debug_mode=False unchanged)
  - [ ] grep for "debug_mode" in Runner files shows conditional logic

  **QA Scenarios**:

  ```
  Scenario: Debug mode OFF — no behavior change
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q -x
    Expected Result: All 739+ tests pass unchanged
    Evidence: .sisyphus/evidence/task-7-debug-off.txt

  Scenario: Debug mode ON — data sampling active
    Tool: Bash (python3)
    Steps:
      1. Verify DataScienceRunner.run() has conditional sampling logic
      2. grep -n "debug_mode" scenarios/data_science/plugin.py → at least 1 match
      3. grep -n "sample_fraction" scenarios/data_science/plugin.py → at least 1 match
    Expected Result: Debug sampling code present in data_science and quant Runners
    Evidence: .sisyphus/evidence/task-7-debug-on.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `scenarios/data_science/plugin.py`, `scenarios/quant/plugin.py`, `scenarios/synthetic_research/plugin.py`

- [ ] 8. FC-5 Coder consumes _costeer_feedback in prompt

  **What to do**:
  - In each scenario's Coder implementation, check for CoSTEER feedback in the hypothesis/experiment:
    - The CoSTEER evolver (in `core/loop/costeer.py`) already injects `_costeer_feedback` into experiment.hypothesis after each round
    - BUT scenario Coders don't read this field
  - **data_science/plugin.py** — DataScienceCoder.generate_code():
    - Check `experiment.hypothesis` for `_costeer_feedback` attribute/field
    - If present, include it in the coding prompt as "Previous round feedback: {feedback}"
    - This enables multi-round code improvement
  - **quant/plugin.py** — QuantCoder.generate_code():
    - Same pattern for factor code generation
  - **synthetic_research/plugin.py** — SyntheticResearchCoder:
    - Same pattern for research code
  - Handle gracefully if _costeer_feedback doesn't exist (first round): no feedback section in prompt

  **Must NOT do**:
  - Do NOT change Coder Protocol in contracts.py
  - Do NOT change CoSTEER evolver logic — just READ what it produces

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small prompt additions to existing Coder methods
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6, 7)
  - **Blocks**: T11, T14
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `core/loop/costeer.py:80-130` — CoSTEEREvolver showing WHERE _costeer_feedback is injected
  - `scenarios/data_science/plugin.py` — DataScienceCoder.generate_code() (current prompt construction)
  - `scenarios/quant/plugin.py` — QuantCoder.generate_code()

  **API/Type References**:
  - Look for how experiment.hypothesis stores feedback — it may be a dict or an attribute

  **WHY Each Reference Matters**:
  - `costeer.py` — Shows exactly what field name and format the feedback is stored in
  - Coder implementations — Need to find prompt construction to add feedback section

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] Each Coder checks for _costeer_feedback and includes it when present

  **QA Scenarios**:

  ```
  Scenario: Coder includes feedback when present
    Tool: Bash (grep)
    Steps:
      1. grep -n "costeer_feedback" scenarios/data_science/plugin.py → at least 1 match
      2. grep -n "costeer_feedback" scenarios/quant/plugin.py → at least 1 match
    Expected Result: Both Coders reference costeer_feedback
    Evidence: .sisyphus/evidence/task-8-coder-feedback.txt

  Scenario: Coder handles missing feedback gracefully
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q -x — tests run without costeer_feedback set
    Expected Result: All tests pass (first round has no feedback, should not crash)
    Evidence: .sisyphus/evidence/task-8-no-feedback.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `scenarios/data_science/plugin.py`, `scenarios/quant/plugin.py`, `scenarios/synthetic_research/plugin.py`

### Wave 3 — Pipeline Integration

- [ ] 9. FC-6 StratifiedSplitter auto-call in build_context + leaderboard population

  **What to do**:
  - **StratifiedSplitter integration**:
    - In each scenario's `build_context()` method (inside ScenarioPlugin), call StratifiedSplitter to split input data
    - Import from `evaluation_service/stratified_splitter.py`
    - Call `splitter.split(data, labels)` to produce train/validation/test splits
    - Store splits in ScenarioContext.config so downstream steps (Runner, FeedbackAnalyzer) can access them
    - If no labels available (unsupervised), skip splitting and use all data
  - **Leaderboard population**:
    - In `evaluation_service/service.py`, modify `evaluate_run()` to write results to the leaderboard dict
    - Each evaluation result should be recorded as: `leaderboard[hypothesis_id] = {"score": score, "metrics": metrics, "timestamp": time.time()}`
    - The leaderboard is currently an empty dict — populate it on every evaluate_run() call
  - **data_science scenario**: StratifiedSplitter splits the dataset for proper train/test
  - **quant scenario**: StratifiedSplitter splits time-series data (chronological split, not random)
  - **synthetic_research**: No data splitting needed (flag or skip)

  **Must NOT do**:
  - Do NOT change StratifiedSplitter implementation — it's COMPLETE, just call it
  - Do NOT make splitting mandatory for scenarios without labeled data

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration across multiple files + scenario-specific split strategies
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 11, 12)
  - **Blocks**: T12, T14
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `evaluation_service/stratified_splitter.py:1-74` — COMPLETE StratifiedSplitter (read its API)
  - `evaluation_service/service.py:40-109` — evaluate_run() and leaderboard (currently empty dict)

  **API/Type References**:
  - Each scenario's ScenarioPlugin.build_context() method — the intake point for splitting
  - `plugins/contracts.py` — ScenarioPlugin Protocol (read-only)

  **WHY Each Reference Matters**:
  - `stratified_splitter.py` — COMPLETE code, read it to understand split() signature
  - `service.py` — evaluate_run() is WHERE leaderboard writes should happen
  - build_context() — WHERE StratifiedSplitter should be called (the data intake point)

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/test_fc6_evaluation.py -q` → PASS
  - [ ] evaluate_run() populates leaderboard (not empty dict after evaluation)
  - [ ] build_context() calls StratifiedSplitter when labels are available

  **QA Scenarios**:

  ```
  Scenario: Leaderboard populated after evaluation
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/test_fc6_evaluation.py -q -x
    Expected Result: Tests pass, leaderboard contains entries after evaluate_run()
    Evidence: .sisyphus/evidence/task-9-leaderboard.txt

  Scenario: StratifiedSplitter called in build_context
    Tool: Bash (grep)
    Steps:
      1. grep -rn "stratified_splitter\|StratifiedSplitter" scenarios/ → at least 2 matches
    Expected Result: StratifiedSplitter imported and called in scenario plugins
    Evidence: .sisyphus/evidence/task-9-splitter-call.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `evaluation_service/service.py`, `scenarios/*/plugin.py`

- [ ] 10. FC-1 StepExecutor applies plan budget as soft timeout default

  **What to do**:
  - In `core/loop/step_executor.py`, modify `_resolve_step_config()` (line ~99) to:
    1. Read `plan.budget_allocation` (from the Plan object passed through the pipeline)
    2. If budget_allocation has a value for the current step (e.g., "coding": 180 seconds), use it as the default timeout
    3. BUT: if the user provided an explicit `step_override` for this step, the step_override ALWAYS wins
    4. Priority: explicit step_override > plan budget > global default
  - The Plan object should be accessible via the run context or passed through LoopEngine
  - Add logging: `logger.debug("Step '%s' timeout: %ds (source: %s)", step_name, timeout, source)`

  **Must NOT do**:
  - Plan budget MUST NOT override explicit user step_overrides
  - Do NOT change StepExecutor.__init__() signature
  - Do NOT make plan budget mandatory

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding config resolution priority chain
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 11, 12)
  - **Blocks**: T13, T14
  - **Blocked By**: T4

  **References**:

  **Pattern References**:
  - `core/loop/step_executor.py:95-120` — _resolve_step_config() current implementation (config priority chain)
  - `core/loop/step_executor.py:50-80` — execute_step() showing how config is used

  **API/Type References**:
  - `data_models.py` — Plan, PlanningStrategy (budget_allocation field)
  - `app/config.py` — step_overrides structure

  **WHY Each Reference Matters**:
  - `step_executor.py:95` — THE function being modified. Must understand existing priority chain before adding plan budget layer.
  - Plan/PlanningStrategy — The budget_allocation data source

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] step_overrides still win over plan budget (write a test for this)
  - [ ] Plan budget is used when no step_override exists

  **QA Scenarios**:

  ```
  Scenario: step_override wins over plan budget
    Tool: Bash (python3)
    Steps:
      1. Construct scenario with step_override for "coding" = 30s and plan budget for "coding" = 180s
      2. Verify resolved timeout is 30s (step_override wins)
    Expected Result: Explicit override takes precedence
    Evidence: .sisyphus/evidence/task-10-override-wins.txt

  Scenario: Plan budget used as default
    Tool: Bash (python3)
    Steps:
      1. Construct scenario with NO step_override but plan budget for "coding" = 180s
      2. Verify resolved timeout is 180s (plan budget used)
    Expected Result: Plan budget applied when no override exists
    Evidence: .sisyphus/evidence/task-10-budget-default.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `core/loop/step_executor.py`

- [ ] 11. FC-5 CoSTEER timing extrapolation from debug runs

  **What to do**:
  - In `core/loop/costeer.py`, add timing measurement and extrapolation:
    1. When running in debug mode (DebugConfig.debug_mode=True), measure actual execution time of the debug run
    2. Extrapolate to full-data time: `estimated_full_time = debug_time / sample_fraction`
    3. Store the estimate in the experiment result: `experiment.estimated_full_time_sec = estimated_full_time`
    4. This enables the planner to adjust future budgets based on actual timing data
  - When NOT in debug mode, skip timing extrapolation (no behavior change)
  - Use `time.monotonic()` for measurement (not `time.time()`)

  **Must NOT do**:
  - Do NOT change behavior when debug_mode=False
  - Do NOT block on timing — just measure and record
  - Do NOT change CoSTEEREvolver's core evolution logic

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding CoSTEER evolution loop + timing measurement
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 12)
  - **Blocks**: T14
  - **Blocked By**: T7, T8

  **References**:

  **Pattern References**:
  - `core/loop/costeer.py:50-130` — CoSTEEREvolver.evolve() loop (wrap with timing)

  **API/Type References**:
  - `data_models.py` — DebugConfig (sample_fraction for extrapolation)
  - `data_models.py` — ExecutionResult or experiment result type (where to store estimated time)

  **WHY Each Reference Matters**:
  - `costeer.py` — THE file to modify. Wrap the execution section with timing measurement.
  - DebugConfig.sample_fraction — The divisor for extrapolation calculation.

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/test_e2e_fc3.py -q` → CoSTEER tests pass
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass

  **QA Scenarios**:

  ```
  Scenario: Timing extrapolation calculated correctly
    Tool: Bash (python3)
    Steps:
      1. debug_time = 5.0 seconds, sample_fraction = 0.1
      2. estimated_full_time = 5.0 / 0.1 = 50.0 seconds
      3. Verify this calculation in the code
    Expected Result: Extrapolation formula is correct
    Evidence: .sisyphus/evidence/task-11-timing.txt

  Scenario: No timing when debug_mode=False
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q -x
    Expected Result: All tests pass (no timing code runs in non-debug mode)
    Evidence: .sisyphus/evidence/task-11-no-debug.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `core/loop/costeer.py`

- [ ] 12. FC-6 ValidationSelector in LoopEngine for multi-candidate ranking

  **What to do**:
  - In `core/loop/engine.py`, after the feedback step produces scores for multiple candidates:
    1. Import ValidationSelector from `evaluation_service/validation_selector.py`
    2. Call `selector.select_best(candidates, scores)` to pick the winner
    3. The current code likely just takes the top score — replace with ValidationSelector logic
    4. ValidationSelector should use the leaderboard (populated in T9) for historical comparison
  - ValidationSelector already exists and is implemented — just need to wire it into the engine
  - Handle single-candidate case gracefully (no selection needed, just pass through)

  **Must NOT do**:
  - Do NOT change ValidationSelector implementation — it's COMPLETE
  - Do NOT change LoopEngine.run() signature

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Engine integration requiring understanding of candidate flow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11)
  - **Blocks**: T14
  - **Blocked By**: T9

  **References**:

  **Pattern References**:
  - `core/loop/engine.py:90-200` — LoopEngine.run() main loop (find where candidate selection happens)
  - `evaluation_service/validation_selector.py:1-37` — COMPLETE ValidationSelector (read its API)

  **API/Type References**:
  - `evaluation_service/service.py` — Leaderboard dict structure (populated in T9)

  **WHY Each Reference Matters**:
  - `engine.py` — THE file to modify. Must find the candidate selection point in the main loop.
  - `validation_selector.py` — COMPLETE code to call. Read its select_best() method signature.

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] ValidationSelector is imported and called in engine.py

  **QA Scenarios**:

  ```
  Scenario: ValidationSelector wired into engine
    Tool: Bash (grep)
    Steps:
      1. grep -n "ValidationSelector\|validation_selector" core/loop/engine.py → at least 1 match
    Expected Result: ValidationSelector imported and used in LoopEngine
    Evidence: .sisyphus/evidence/task-12-selector-wired.txt

  Scenario: Single candidate passthrough
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q -x
    Expected Result: All tests pass (most tests use single candidate)
    Evidence: .sisyphus/evidence/task-12-single-candidate.txt
  ```

  **Commit**: YES (groups with Wave 2+3)
  - Files: `core/loop/engine.py`

### Wave 4 — Cross-FC Wiring + Tests

- [ ] 13. Cross-FC integration wiring + LoopEngine history_summary feed

  **What to do**:
  - **LoopEngine history_summary** (THE critical wiring):
    - In `core/loop/engine.py` line 106, replace `history_summary={}` with actual history data
    - After each iteration completes, collect: hypothesis text, score, what worked, what didn't
    - Format as dict: `{"iteration_N": {"hypothesis": text, "score": float, "outcome": str}}`
    - Pass this to `planner.generate_plan(history_summary=history)` so the planner has context
  - **Cross-FC data flow verification**:
    - Verify that Plan → StepExecutor → budget applied (T4 + T10)
    - Verify that MemoryService → ContextPack → ProposalEngine (T5 + T6)
    - Verify that DebugConfig → Runner → timing → CoSTEER extrapolation (T3 + T7 + T11)
    - Verify that StratifiedSplitter → splits → FeedbackAnalyzer → leaderboard (T9 + T12)
  - **Wire ContextPack metadata**:
    - Ensure branch_id from exploration_manager is passed through to ContextPack
    - Ensure cross-branch hypotheses are merged with branch_id metadata set
  - This task is primarily about making sure the FULL data pipeline flows end-to-end, not individual components

  **Must NOT do**:
  - Do NOT re-implement any individual FC — they should already work from previous tasks
  - Do NOT change any Protocol signatures

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Cross-cutting integration across multiple modules, requires system-level understanding
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on Wave 2+3)
  - **Blocks**: T14
  - **Blocked By**: T4, T5, T6, T10

  **References**:

  **Pattern References**:
  - `core/loop/engine.py:90-200` — LoopEngine.run() main loop (THE file for integration wiring)
  - `core/loop/engine.py:106` — `history_summary={}` (THE line to fix)

  **API/Type References**:
  - `planner/service.py` — generate_plan() accepts history_summary parameter
  - `memory_service/service.py` — query_context() returns ContextPack
  - `core/loop/step_executor.py` — _resolve_step_config() uses plan budget

  **WHY Each Reference Matters**:
  - `engine.py` — THE orchestration point where all FC data converges. This is where you verify the pipeline works.
  - Each service file — Verify that what one module produces matches what the next module expects.

  **Acceptance Criteria**:
  - [ ] `grep "history_summary={}" core/loop/engine.py` → NO matches (empty dict replaced)
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] Data flows: Plan→StepExecutor, Memory→ProposalEngine, Debug→Runner, Splitter→Leaderboard all verified

  **QA Scenarios**:

  ```
  Scenario: history_summary no longer empty
    Tool: Bash (grep)
    Steps:
      1. grep -n "history_summary={}" core/loop/engine.py → should return empty
      2. grep -n "history_summary" core/loop/engine.py → should show populated dict
    Expected Result: history_summary is built from iteration results, not hardcoded empty
    Evidence: .sisyphus/evidence/task-13-history-summary.txt

  Scenario: Full pipeline data flow
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q -x
    Expected Result: All tests pass — full pipeline is connected
    Evidence: .sisyphus/evidence/task-13-pipeline.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Message: `test(fc-1456): add targeted behavioral tests and edge case handling for all 4 FCs`
  - Files: `core/loop/engine.py`

- [ ] 14. Targeted regression tests for all 4 FCs (behavioral assertions)

  **What to do**:
  - Create or extend test files with BEHAVIORAL assertions (not just "returns dict"):
  - **FC-1 tests** (`tests/test_fc1_planning.py`):
    - Test that PlanningStrategy.budget_allocation contains step names as keys
    - Test that budget values are positive numbers (seconds)
    - Test fallback: None budget → equal distribution
  - **FC-4 tests** (`tests/test_memory_service.py` or `tests/test_fc4_*.py`):
    - Test that query_context() returns scored_items (not just items)
    - Test that scored_items are sorted by score descending
    - Test that cross-branch hypotheses are included when available
    - Test that ProposalEngine.propose() prompt contains context highlights (mock LLM, check prompt)
  - **FC-5 tests** (`tests/test_e2e_fc3.py` or new file):
    - Test that debug_mode=True reduces data (verify row count decreased)
    - Test that debug_mode=False produces identical results to current behavior
    - Test that _costeer_feedback is included in Coder prompt when present
  - **FC-6 tests** (`tests/test_fc6_evaluation.py`):
    - Test that leaderboard is populated after evaluate_run() (not empty dict)
    - Test that leaderboard entries have score, metrics, timestamp fields
    - Test that StratifiedSplitter is called in build_context() (mock splitter, verify call)
  - All tests should use pytest fixtures and mocks where needed (NOT real LLM calls)

  **Must NOT do**:
  - Do NOT require real LLM calls in unit tests
  - Do NOT make tests flaky or timing-dependent
  - Do NOT duplicate existing test coverage

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Writing comprehensive behavioral tests across 4 FCs
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (needs all FCs wired first)
  - **Blocks**: T16
  - **Blocked By**: T6, T7, T9, T10, T11, T12, T13

  **References**:

  **Test References**:
  - `tests/test_fc1_planning.py` — Existing FC-1 tests (extend, don't duplicate)
  - `tests/test_fc4_interaction_kernel.py` — Existing kernel tests
  - `tests/test_memory_service.py` — Existing memory tests
  - `tests/test_fc6_evaluation.py` — Existing evaluation tests (currently permissive)
  - `tests/test_fc1456_wiring.py` — Existing wiring tests

  **WHY Each Reference Matters**:
  - Each existing test file — Must extend, not duplicate. Read current assertions to know what's already covered.
  - `test_fc6_evaluation.py` — Currently asserts "returns dict" — needs behavioral upgrade.

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass (old + new)
  - [ ] At least 15 new behavioral assertions across the 4 FCs
  - [ ] No new test requires real LLM calls

  **QA Scenarios**:

  ```
  Scenario: All new tests pass
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/test_fc1_planning.py tests/test_memory_service.py tests/test_fc6_evaluation.py -v
    Expected Result: All tests pass, new behavioral assertions verified
    Evidence: .sisyphus/evidence/task-14-tests.txt

  Scenario: No test uses real LLM
    Tool: Bash (grep)
    Steps:
      1. grep -rn "GEMINI_API_KEY\|openai.api_key" tests/test_fc1_planning.py tests/test_memory_service.py tests/test_fc6_evaluation.py → should return empty
    Expected Result: Zero real API key references in unit tests
    Evidence: .sisyphus/evidence/task-14-no-llm.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Files: `tests/test_fc1_planning.py`, `tests/test_memory_service.py`, `tests/test_fc6_evaluation.py`, `tests/test_fc1456_wiring.py`
  - Pre-commit: `python3 -m pytest tests/ -q -x`

- [ ] 15. Edge case handling (zero budget, no candidates, no labels, etc.)

  **What to do**:
  - Audit all new FC integration code for edge cases:
  - **Zero/None budget**: Planner returns None budget → StepExecutor uses global default, not crash
  - **No candidates**: ValidationSelector receives empty list → returns None, not crash
  - **No labels**: StratifiedSplitter receives data without labels → skip splitting, return full dataset
  - **Empty ContextPack**: ProposalEngine receives ContextPack with empty items → prompt omits "prior context" section, not crash
  - **No cross-branch hypotheses**: MemoryService has no other branches → return within-branch only, not error
  - **No CoSTEER feedback**: First CoSTEER round → Coder omits feedback section, not crash
  - **Debug mode with sample_fraction=0**: Handle gracefully → log warning, use full data
  - Add defensive None checks and fallback values wherever integration points exist

  **Must NOT do**:
  - Do NOT add excessive error handling that masks real bugs
  - Do NOT add try/except that silently swallows errors

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small defensive additions to existing code
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T14)
  - **Parallel Group**: Wave 4 (with T13, T14)
  - **Blocks**: T14
  - **Blocked By**: T13

  **References**:
  - All files modified in T4-T13 — audit each for edge cases
  - Focus on: None checks, empty list handling, missing dict keys

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q -x` → all tests pass
  - [ ] No uncaught exceptions on empty/None inputs at integration points

  **QA Scenarios**:

  ```
  Scenario: Empty ContextPack doesn't crash ProposalEngine
    Tool: Bash (python3)
    Steps:
      1. python3 -c "from data_models import ContextPack; c = ContextPack(); assert c.items == []; assert c.highlights == []; print('PASS')"
    Expected Result: Empty ContextPack is valid and doesn't cause errors
    Evidence: .sisyphus/evidence/task-15-empty-context.txt
  ```

  **Commit**: YES (groups with Wave 4)
  - Files: Various (wherever edge cases are found)

### Wave 5 — Documentation + Final

- [ ] 16. Update README FC table + paper_gap_analysis.md

  **What to do**:
  - In `README.md`, update the FC status table:
    - FC-1 Planning: "Partial" → "Implemented" with updated description
    - FC-4 Memory Context: "Partial" → "Implemented" with updated description
    - FC-5 Coding Workflow: "Partial" → "Implemented" with updated description
    - FC-6 Evaluation Strategy: "Partial" → "Implemented" with updated description
  - In `dev_doc/paper_gap_analysis.md`, update each FC section to reflect completions:
    - Mark completed items, update status, note what was wired
  - Keep descriptions concise — match the style of existing FC-2/FC-3 entries
  - Example updated row: `| FC-1 Planning | Implemented | Dynamic time-aware budget allocation with step-level soft timeouts |`

  **Must NOT do**:
  - Do NOT change FC-2 or FC-3 descriptions (they're already correct)
  - Do NOT add marketing language — stick to technical accuracy

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation updates
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after all implementation verified)
  - **Blocks**: T17
  - **Blocked By**: T14

  **References**:
  - `README.md:9-18` — Current FC status table
  - `dev_doc/paper_gap_analysis.md` — Full gap analysis (500 lines)

  **Acceptance Criteria**:
  - [ ] README FC table shows all 6 as "Implemented"
  - [ ] paper_gap_analysis.md updated with completion notes
  - [ ] `grep "Partial" README.md` → NO matches in FC table

  **QA Scenarios**:

  ```
  Scenario: All FCs marked Implemented
    Tool: Bash (grep)
    Steps:
      1. grep -c "Implemented" README.md → should be 6
      2. grep -c "Partial" README.md → should be 0 (in FC table section)
    Expected Result: 6 Implemented, 0 Partial
    Evidence: .sisyphus/evidence/task-16-readme.txt
  ```

  **Commit**: YES
  - Message: `docs: mark all 6 framework components as Implemented in README`
  - Files: `README.md`, `dev_doc/paper_gap_analysis.md`

- [ ] 17. Final full test suite run + commit and push

  **What to do**:
  - Run the full test suite: `python3 -m pytest tests/ -q`
  - Verify 750+ tests pass (739 original + new FC tests)
  - Run all 3 e2e scripts (if LLM key available):
    - `python3 scripts/run_quant_e2e.py`
    - `python3 scripts/run_data_science_e2e.py`
    - `python3 scripts/run_synthetic_research_e2e.py`
  - If any test fails, fix it before proceeding
  - Create commits per the Commit Strategy (4 commits)
  - Push all commits to `origin/feat/quant-scenario`

  **Must NOT do**:
  - Do NOT push if tests fail
  - Do NOT skip e2e tests if LLM key is available

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Test running and git operations
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final step)
  - **Blocks**: F1-F4
  - **Blocked By**: T16

  **References**:
  - `tests/` — Full test suite
  - `scripts/run_*_e2e.py` — E2E test scripts

  **Acceptance Criteria**:
  - [ ] `python3 -m pytest tests/ -q` → 750+ passed, 0 failed
  - [ ] All 3 e2e scripts complete successfully (or skip with note if no LLM key)
  - [ ] All commits pushed to `origin/feat/quant-scenario`

  **QA Scenarios**:

  ```
  Scenario: Full test suite passes
    Tool: Bash (pytest)
    Steps:
      1. python3 -m pytest tests/ -q
    Expected Result: 750+ passed, 0 failed, 0 errors
    Evidence: .sisyphus/evidence/task-17-tests.txt

  Scenario: Git push succeeds
    Tool: Bash (git)
    Steps:
      1. git log --oneline -5 — verify all 4 commits present
      2. git push origin feat/quant-scenario — verify push succeeds
    Expected Result: Push succeeds, branch is up to date
    Evidence: .sisyphus/evidence/task-17-push.txt
  ```

  **Commit**: YES (this IS the commit task)
  - 4 commits per Commit Strategy section above
  - Push: `git push origin feat/quant-scenario`

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python3 -m pytest tests -q`. Review all changed files for: type ignores, empty catches, print() in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA** — `unspecified-high`
  Start from clean state. Run all 3 e2e test scripts. Run targeted FC tests. Verify behavioral assertions pass.
  Output: `E2E [3/3 pass] | FC Tests [N/N] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Commit 1** (after Wave 1): `feat(models): extend ContextPack, PlanningStrategy, and Runner protocol for FC-1/4/5/6`
- **Commit 2** (after Wave 2+3): `feat(fc-1456): wire InteractionKernel, plan budget, debug mode, and StratifiedSplitter into pipeline`
- **Commit 3** (after Wave 4): `test(fc-1456): add targeted behavioral tests and edge case handling for all 4 FCs`
- **Commit 4** (after Wave 5): `docs: mark all 6 framework components as Implemented in README`

---

## Success Criteria

### Verification Commands
```bash
python3 -m pytest tests -q                    # Expected: 750+ passed, 0 failed
python3 scripts/run_quant_e2e.py              # Expected: PASS
python3 scripts/run_data_science_e2e.py       # Expected: PASS
python3 scripts/run_synthetic_research_e2e.py # Expected: PASS
```

### Final Checklist
- [ ] All "Must Have" present — InteractionKernel, StratifiedSplitter, plan budget, debug mode all wired
- [ ] All "Must NOT Have" absent — no protocol changes, no new DBs, no async, no mock fallbacks
- [ ] All tests pass (739+ existing + new FC tests)
- [ ] README shows all 6 FCs as "Implemented"
- [ ] paper_gap_analysis.md updated to reflect completions
