# FC-1 + FC-4 + FC-5 + FC-6: Planning, Memory, Coding Workflow, Evaluation

## TL;DR

> **Quick Summary**: Implement the remaining 4 paper components — FC-1 (dynamic time-aware planning), FC-4 (cross-branch collaborative memory with interaction kernel), FC-5 (debug-mode coding workflow with multi-stage evaluation), and FC-6 (automated stratified evaluation with ValidationSelector) — completing the full RDAgent paper reproduction.
> 
> **Deliverables**:
> - FC-1: Time measurement in LoopEngine, BudgetLedger extension, LLM-based strategy generation, time-aware planning prompts/schemas
> - FC-4: Hypothesis storage table, TF-IDF cosine similarity, interaction kernel (α·cosine + β·score_delta + γ·decay), Algorithm 2 adaptive selection (Select/Modify/Generate), cross-branch hypothesis sharing
> - FC-5: Debug mode config, ExecutionResult duration propagation, 10% data sampling injection, multi-stage evaluation (execution→alignment→debug_compliance→authenticity)
> - FC-6: 90/10 stratified train/test splitter, real evaluate_run scoring, ValidationSelector multi-candidate ranking, grading script generation
> - Full TDD coverage for all new components
> - Updated design documents
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1 (data models) → T5 (planning service) → T11 (wiring) → T13 (E2E test)

---

## Context

### Original Request
Complete ALL 6 Framework Components from the RDAgent paper. FC-2 (Exploration Path) and FC-3 (Reasoning Pipeline) are done (305 tests, 16 commits). Now implement FC-1, FC-4, FC-5, FC-6 with precise paper reproduction, full TDD, and conservative design choices.

### Prior Work Summary
**FC-2 (DONE)**: MCTS/PUCT scheduler, branch pruning, trace merging, multi-branch engine, ExplorationGraph DAG
**FC-3 (DONE)**: 4-stage reasoning pipeline (analyze→identify→hypothesize→design), virtual evaluation N=5/K=2

### Key Constraints from User
- "论文精确复现" — Precise paper reproduction
- "TDD" — RED-GREEN-REFACTOR testing approach
- "统一选择保守而稳妥的方案" — When choices arise, always choose conservative/stable approach
- No NetworkX, no asyncio, no changes to 6 Protocol signatures in `plugins/contracts.py`

### Research Findings (from exploration phase)
- **FC-1**: Planner already has `_compute_progress()`, `_stage_from_progress()`, `_build_guidance()`. BudgetLedger exists but `elapsed_time` is never updated. LoopEngine never measures iteration time.
- **FC-4**: MemoryService is SQLite text store with `failure_cases` table. No embedding/cosine/vector code anywhere. ContextPack has `items` + `highlights` only. ProposalEngine ignores context.
- **FC-5**: BackendResult already has `duration_sec` and `timed_out` but ExecutionResult doesn't propagate them. EvaluationService is all placeholders (returns 0.0). CoSTEER has coder→runner→feedback loop.
- **FC-6**: TaskIntakeDataSplitter already has `_split_by_stratified()` with 70/20/10 defaults. DataSplitManifest exists with train_ids/val_ids/test_ids. EvaluationService stubs return empty.

### Bug History (lessons from FC-2+FC-3 to avoid repeating)
- **Prompt-Schema field name mismatch**: Every prompt's `## Output Fields` must use EXACT field names from schema's `from_dict()`.
- **Mock detection order**: More specific patterns MUST come before less specific ones in MockLLMProvider.complete().

---

## Work Objectives

### Core Objective
Complete the full paper reproduction by implementing time-aware planning (FC-1), cross-branch collaborative memory (FC-4), debug-mode coding workflow (FC-5), and automated evaluation (FC-6), matching the paper's Appendix E specifications.

### Concrete Deliverables
- `data_models.py`: Extended BudgetLedger (iteration timing), ContextPack (scored_items), ExecutionResult (duration_sec, timed_out)
- `llm/schemas.py`: New PlanningStrategy schema, HypothesisModification schema
- `llm/prompts.py`: New planning_strategy_prompt, hypothesis_modification_prompt
- `llm/adapter.py`: Mock responses for FC-1/FC-4 prompts
- `planner/service.py`: LLM-enhanced time-aware planning with dynamic strategy
- `memory_service/service.py`: Hypothesis storage table, extended query_context
- `memory_service/interaction_kernel.py`: NEW — TF-IDF cosine + score_delta + temporal_decay
- `memory_service/hypothesis_selector.py`: NEW — Algorithm 2 (Select/Modify/Generate)
- `core/loop/engine.py`: Time measurement per iteration, elapsed_time updates
- `core/loop/costeer.py`: Debug mode flag propagation
- `evaluation_service/service.py`: Multi-stage evaluation, real scoring
- `evaluation_service/stratified_splitter.py`: NEW — 90/10 stratified train/test split
- `evaluation_service/validation_selector.py`: NEW — multi-candidate ranking
- `app/config.py`: New config fields (debug_mode, FC-1/4/5/6 parameters)
- `app/runtime.py`: Wire new services and config

### Definition of Done
- [ ] All existing 305 tests still pass (zero regression)
- [ ] All new tests pass (`python -m pytest tests/` → 0 failures)
- [ ] FC-1: Planner uses LLM for strategy generation; BudgetLedger.elapsed_time tracks real time
- [ ] FC-4: Hypotheses stored with scores; interaction kernel computes similarity; Algorithm 2 selects/modifies/generates
- [ ] FC-5: ExecutionResult propagates duration_sec; debug mode injects sampling config
- [ ] FC-6: 90/10 stratified split works; evaluate_run returns real scores; ValidationSelector ranks candidates
- [ ] No changes to 6 Protocol signatures in `plugins/contracts.py`
- [ ] MockLLMProvider updated to support all new prompt patterns

### Must Have
- Time measurement per iteration in LoopEngine (FC-1)
- LLM-based planning strategy generation (FC-1)
- Hypothesis storage with score tracking in SQLite (FC-4)
- TF-IDF-based cosine similarity (conservative, no external deps) (FC-4)
- Interaction kernel: K = α·cosine + β·score_delta + γ·decay (FC-4)
- Algorithm 2: Select/Modify/Generate adaptive hypothesis selection (FC-4)
- ExecutionResult duration_sec propagation from BackendResult (FC-5)
- Debug mode config with 10% sampling (FC-5)
- Multi-stage evaluation in EvaluationService (FC-5)
- 90/10 stratified train/test split (FC-6)
- ValidationSelector for multi-candidate ranking (FC-6)
- Full backward compatibility with existing plugin contracts
- TDD: tests written before implementation for each component
- MockLLMProvider support for all new stages

### Must NOT Have (Guardrails)
- **No external embedding libraries** (no FAISS, no sentence-transformers) — use pure Python TF-IDF
- **No NetworkX** — existing adjacency list pattern
- **No asyncio/concurrent execution** — sequential for stability
- **No changes to 6 Protocol signatures** in `plugins/contracts.py`
- **No new web frameworks or ORMs**
- **No Docker infrastructure changes**
- **No RAG integration** — paper showed RAG hurts performance
- **No breaking changes to public APIs** — MemoryService.write_memory/query_context/get_memory_stats, Planner.generate_plan/update_planning_state, EvaluationService.evaluate_run/aggregate_branch_scores/get_leaderboard

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (unittest, 305 tests passing)
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: `python -m pytest tests/` (unittest-compatible)
- **Each task follows**: Write failing test → implement minimal code → refactor

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Core logic**: Use Bash (python REPL / pytest) — Import, call functions, compare output
- **Integration**: Use Bash (python -m pytest) — Run test suites, verify all pass
- **LLM interaction**: Use Bash (python script) — Mock LLM calls, verify structured output parsing

---

## Execution Strategy

### Parallel Execution Waves

> Wave 1 = Foundation (shared data models, schemas, prompts, mocks). Wave 2 = FC-1 + FC-4. Wave 3 = FC-5 + FC-6. Wave 4 = Integration + verification.

```
Wave 1 (Start Immediately — Foundation for all FCs):
├── Task 1: Extended data models (BudgetLedger, ContextPack, ExecutionResult) [quick]
├── Task 2: FC-1/FC-4 schemas (PlanningStrategy, HypothesisModification) [quick]
├── Task 3: FC-1/FC-4 prompt templates [quick]
├── Task 4: MockLLMProvider extensions for FC-1/FC-4 prompts [quick]

Wave 2 (After Wave 1 — FC-1 Planning + FC-4 Memory):
├── Task 5: FC-1 time-aware planning service (depends: 1, 2, 3, 4) [deep]
├── Task 6: FC-4 interaction kernel — TF-IDF + cosine + decay (depends: 1) [deep]
├── Task 7: FC-4 hypothesis selector — Algorithm 2 (depends: 1, 2, 3, 4, 6) [deep]
├── Task 8: FC-4 memory service extension (depends: 1, 6, 7) [deep]

Wave 3 (After Wave 1 — FC-5 Coding + FC-6 Evaluation, can overlap with Wave 2):
├── Task 9: FC-5 debug mode + ExecutionResult extension (depends: 1) [unspecified-high]
├── Task 10: FC-6 stratified splitter + ValidationSelector + real evaluate_run (depends: 1) [deep]

Wave 4 (After Waves 2+3 — Integration + Verification):
├── Task 11: Wiring — config.py, runtime.py, LoopEngine time tracking (depends: 5, 8, 9, 10) [deep]
├── Task 12: End-to-end integration test — full loop with all FCs (depends: 11) [deep]
├── Task 13: Update gap analysis documents (depends: 12) [writing]

Critical Path: T1 → T5 → T11 → T12 → T13
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1   | —         | T5, T6, T7, T8, T9, T10, T11 | 1 |
| T2   | —         | T5, T7 | 1 |
| T3   | —         | T5, T7 | 1 |
| T4   | —         | T5, T7 | 1 |
| T5   | T1, T2, T3, T4 | T11 | 2 |
| T6   | T1       | T7, T8 | 2 |
| T7   | T1, T2, T3, T4, T6 | T8 | 2 |
| T8   | T1, T6, T7 | T11 | 2 |
| T9   | T1       | T11 | 3 |
| T10  | T1       | T11 | 3 |
| T11  | T5, T8, T9, T10 | T12 | 4 |
| T12  | T11      | T13 | 4 |
| T13  | T12      | — | 4 |

### Agent Dispatch Summary

| Wave | Count | Tasks → Categories |
|------|-------|--------------------|
| 1    | 4     | T1 → `quick`, T2 → `quick`, T3 → `quick`, T4 → `quick` |
| 2    | 4     | T5 → `deep`, T6 → `deep`, T7 → `deep`, T8 → `deep` |
| 3    | 2     | T9 → `unspecified-high`, T10 → `deep` |
| 4    | 3     | T11 → `deep`, T12 → `deep`, T13 → `writing` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

### Wave 1 — Foundation (Data Models, Schemas, Prompts, Mocks)

- [ ] 1. Extended Data Models for FC-1/4/5/6

  **What to do**:
  - Extend `BudgetLedger` in `data_models.py` with new fields:
    - `iteration_durations: List[float] = field(default_factory=list)` — per-iteration wall-clock seconds
    - `estimated_remaining: float = 0.0` — estimated time remaining based on moving average
  - Extend `ContextPack` in `data_models.py` with new field:
    - `scored_items: List[Tuple[str, float]] = field(default_factory=list)` — (hypothesis_text, relevance_score) pairs from FC-4 interaction kernel
  - Extend `ExecutionResult` in `data_models.py` with new fields:
    - `duration_sec: float = 0.0` — propagated from BackendResult.duration_sec
    - `timed_out: bool = False` — propagated from BackendResult.timed_out
  - Write TDD tests FIRST: test new fields have correct defaults, backward compatibility (existing construction works)

  **Must NOT do**:
  - Do NOT change existing field types or names
  - Do NOT modify `model_to_dict()` — it already handles List, Dict, Tuple
  - Do NOT add any methods to these dataclasses

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3, T4)
  - **Blocks**: T5, T6, T7, T8, T9, T10, T11
  - **Blocked By**: None

  **References**:
  - `data_models.py:396-401` — Current BudgetLedger
  - `data_models.py:414-418` — Current ContextPack
  - `data_models.py:421-428` — Current ExecutionResult
  - `core/execution/backend.py:27-38` — BackendResult with duration_sec and timed_out fields

  **Acceptance Criteria**:
  - [ ] BudgetLedger has `iteration_durations` and `estimated_remaining` fields
  - [ ] ContextPack has `scored_items` field (List of (str, float) tuples)
  - [ ] ExecutionResult has `duration_sec` and `timed_out` fields
  - [ ] All existing construction still works (backward compatible defaults)
  - [ ] `python -m pytest tests/` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: BudgetLedger backward compatibility
    Tool: Bash (python -c)
    Steps:
      1. python -c "from data_models import BudgetLedger; b = BudgetLedger(total_time_budget=100.0); assert b.iteration_durations == []; assert b.estimated_remaining == 0.0; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-1-budget-compat.txt

  Scenario: ContextPack scored_items
    Tool: Bash (python -c)
    Steps:
      1. python -c "from data_models import ContextPack; cp = ContextPack(scored_items=[('hyp1', 0.8), ('hyp2', 0.6)]); assert len(cp.scored_items) == 2; assert cp.scored_items[0] == ('hyp1', 0.8); print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-1-context-scored.txt

  Scenario: ExecutionResult duration propagation
    Tool: Bash (python -c)
    Steps:
      1. python -c "from data_models import ExecutionResult; er = ExecutionResult(run_id='r1', exit_code=0, logs_ref='l', artifacts_ref='a', duration_sec=12.5, timed_out=False); assert er.duration_sec == 12.5; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-1-exec-duration.txt
  ```

- [ ] 2. FC-1/FC-4 LLM Schemas (PlanningStrategy, HypothesisModification)

  **What to do**:
  - Add `PlanningStrategy` dataclass to `llm/schemas.py`:
    - `strategy_name: str = ""` — e.g. "explore_novel", "refine_best", "consolidate"
    - `method_selection: str = ""` — recommended approach method
    - `exploration_weight: float = 0.5` — 0.0 (pure exploit) to 1.0 (pure explore)
    - `reasoning: str = ""` — rationale for strategy choice
    - `from_dict()` classmethod following existing pattern
  - Add `HypothesisModification` dataclass to `llm/schemas.py`:
    - `modified_hypothesis: str = ""` — the adapted hypothesis text
    - `modification_type: str = ""` — "select" | "modify" | "generate"
    - `source_hypothesis: str = ""` — which original hypothesis was used
    - `reasoning: str = ""` — rationale
    - `from_dict()` classmethod following existing pattern
  - Write TDD tests: each schema has from_dict(), handles missing fields gracefully

  **Must NOT do**:
  - Do NOT modify existing schemas (ProposalDraft, CodeDraft, FeedbackDraft, etc.)
  - Do NOT add validation logic — schemas are pure data containers

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3, T4)
  - **Blocks**: T5, T7
  - **Blocked By**: None

  **References**:
  - `llm/schemas.py:9-21` — ProposalDraft pattern (follow exactly)
  - `llm/schemas.py:58-72` — AnalysisResult pattern (existing FC-3 schema)

  **Acceptance Criteria**:
  - [ ] PlanningStrategy has 4 fields with defaults + from_dict()
  - [ ] HypothesisModification has 4 fields with defaults + from_dict()
  - [ ] from_dict({}) returns valid objects with defaults
  - [ ] `python -m pytest tests/` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: PlanningStrategy from_dict
    Tool: Bash (python -c)
    Steps:
      1. python -c "from llm.schemas import PlanningStrategy; ps = PlanningStrategy.from_dict({'strategy_name': 'explore', 'exploration_weight': 0.8}); assert ps.strategy_name == 'explore'; assert ps.exploration_weight == 0.8; assert ps.reasoning == ''; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-2-planning-schema.txt

  Scenario: HypothesisModification from_dict
    Tool: Bash (python -c)
    Steps:
      1. python -c "from llm.schemas import HypothesisModification; hm = HypothesisModification.from_dict({'modified_hypothesis': 'test', 'modification_type': 'modify'}); assert hm.modified_hypothesis == 'test'; assert hm.modification_type == 'modify'; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-2-hypothesis-schema.txt
  ```

- [ ] 3. FC-1/FC-4 Prompt Templates

  **What to do**:
  - Add `planning_strategy_prompt()` to `llm/prompts.py`:
    - Parameters: `task_summary: str, scenario_name: str, progress: float, stage: str, iteration: int, history_summary: Dict[str, str], budget_remaining: float`
    - Follows paper Appendix E.1 structure: role assignment → context (progress, budget, history) → instruction (select strategy for current stage) → output fields
    - Output fields must EXACTLY match PlanningStrategy schema: `strategy_name`, `method_selection`, `exploration_weight`, `reasoning`
    - Uses `_build_schema_hint(PlanningStrategy)` for JSON format hint
  - Add `hypothesis_modification_prompt()` to `llm/prompts.py`:
    - Parameters: `source_hypothesis: str, action: str, context_items: List[str], task_summary: str, scenario_name: str`
    - action is one of: "select", "modify", "generate"
    - Follows paper Appendix E.4 structure: role → context (source hypothesis, action type, relevant memories) → instruction → output fields
    - Output fields must EXACTLY match HypothesisModification schema: `modified_hypothesis`, `modification_type`, `source_hypothesis`, `reasoning`
    - Uses `_build_schema_hint(HypothesisModification)` for JSON format hint
  - Write TDD tests: each prompt returns non-empty string, contains expected field names

  **Must NOT do**:
  - Do NOT modify existing prompt functions
  - Do NOT hardcode parameter values in prompts
  - **CRITICAL**: Output field names in prompts MUST match schema from_dict() keys EXACTLY (lesson from FC-3 bugs)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T4)
  - **Blocks**: T5, T7
  - **Blocked By**: None

  **References**:
  - `llm/prompts.py:59-103` — `proposal_prompt()` pattern (role → context → instruction → output fields)
  - `llm/prompts.py:17-37` — `_build_schema_hint()` function
  - `llm/prompts.py:40-56` — `_iteration_strategy()` for reuse in planning prompt

  **Acceptance Criteria**:
  - [ ] `planning_strategy_prompt()` exists and returns string containing all 4 PlanningStrategy field names
  - [ ] `hypothesis_modification_prompt()` exists and returns string containing all 4 HypothesisModification field names
  - [ ] Both prompts use `_build_schema_hint()` for JSON format guidance
  - [ ] `python -m pytest tests/` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Planning prompt contains schema fields
    Tool: Bash (python -c)
    Steps:
      1. python -c "from llm.prompts import planning_strategy_prompt; p = planning_strategy_prompt('task', 'ds', 0.3, 'early', 1, {}, 70.0); assert 'strategy_name' in p; assert 'method_selection' in p; assert 'exploration_weight' in p; assert 'reasoning' in p; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-3-planning-prompt.txt

  Scenario: Hypothesis prompt contains schema fields
    Tool: Bash (python -c)
    Steps:
      1. python -c "from llm.prompts import hypothesis_modification_prompt; p = hypothesis_modification_prompt('hyp1', 'modify', ['ctx1'], 'task', 'ds'); assert 'modified_hypothesis' in p; assert 'modification_type' in p; assert 'source_hypothesis' in p; assert 'reasoning' in p; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-3-hypothesis-prompt.txt
  ```

- [ ] 4. MockLLMProvider Extensions for FC-1/FC-4

  **What to do**:
  - Add mock responses in `llm/adapter.py` MockLLMProvider.complete() for:
    1. Planning strategy detection: check for `strategy_name` AND `method_selection` in prompt → return valid PlanningStrategy JSON
    2. Hypothesis modification detection: check for `modified_hypothesis` AND `modification_type` in prompt → return valid HypothesisModification JSON
  - **CRITICAL: Detection order matters!** These new detections must be placed BEFORE the existing FC-3 experiment design detection (`is_experiment = "implementation_steps" in prompt`) but AFTER the merge detection. Order:
    1. Merge detection (existing, most specific)
    2. Feedback detection (existing)
    3. FC-3 analysis (existing)
    4. FC-3 problem (existing)
    5. FC-3 hypothesis (existing)
    6. **FC-1 planning strategy (NEW)** — detect `strategy_name` AND `method_selection`
    7. **FC-4 hypothesis modification (NEW)** — detect `modified_hypothesis` AND `modification_type`
    8. FC-3 experiment design (existing)
    9. FC-3 virtual eval (existing)
    10. Default fallback (existing)
  - Write TDD tests: complete() with planning-like prompt returns valid PlanningStrategy JSON; complete() with hypothesis-like prompt returns valid HypothesisModification JSON

  **Must NOT do**:
  - Do NOT change the detection logic or response format for existing mock patterns
  - Do NOT reorder existing detections (only insert new ones at correct positions)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2, T3)
  - **Blocks**: T5, T7
  - **Blocked By**: None

  **References**:
  - `llm/adapter.py:60-180` — MockLLMProvider.complete() with existing detection order
  - `llm/adapter.py:117-178` — FC-3 detection patterns (insert new patterns BEFORE line 151 `is_experiment`)

  **Acceptance Criteria**:
  - [ ] Planning strategy mock returns JSON with `strategy_name`, `method_selection`, `exploration_weight`, `reasoning`
  - [ ] Hypothesis modification mock returns JSON with `modified_hypothesis`, `modification_type`, `source_hypothesis`, `reasoning`
  - [ ] Existing mock detections still work correctly (no regression)
  - [ ] `python -m pytest tests/` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Planning mock response
    Tool: Bash (python -c)
    Steps:
      1. python -c "import json; from llm.adapter import MockLLMProvider; m = MockLLMProvider(); r = m.complete('Return JSON with strategy_name, method_selection, exploration_weight, reasoning fields'); d = json.loads(r); assert 'strategy_name' in d; assert 'method_selection' in d; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-4-planning-mock.txt

  Scenario: Hypothesis mock response
    Tool: Bash (python -c)
    Steps:
      1. python -c "import json; from llm.adapter import MockLLMProvider; m = MockLLMProvider(); r = m.complete('Return JSON with modified_hypothesis, modification_type, source_hypothesis, reasoning fields'); d = json.loads(r); assert 'modified_hypothesis' in d; assert 'modification_type' in d; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-4-hypothesis-mock.txt

  Scenario: Existing FC-3 mocks not broken
    Tool: Bash (python -c)
    Steps:
      1. python -c "import json; from llm.adapter import MockLLMProvider; m = MockLLMProvider(); r = m.complete('Analyze strengths and weaknesses with `strengths` and `weaknesses`'); d = json.loads(r); assert 'strengths' in d; print('PASS: analysis still works')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-4-fc3-compat.txt
  ```

### Wave 2 — FC-1 Planning + FC-4 Memory Core

- [ ] 5. FC-1: Time-Aware Planning Service

  **What to do**:
  - Enhance `planner/service.py` Planner class:
    - Add `_llm_adapter` optional parameter to `__init__` (default None for backward compat)
    - Add `generate_strategy(context: PlanningContext) -> PlanningStrategy` method that calls LLM with planning_strategy_prompt
    - If `_llm_adapter` is None, use existing heuristic logic (no LLM call)
    - If `_llm_adapter` is provided, call `_llm_adapter.generate_structured(planning_strategy_prompt(...), PlanningStrategy)` and use the result to inform the plan
    - Modify `generate_plan()` to:
      1. Call `generate_strategy()` first if LLM adapter available
      2. Use strategy's `exploration_weight` instead of linear decay when available
      3. Include strategy reasoning in guidance list
    - Update `_iteration_strategy()` in `llm/prompts.py` to be time-aware: use progress ratio from BudgetLedger instead of just iteration count
  - Add `PlannerConfig.use_llm_planning: bool = False` field
  - Write TDD tests:
    - Test Planner without LLM (existing behavior preserved)
    - Test Planner with mock LLM adapter
    - Test generate_strategy returns valid PlanningStrategy
    - Test time-aware planning at different progress levels (0.1, 0.5, 0.9)
  - Create `tests/test_fc1_planning.py`

  **Must NOT do**:
  - Do NOT change `generate_plan()` signature
  - Do NOT break existing Planner(PlannerConfig()) construction
  - Do NOT make LLM calls synchronous blockers — if LLM fails, fall back to heuristic

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T6, T7, T8 — but T7 depends on T6)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11
  - **Blocked By**: T1, T2, T3, T4

  **References**:
  - `planner/service.py:22-131` — Current Planner class
  - `llm/prompts.py:40-56` — Current `_iteration_strategy()`
  - `llm/adapter.py:190-274` — LLMAdapter.generate_structured() interface
  - Paper Appendix E.1: Time-budget tracking, dynamic method selection

  **Acceptance Criteria**:
  - [ ] Planner() without LLM works identically to before
  - [ ] Planner(config, llm_adapter=adapter) uses LLM for strategy
  - [ ] Strategy exploration_weight influences plan's exploration_strength
  - [ ] LLM failure falls back to heuristic (no crash)
  - [ ] Tests cover progress at 0.1, 0.5, 0.9
  - [ ] `python -m pytest tests/test_fc1_planning.py -v` → ALL pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Planner backward compatibility
    Tool: Bash (python -c)
    Steps:
      1. python -c "from planner.service import Planner, PlannerConfig; from data_models import PlanningContext, LoopState, BudgetLedger; p = Planner(PlannerConfig()); ctx = PlanningContext(loop_state=LoopState(loop_id='l1', iteration=1), budget=BudgetLedger(total_time_budget=100.0, elapsed_time=30.0)); plan = p.generate_plan(ctx); assert plan.plan_id; assert 0.0 <= plan.exploration_strength <= 1.0; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-5-planner-compat.txt

  Scenario: LLM-enhanced planning
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/test_fc1_planning.py -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-5-fc1-tests.txt
  ```

- [ ] 6. FC-4: Interaction Kernel (TF-IDF Cosine + Score Delta + Temporal Decay)

  **What to do**:
  - Create `memory_service/interaction_kernel.py` with:
    - `class TFIDFVectorizer`: Pure Python TF-IDF implementation
      - `fit_transform(documents: List[str]) -> List[Dict[str, float]]` — returns sparse TF-IDF vectors as {term: weight} dicts
      - `transform(document: str) -> Dict[str, float]` — transform single doc using fitted vocabulary
      - Uses simple tokenization (split on whitespace + lowercase)
    - `cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float` — cosine between sparse vectors
    - `score_delta(score_a: float, score_b: float) -> float` — normalized score difference
    - `temporal_decay(timestamp_a: float, timestamp_b: float, half_life: float = 3600.0) -> float` — exponential decay based on time difference
    - `class InteractionKernel`:
      - `__init__(alpha: float = 0.4, beta: float = 0.3, gamma: float = 0.3)` — paper's kernel weights
      - `compute(hypothesis_a: HypothesisRecord, hypothesis_b: HypothesisRecord) -> float` — K = α·cosine + β·score_delta + γ·decay
  - Define `HypothesisRecord` dataclass in same file:
    - `text: str`, `score: float`, `timestamp: float`, `branch_id: str`
    - Lightweight data carrier, NOT stored in data_models.py (module-local)
  - Write TDD tests in `tests/test_fc4_interaction_kernel.py`:
    - TF-IDF produces expected weights for simple docs
    - Cosine of identical vectors = 1.0
    - Cosine of orthogonal vectors = 0.0
    - Score delta is normalized
    - Temporal decay approaches 0 for very old timestamps
    - InteractionKernel.compute() returns value in [0, 1]

  **Must NOT do**:
  - Do NOT import numpy, scipy, sklearn, or any external library
  - Do NOT use HypothesisRecord as a general-purpose data model (keep it module-local)
  - Do NOT optimize for large datasets — conservative simple implementation

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5)
  - **Parallel Group**: Wave 2
  - **Blocks**: T7, T8
  - **Blocked By**: T1

  **References**:
  - Paper Appendix E.4: Interaction kernel formula K(hi, hj) = α·cosine(embed(hi), embed(hj)) + β·(score(hi) - score(hj)) + γ·decay(time)
  - Conservative choice: TF-IDF instead of neural embeddings (per user instruction "保守而稳妥")

  **Acceptance Criteria**:
  - [ ] TFIDFVectorizer works with pure Python (no imports)
  - [ ] cosine_similarity returns correct values for known inputs
  - [ ] InteractionKernel.compute() returns float in [0, 1]
  - [ ] Temporal decay is exponential with configurable half_life
  - [ ] All tests in test_fc4_interaction_kernel.py pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: TF-IDF cosine similarity
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.interaction_kernel import TFIDFVectorizer, cosine_similarity; v = TFIDFVectorizer(); vecs = v.fit_transform(['hello world', 'hello world']); sim = cosine_similarity(vecs[0], vecs[1]); assert abs(sim - 1.0) < 0.01; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-6-tfidf-cosine.txt

  Scenario: Interaction kernel range
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord; import time; k = InteractionKernel(); h1 = HypothesisRecord(text='use random forest', score=0.8, timestamp=time.time(), branch_id='b1'); h2 = HypothesisRecord(text='use gradient boosting', score=0.6, timestamp=time.time()-3600, branch_id='b2'); val = k.compute(h1, h2); assert 0.0 <= val <= 1.0; print(f'PASS: kernel={val:.3f}')"
    Expected Result: Prints PASS with kernel value
    Evidence: .sisyphus/evidence/task-6-kernel-range.txt
  ```

- [ ] 7. FC-4: Hypothesis Selector — Algorithm 2 (Select/Modify/Generate)

  **What to do**:
  - Create `memory_service/hypothesis_selector.py` with:
    - `class HypothesisSelector`:
      - `__init__(self, interaction_kernel: InteractionKernel, llm_adapter: Optional[LLMAdapter] = None)`
      - `select_hypothesis(candidates: List[HypothesisRecord], context: str) -> HypothesisRecord` — Select: pick highest-scoring candidate
      - `modify_hypothesis(source: HypothesisRecord, context_items: List[str], task_summary: str, scenario_name: str) -> HypothesisModification` — Modify: use LLM to adapt hypothesis. If no LLM adapter, return source hypothesis unmodified.
      - `generate_hypothesis(context_items: List[str], task_summary: str, scenario_name: str) -> HypothesisModification` — Generate: use LLM to create new hypothesis from context. If no LLM adapter, return empty hypothesis.
      - `adaptive_select(candidates: List[HypothesisRecord], iteration: int, max_iterations: int, context_items: List[str], task_summary: str, scenario_name: str) -> HypothesisModification` — Algorithm 2: early iterations = generate, mid = modify best, late = select best
    - `rank_by_kernel(target: HypothesisRecord, candidates: List[HypothesisRecord], kernel: InteractionKernel) -> List[Tuple[HypothesisRecord, float]]` — rank candidates by kernel similarity to target
  - Paper Algorithm 2 logic (conservative implementation):
    - progress < 0.33 → Generate (create novel hypotheses)
    - 0.33 ≤ progress < 0.66 → Modify (adapt top-scored hypothesis)
    - progress ≥ 0.66 → Select (pick best-scored hypothesis)
  - Write TDD tests in `tests/test_fc4_hypothesis_selector.py`:
    - select_hypothesis picks highest-scored
    - adaptive_select at progress=0.1 generates
    - adaptive_select at progress=0.5 modifies
    - adaptive_select at progress=0.9 selects
    - Works without LLM adapter (graceful degradation)

  **Must NOT do**:
  - Do NOT make LLM calls mandatory — always have fallback
  - Do NOT import from data_models.py (use module-local HypothesisRecord)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T6)
  - **Parallel Group**: Wave 2 (after T6)
  - **Blocks**: T8
  - **Blocked By**: T1, T2, T3, T4, T6

  **References**:
  - `memory_service/interaction_kernel.py` (T6 output) — HypothesisRecord, InteractionKernel
  - `llm/prompts.py` — hypothesis_modification_prompt (T3 output)
  - `llm/schemas.py` — HypothesisModification schema (T2 output)
  - Paper Algorithm 2: Adaptive hypothesis selection

  **Acceptance Criteria**:
  - [ ] select_hypothesis returns highest-scored candidate
  - [ ] adaptive_select switches behavior at 0.33 and 0.66 progress thresholds
  - [ ] Works without LLM adapter (returns sensible defaults)
  - [ ] With MockLLMProvider, modify and generate return valid HypothesisModification
  - [ ] All tests pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Adaptive selection at different stages
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/test_fc4_hypothesis_selector.py -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-7-selector-tests.txt

  Scenario: Select picks highest score
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.hypothesis_selector import HypothesisSelector; from memory_service.interaction_kernel import InteractionKernel, HypothesisRecord; import time; k = InteractionKernel(); sel = HypothesisSelector(k); h1 = HypothesisRecord('hyp1', 0.5, time.time(), 'b1'); h2 = HypothesisRecord('hyp2', 0.9, time.time(), 'b2'); best = sel.select_hypothesis([h1, h2], 'ctx'); assert best.score == 0.9; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-7-select-best.txt
  ```

- [ ] 8. FC-4: Memory Service Extension (Hypothesis Storage + Cross-Branch)

  **What to do**:
  - Extend `memory_service/service.py` MemoryService class:
    - Add new SQLite table `hypotheses` in `_initialize()`:
      ```sql
      CREATE TABLE IF NOT EXISTS hypotheses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          score REAL DEFAULT 0.0,
          branch_id TEXT DEFAULT '',
          timestamp REAL DEFAULT 0.0,
          metadata TEXT DEFAULT '{}',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
      ```
    - Add `write_hypothesis(text: str, score: float, branch_id: str, metadata: Dict[str, str] = None) -> None` — stores hypothesis with current timestamp
    - Add `query_hypotheses(branch_id: Optional[str] = None, limit: int = 10) -> List[HypothesisRecord]` — returns hypotheses, optionally filtered by branch
    - Add `get_cross_branch_hypotheses(exclude_branch: str, limit: int = 10) -> List[HypothesisRecord]` — returns hypotheses from OTHER branches (cross-branch sharing)
    - Modify `query_context()` to optionally include scored hypotheses in `ContextPack.scored_items` when hypotheses exist
    - Add optional `_hypothesis_selector: Optional[HypothesisSelector]` and `_interaction_kernel: Optional[InteractionKernel]` to __init__
    - When hypothesis_selector is available, `query_context` uses interaction kernel to score and rank relevant hypotheses
  - Update `MemoryServiceConfig` with `enable_hypothesis_storage: bool = False` (default False for backward compat)
  - Preserve public API: `write_memory()`, `query_context()`, `get_memory_stats()` signatures unchanged
  - Write TDD tests in `tests/test_fc4_memory.py`:
    - write_hypothesis stores correctly
    - query_hypotheses returns stored hypotheses
    - get_cross_branch_hypotheses excludes current branch
    - query_context backward compatible (no hypotheses → same behavior)
    - query_context with hypotheses → scored_items populated
    - get_memory_stats includes hypothesis count

  **Must NOT do**:
  - Do NOT change write_memory/query_context/get_memory_stats signatures
  - Do NOT break existing failure_cases table functionality
  - Do NOT make hypothesis storage mandatory (controlled by config flag)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T6, T7)
  - **Parallel Group**: Wave 2 (after T6, T7)
  - **Blocks**: T11
  - **Blocked By**: T1, T6, T7

  **References**:
  - `memory_service/service.py:24-145` — Current MemoryService
  - `memory_service/interaction_kernel.py` (T6) — HypothesisRecord, InteractionKernel
  - `memory_service/hypothesis_selector.py` (T7) — HypothesisSelector

  **Acceptance Criteria**:
  - [ ] Hypotheses table created when enable_hypothesis_storage=True
  - [ ] write_hypothesis/query_hypotheses/get_cross_branch_hypotheses work correctly
  - [ ] query_context backward compatible (returns same ContextPack when no hypotheses)
  - [ ] get_memory_stats includes hypothesis_count
  - [ ] Cross-branch query excludes current branch
  - [ ] All tests pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Hypothesis storage round-trip
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.service import MemoryService, MemoryServiceConfig; ms = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True)); ms.write_hypothesis('use XGBoost', 0.8, 'branch-1'); hyps = ms.query_hypotheses(); assert len(hyps) == 1; assert hyps[0].text == 'use XGBoost'; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-8-hypothesis-roundtrip.txt

  Scenario: Cross-branch isolation
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.service import MemoryService, MemoryServiceConfig; ms = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True)); ms.write_hypothesis('hyp-A', 0.7, 'b1'); ms.write_hypothesis('hyp-B', 0.8, 'b2'); cross = ms.get_cross_branch_hypotheses('b1'); assert len(cross) == 1; assert cross[0].branch_id == 'b2'; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-8-cross-branch.txt

  Scenario: Backward compatibility
    Tool: Bash (python -c)
    Steps:
      1. python -c "from memory_service.service import MemoryService, MemoryServiceConfig; ms = MemoryService(MemoryServiceConfig()); ms.write_memory('test item', {'key': 'val'}); cp = ms.query_context({'key': 'val'}); assert len(cp.items) == 1; assert cp.scored_items == []; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-8-backward-compat.txt
  ```

### Wave 3 — FC-5 Coding Workflow + FC-6 Evaluation

- [ ] 9. FC-5: Debug Mode + ExecutionResult Duration Propagation

  **What to do**:
  - Add `debug_mode: bool = False` to `AppConfig` in `app/config.py` (read from `RD_AGENT_DEBUG_MODE` env var)
  - Add `debug_sample_fraction: float = 0.1` to `AppConfig` (read from `RD_AGENT_DEBUG_SAMPLE_FRACTION`)
  - Add `debug_max_epochs: int = 5` to `AppConfig` (read from `RD_AGENT_DEBUG_MAX_EPOCHS`)
  - Update scenario plugins to propagate debug mode config into ScenarioContext.input_payload:
    - In `scenarios/data_science/plugin.py` DataScienceScenarioPlugin.build_context(): if debug config in input_payload, include `debug_mode`, `debug_sample_fraction`, `debug_max_epochs` in context
    - Same for `scenarios/synthetic_research/plugin.py`
  - Update DataScienceRunner.run() in scenarios/data_science/plugin.py:
    - After getting BackendResult, propagate `backend_result.duration_sec` → ExecutionResult.duration_sec
    - Propagate `backend_result.timed_out` → ExecutionResult.timed_out
  - Same for SyntheticResearchRunner.run() in scenarios/synthetic_research/plugin.py
  - Add multi-stage evaluation logic to `evaluation_service/service.py` EvaluationService.evaluate_run():
    - Stage 1: Execution success (exit_code == 0)
    - Stage 2: Competition alignment (artifacts_ref is not empty)
    - Stage 3: Debug compliance (if debug mode, check duration_sec is reasonable)
    - Stage 4: Submission authenticity (basic validation)
    - Combine into a single Score with `details` dict containing stage results
    - Score.value = weighted sum of stage scores
  - Write TDD tests in `tests/test_fc5_debug_mode.py`:
    - Config loads debug mode from env vars
    - ExecutionResult duration_sec propagation
    - Multi-stage evaluation returns stage details
    - evaluate_run with exit_code=0 scores higher than exit_code=1
    - evaluate_run with debug mode checks duration compliance

  **Must NOT do**:
  - Do NOT change Runner Protocol signature in contracts.py
  - Do NOT break existing evaluate_run callers (score still has .value)
  - Do NOT add complex timing logic — simple propagation only
  - Do NOT change ScenarioContext Protocol signature

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T10)
  - **Parallel Group**: Wave 3
  - **Blocks**: T11
  - **Blocked By**: T1

  **References**:
  - `app/config.py:9-28` — AppConfig (frozen=True, new fields need defaults)
  - `core/execution/backend.py:27-38` — BackendResult with duration_sec, timed_out
  - `data_models.py:421-428` — ExecutionResult (extended in T1)
  - `evaluation_service/service.py:27-42` — evaluate_run placeholder
  - `scenarios/data_science/plugin.py` — DataScienceRunner.run()
  - `scenarios/synthetic_research/plugin.py` — SyntheticResearchRunner.run()
  - Paper Appendix E.5: Debug mode, 10% sampling, multi-stage evaluation

  **Acceptance Criteria**:
  - [ ] AppConfig has debug_mode, debug_sample_fraction, debug_max_epochs fields
  - [ ] ExecutionResult.duration_sec populated from BackendResult in both scenario runners
  - [ ] evaluate_run returns Score with stage details in details dict
  - [ ] Debug mode config propagated through scenario context
  - [ ] All tests pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Config loads debug settings
    Tool: Bash (python -c)
    Steps:
      1. python -c "from app.config import load_config; c = load_config({'RD_AGENT_DEBUG_MODE': 'true', 'RD_AGENT_DEBUG_SAMPLE_FRACTION': '0.1'}); assert c.debug_mode == True; assert c.debug_sample_fraction == 0.1; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-9-config-debug.txt

  Scenario: Multi-stage evaluation
    Tool: Bash (python -c)
    Steps:
      1. python -c "from evaluation_service.service import EvaluationService, EvaluationServiceConfig; from data_models import ExecutionResult; es = EvaluationService(EvaluationServiceConfig()); er = ExecutionResult(run_id='r1', exit_code=0, logs_ref='l', artifacts_ref='a', duration_sec=5.0); result = es.evaluate_run(er); assert result.score.value > 0.0; assert 'stages' in result.score.details; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-9-multistage-eval.txt
  ```

- [ ] 10. FC-6: Stratified Splitter + ValidationSelector + Real evaluate_run

  **What to do**:
  - Create `evaluation_service/stratified_splitter.py`:
    - `class StratifiedSplitter`:
      - `__init__(train_ratio: float = 0.9, test_ratio: float = 0.1, seed: int = 42)` — paper 90/10 split
      - `split(data_ids: List[str], labels: Optional[List[str]] = None) -> DataSplitManifest` — if labels provided, do stratified split; otherwise random split
      - Reuse same `_allocate_counts` and `_split_by_stratified` logic pattern from TaskIntakeDataSplitter (but simplified — no val split, just train+test)
    - Pure function, no SQLite dependency
  - Create `evaluation_service/validation_selector.py`:
    - `class ValidationSelector`:
      - `__init__(evaluation_service: EvaluationService)`
      - `rank_candidates(candidates: List[ExecutionResult]) -> List[Tuple[ExecutionResult, Score]]` — evaluate each candidate, return sorted by score descending
      - `select_best(candidates: List[ExecutionResult]) -> Tuple[ExecutionResult, Score]` — return top-ranked candidate
    - Simple and conservative — just sorts by evaluate_run score
  - Implement real scoring in `EvaluationService.evaluate_run()` (enhance T9's multi-stage logic):
    - Score based on exit_code (0 = base score), artifacts presence, duration compliance
    - `aggregate_branch_scores()`: weighted average of scores (not just placeholder 0.0)
    - `get_leaderboard()`: maintain in-memory dict of task_id → {solution_id: score}
  - Update `EvaluationServiceConfig`:
    - Add `train_test_split_ratio: float = 0.9` (default 90/10 per paper)
    - Add `evaluation_seed: int = 42`
  - Write TDD tests in `tests/test_fc6_evaluation.py`:
    - StratifiedSplitter produces correct 90/10 split
    - Stratified split preserves label proportions
    - ValidationSelector ranks by score
    - select_best returns highest scorer
    - aggregate_branch_scores returns weighted average
    - get_leaderboard tracks scores

  **Must NOT do**:
  - Do NOT change evaluate_run/aggregate_branch_scores/get_leaderboard signatures
  - Do NOT import from task_intake_data_splitter (copy the pattern, don't create dependency)
  - Do NOT add complex grading scripts (simple score computation for now)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T9)
  - **Parallel Group**: Wave 3
  - **Blocks**: T11
  - **Blocked By**: T1

  **References**:
  - `task_intake_data_splitter/service.py:314-348` — _split_rows pattern (reuse allocation logic)
  - `task_intake_data_splitter/service.py:367-380` — _allocate_counts (train_count + val_count + test_count)
  - `data_models.py:360-368` — DataSplitManifest(train_ids, val_ids, test_ids, seed)
  - `evaluation_service/service.py:19-74` — Current placeholder EvaluationService
  - Paper Appendix E.6: 90/10 stratified split, ValidationSelector

  **Acceptance Criteria**:
  - [ ] StratifiedSplitter produces ~90/10 train/test split
  - [ ] Stratified split with labels preserves proportions
  - [ ] ValidationSelector.rank_candidates sorts by score descending
  - [ ] ValidationSelector.select_best returns highest scorer
  - [ ] aggregate_branch_scores returns weighted average
  - [ ] get_leaderboard tracks and returns scores
  - [ ] All tests pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 90/10 split ratio
    Tool: Bash (python -c)
    Steps:
      1. python -c "from evaluation_service.stratified_splitter import StratifiedSplitter; from data_models import DataSplitManifest; s = StratifiedSplitter(train_ratio=0.9, test_ratio=0.1); ids = [f'id-{i}' for i in range(100)]; manifest = s.split(ids); assert len(manifest.train_ids) == 90; assert len(manifest.test_ids) == 10; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-10-split-ratio.txt

  Scenario: ValidationSelector ranking
    Tool: Bash (python -c)
    Steps:
      1. python -c "from evaluation_service.validation_selector import ValidationSelector; from evaluation_service.service import EvaluationService, EvaluationServiceConfig; from data_models import ExecutionResult; es = EvaluationService(EvaluationServiceConfig()); vs = ValidationSelector(es); c1 = ExecutionResult(run_id='r1', exit_code=1, logs_ref='l', artifacts_ref='a'); c2 = ExecutionResult(run_id='r2', exit_code=0, logs_ref='l', artifacts_ref='a'); ranked = vs.rank_candidates([c1, c2]); assert ranked[0][0].run_id == 'r2'; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-10-selector-rank.txt

  Scenario: aggregate_branch_scores
    Tool: Bash (python -c)
    Steps:
      1. python -c "from evaluation_service.service import EvaluationService, EvaluationServiceConfig; from data_models import Score; es = EvaluationService(EvaluationServiceConfig()); s1 = Score(score_id='s1', value=0.8, metric_name='m'); s2 = Score(score_id='s2', value=0.6, metric_name='m'); agg = es.aggregate_branch_scores([s1, s2]); assert 0.6 <= agg.value <= 0.8; print(f'PASS: agg={agg.value:.2f}')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-10-aggregate.txt
  ```

### Wave 4 — Integration + Verification

- [ ] 11. Wiring — Config, Runtime, LoopEngine Time Tracking

  **What to do**:
  - Update `app/config.py` `load_config()` to read new env vars:
    - `RD_AGENT_DEBUG_MODE` → debug_mode
    - `RD_AGENT_DEBUG_SAMPLE_FRACTION` → debug_sample_fraction
    - `RD_AGENT_DEBUG_MAX_EPOCHS` → debug_max_epochs
    - `RD_AGENT_HYPOTHESIS_STORAGE` → enable_hypothesis_storage (bool)
    - `RD_AGENT_LLM_PLANNING` → use_llm_planning (bool)
  - Update `app/runtime.py` `build_runtime()`:
    - Pass `llm_adapter` to Planner when `config.use_llm_planning` is True (via PlannerConfig)
    - Pass `enable_hypothesis_storage` to MemoryServiceConfig
    - Create InteractionKernel and HypothesisSelector when hypothesis storage enabled
    - Pass hypothesis_selector and interaction_kernel to MemoryService
  - Update `core/loop/engine.py` LoopEngine.run():
    - Add `import time` at top
    - Wrap each iteration in timing: `t0 = time.monotonic()` before iteration, `elapsed = time.monotonic() - t0` after
    - Update `budget.elapsed_time += elapsed`
    - Append `elapsed` to `budget.iteration_durations`
    - Compute `budget.estimated_remaining` using moving average of last 3 iteration durations × remaining iterations
  - Write TDD tests in `tests/test_fc1456_wiring.py`:
    - build_runtime() succeeds with default config
    - LoopEngine updates elapsed_time after iteration
    - Config loads all new env vars correctly

  **Must NOT do**:
  - Do NOT change LoopEngine.run() signature
  - Do NOT break existing build_runtime/build_run_service callers
  - Do NOT add async time tracking

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all Wave 2+3 tasks)
  - **Blocks**: T12
  - **Blocked By**: T5, T8, T9, T10

  **References**:
  - `app/config.py:53-79` — load_config()
  - `app/runtime.py:65-114` — build_runtime()
  - `core/loop/engine.py:88-226` — LoopEngine.run() main loop

  **Acceptance Criteria**:
  - [ ] build_runtime() succeeds with new config fields
  - [ ] LoopEngine updates budget.elapsed_time per iteration
  - [ ] budget.iteration_durations populated after loop run
  - [ ] Config loads all new env vars
  - [ ] All tests pass
  - [ ] `python -m pytest tests/` → ALL pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Config loads new fields
    Tool: Bash (python -c)
    Steps:
      1. python -c "from app.config import load_config; c = load_config({'RD_AGENT_DEBUG_MODE': 'true', 'RD_AGENT_HYPOTHESIS_STORAGE': 'true', 'RD_AGENT_LLM_PLANNING': 'false'}); assert c.debug_mode == True; print('PASS')"
    Expected Result: Prints PASS
    Evidence: .sisyphus/evidence/task-11-config-new.txt

  Scenario: LoopEngine time tracking
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/test_fc1456_wiring.py -v -k time
    Expected Result: Time tracking tests pass
    Evidence: .sisyphus/evidence/task-11-time-tracking.txt
  ```

- [ ] 12. End-to-End Integration Test — Full Loop with All FCs

  **What to do**:
  - Create `tests/test_fc1456_e2e.py` with comprehensive integration tests:
    - Test 1: Full loop run with FC-1 time-aware planning — verify budget.elapsed_time > 0 after run
    - Test 2: Full loop run with FC-4 memory — write hypotheses, verify cross-branch query works
    - Test 3: Full loop with FC-5 debug mode — verify ExecutionResult has duration_sec
    - Test 4: Full loop with FC-6 evaluation — verify evaluate_run returns non-zero scores
    - Test 5: Combined run — all FCs active, verify no crashes, all interactions work together
    - Test 6: Regression — run with all FCs disabled (default config), verify identical behavior to before
  - Run full regression: `python -m pytest tests/ -v` — all 305+ existing tests plus new ones must pass
  - Verify no import errors across all modules

  **Must NOT do**:
  - Do NOT modify existing test files
  - Do NOT skip or disable any existing tests
  - Do NOT use external services (all tests must work offline with MockLLMProvider)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T11)
  - **Blocks**: T13
  - **Blocked By**: T11

  **References**:
  - `tests/test_e2e_loop.py` — Existing E2E test (follow same pattern)
  - All new modules from T1-T11

  **Acceptance Criteria**:
  - [ ] All E2E tests pass
  - [ ] Full regression (ALL tests) passes
  - [ ] No import errors
  - [ ] `python -m pytest tests/` → 0 failures

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Full regression
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/ -v --tb=short
    Expected Result: ALL tests pass (305+ existing + new)
    Evidence: .sisyphus/evidence/task-12-full-regression.txt

  Scenario: Combined FC run
    Tool: Bash (pytest)
    Steps:
      1. python -m pytest tests/test_fc1456_e2e.py -v
    Expected Result: All E2E tests pass
    Evidence: .sisyphus/evidence/task-12-e2e.txt
  ```

- [ ] 13. Update Gap Analysis Documents

  **What to do**:
  - Update `dev_doc/paper_gap_analysis.md`:
    - FC-1 Planning: Update rating from current gap level to "fully implemented"
    - FC-4 Memory: Update rating to "fully implemented"
    - FC-5 Coding: Update rating to "fully implemented"
    - FC-6 Evaluation: Update rating to "fully implemented"
    - Add implementation notes for each FC
    - Update overall status summary
  - Keep existing FC-2 and FC-3 sections unchanged

  **Must NOT do**:
  - Do NOT rewrite the entire document — patch only FC-1/4/5/6 sections
  - Do NOT change FC-2 or FC-3 descriptions

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Blocks**: None
  - **Blocked By**: T12

  **References**:
  - `dev_doc/paper_gap_analysis.md` — Current gap analysis

  **Acceptance Criteria**:
  - [ ] FC-1, FC-4, FC-5, FC-6 sections updated to reflect implementation
  - [ ] FC-2, FC-3 sections unchanged
  - [ ] Document is internally consistent

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Gap analysis updated
    Tool: Bash (grep)
    Steps:
      1. grep -c "fully implemented" dev_doc/paper_gap_analysis.md
    Expected Result: At least 4 occurrences (one per FC)
    Evidence: .sisyphus/evidence/task-13-gap-update.txt
  ```
