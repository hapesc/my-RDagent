# FC-2 + FC-3: DAG Exploration Path & Scientific Reasoning Pipeline

## TL;DR

> **Quick Summary**: Implement the two highest-impact paper components — FC-2 (DAG-based multi-branch exploration, -28% ablation) and FC-3 (4-stage scientific reasoning pipeline with virtual evaluation, -15% ablation) — transforming the current sequential single-chain loop into a multi-branch DAG explorer with structured scientific reasoning.
> 
> **Deliverables**:
> - FC-3: 4-stage reasoning pipeline (analyze → identify → hypothesize → design) inside ProposalEngine
> - FC-3: Virtual evaluation — generate N=5 candidates, LLM rank, forward top K=2
> - FC-3: New schemas (ReasoningTrace, VirtualEvaluation) and prompt templates
> - FC-2: DAG data model with adjacency list trace structure
> - FC-2: Branch scheduler (MCTS/PUCT-based node selection)
> - FC-2: Multi-branch loop executor in LoopEngine
> - FC-2: Pruning logic (score-based branch elimination)
> - FC-2: Multi-trace merging (LLM-driven synthesis of best traces)
> - Full TDD coverage for all new components
> - Updated design documents
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1 (data models) → T5 (reasoning pipeline) → T9 (multi-branch engine) → T13 (integration test)

---

## Context

### Original Request
Implement FC-2 (Exploration Path) and FC-3 (Reasoning Pipeline) from the RDAgent paper with precise paper reproduction fidelity ("论文精确复现"). These are the two highest-impact components per the paper's ablation study.

### Interview Summary
**Key Discussions**:
- **Scope**: FC-2 + FC-3 only (FC-1/4/5/6 deferred to future phases)
- **Fidelity**: Precise paper reproduction — Algorithm 1 parameters, Appendix E prompt structure
- **Testing**: TDD (RED-GREEN-REFACTOR), currently 123 tests all passing
- **Backward compatibility**: Must NOT break 6 Protocol interface signatures in `plugins/contracts.py`
- **Integration style**: Pragmatic — patch existing modules, don't rewrite from scratch

**Research Findings**:
- **Metis critical finding #1**: Reference implementation (Microsoft RD-Agent) uses `list[tuple[int,...]]` adjacency list for trace DAG, NOT NetworkX — simpler and sufficient
- **Metis critical finding #2**: 4-stage reasoning is structured prompt sections within 1-2 LLM calls, NOT 4 separate API calls — cheaper and preserves context
- **Metis critical finding #3**: "50% pruning" uses MCTS natural selection via PUCT formula, not explicit percentage-based pruning
- **Metis critical finding #4**: asyncio would be risky — entire system is synchronous. Sequential multi-branch execution is safer for this phase
- **Metis critical finding #5**: `ExplorationManager` and `Planner` are intentional stubs (return empty lists/defaults) — designed to be filled
- **Metis recommendation**: FC-3 first (lower risk, self-contained in ProposalEngine), then FC-2 (higher risk, architectural changes to LoopEngine)

### Metis Review
**Identified Gaps** (addressed):
- Gap: No decision on whether N=5/K=2 virtual evaluation follows paper or reference implementation (reference omits it) → **Resolved**: Follow paper ("论文精确复现") — implement N=5/K=2
- Gap: Unclear how DAG interacts with existing `ExplorationGraph` data model → **Resolved**: Extend `ExplorationGraph` with trace adjacency list, keep existing `NodeRecord` structure
- Gap: All-branches-fail edge case not addressed → **Resolved**: Fallback to creating new root nodes (restart exploration)
- Gap: FC-2 without asyncio means sequential branch execution → **Resolved**: Accept sequential for Phase 1, optimize later
- Gap: Unclear how 4-stage reasoning integrates with frozen `ProposalEngine.propose()` signature → **Resolved**: Implement as internal composition — `propose()` signature unchanged, internal logic becomes multi-stage

---

## Work Objectives

### Core Objective
Transform the single-step sequential R&D loop into a multi-branch DAG-based exploration system (FC-2) with structured scientific reasoning (FC-3), matching the paper's Algorithm 1 and Appendix E specifications.

### Concrete Deliverables
- `llm/schemas.py`: New dataclasses — `ReasoningTrace`, `AnalysisResult`, `HypothesisFormulation`, `VirtualEvalResult`
- `llm/prompts.py`: 4 new prompt templates for reasoning stages + virtual evaluation prompt
- `core/reasoning/pipeline.py`: NEW — 4-stage reasoning pipeline orchestrator
- `core/reasoning/virtual_eval.py`: NEW — N=5 candidate generation + LLM ranking + top K=2 selection
- `data_models.py`: Extended `ExplorationGraph` with trace adjacency list, `BranchState` enum, score tracking
- `exploration_manager/service.py`: Full MCTS/PUCT-based node selection replacing stub
- `exploration_manager/scheduler.py`: NEW — trace scheduler with PUCT formula
- `exploration_manager/pruning.py`: NEW — score-based branch pruning logic
- `exploration_manager/merging.py`: NEW — LLM-driven multi-trace merging
- `core/loop/engine.py`: Multi-branch loop execution (sequential branch iteration per loop)
- `scenarios/*/plugin.py`: Updated ProposalEngine implementations using reasoning pipeline
- `dev_doc/paper_gap_analysis.md`: Updated FC-2 and FC-3 gap ratings

### Definition of Done
- [ ] All existing 123 tests still pass (zero regression)
- [ ] All new tests pass (`python -m pytest tests/` → 0 failures)
- [ ] FC-3 reasoning pipeline produces 4-stage structured output from LLM
- [ ] FC-3 virtual evaluation generates N=5 candidates, ranks, forwards K=2
- [ ] FC-2 DAG tracks multiple branches with parent→child edges
- [ ] FC-2 scheduler selects nodes using PUCT exploration/exploitation balance
- [ ] FC-2 pruning eliminates branches below score threshold
- [ ] FC-2 merging combines insights from top traces via LLM
- [ ] No changes to 6 Protocol signatures in `plugins/contracts.py`
- [ ] MockLLMProvider updated to support all new prompt patterns

### Must Have
- 4-stage reasoning pipeline (analyze → identify → hypothesize → design)
- N=5 candidate generation with LLM-based virtual evaluation and K=2 selection
- DAG data model with adjacency list trace structure
- MCTS/PUCT-based node selection scheduler
- Score-based branch pruning
- Multi-trace merging via LLM
- Full backward compatibility with existing plugin contracts
- TDD: tests written before implementation for each component
- MockLLMProvider support for all new stages (deterministic testing)

### Must NOT Have (Guardrails)
- **No NetworkX dependency** — use adjacency list (`list[tuple[int,...]]`) per reference implementation pattern
- **No asyncio/concurrent execution** — keep sequential multi-branch for Phase 1 stability
- **No changes to 6 Protocol signatures** in `plugins/contracts.py` — backward compatibility is non-negotiable
- **No new web frameworks or ORMs**
- **No Docker infrastructure changes**
- **No unused "future extension" code** — every line must serve current FC-2/FC-3 scope
- **No over-abstraction** — each new file has clear single responsibility
- **No RAG integration** — paper showed RAG hurts overall performance (35.1% → 32.0%)
- **No FC-1/FC-4/FC-5/FC-6 implementation** — strictly FC-2 + FC-3 only
- **No embedding/vector DB** — that's FC-4 scope (deferred)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (unittest, 123 tests passing)
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

> FC-3 before FC-2 (lower risk, self-contained). Wave 1-2 = FC-3, Wave 3-4 = FC-2.

```
Wave 1 (Start Immediately — FC-3 foundation + shared data models):
├── Task 1: Extended data models (ReasoningTrace, VirtualEvalResult, DAG extensions) [quick]
├── Task 2: FC-3 reasoning prompt templates (4 stages + virtual eval) [quick]
├── Task 3: FC-3 reasoning schemas (AnalysisResult, HypothesisFormulation, etc.) [quick]
├── Task 4: MockLLMProvider extensions for reasoning stages [quick]

Wave 2 (After Wave 1 — FC-3 core implementation):
├── Task 5: FC-3 reasoning pipeline orchestrator (depends: 1, 2, 3) [deep]
├── Task 6: FC-3 virtual evaluation — N=5 gen + LLM rank + K=2 select (depends: 1, 3, 4) [deep]
├── Task 7: FC-3 integration into scenario ProposalEngines (depends: 5, 6) [unspecified-high]

Wave 3 (After Wave 1 — FC-2 core, can overlap with Wave 2):
├── Task 8: FC-2 trace scheduler — MCTS/PUCT node selection (depends: 1) [deep]
├── Task 9: FC-2 multi-branch loop engine (depends: 1, 8) [deep]
├── Task 10: FC-2 branch pruning logic (depends: 1, 8) [unspecified-high]
├── Task 11: FC-2 multi-trace merging via LLM (depends: 1, 2, 4) [deep]

Wave 4 (After Waves 2+3 — integration + verification):
├── Task 12: FC-2 integration into ExplorationManager + LoopEngine (depends: 8, 9, 10, 11) [deep]
├── Task 13: End-to-end integration test — full loop with FC-2 + FC-3 (depends: 7, 12) [deep]
├── Task 14: Update design documents + gap analysis (depends: 13) [writing]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T5 → T7 → T12 → T13 → F1-F4
Parallel Speedup: ~55% faster than sequential
Max Concurrent: 4 (Waves 1 and 3)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1   | —         | T5, T6, T7, T8, T9, T10, T11, T12 | 1 |
| T2   | —         | T5, T11 | 1 |
| T3   | —         | T5, T6 | 1 |
| T4   | —         | T6, T11 | 1 |
| T5   | T1, T2, T3 | T7 | 2 |
| T6   | T1, T3, T4 | T7 | 2 |
| T7   | T5, T6   | T13 | 2 |
| T8   | T1       | T9, T10, T12 | 3 |
| T9   | T1, T8   | T12 | 3 |
| T10  | T1, T8   | T12 | 3 |
| T11  | T1, T2, T4 | T12 | 3 |
| T12  | T8, T9, T10, T11 | T13 | 4 |
| T13  | T7, T12  | T14 | 4 |
| T14  | T13      | F1-F4 | 4 |

### Agent Dispatch Summary

| Wave | Count | Tasks → Categories |
|------|-------|--------------------|
| 1    | 4     | T1 → `quick`, T2 → `quick`, T3 → `quick`, T4 → `quick` |
| 2    | 3     | T5 → `deep`, T6 → `deep`, T7 → `unspecified-high` |
| 3    | 4     | T8 → `deep`, T9 → `deep`, T10 → `unspecified-high`, T11 → `deep` |
| 4    | 3     | T12 → `deep`, T13 → `deep`, T14 → `writing` |
| FINAL| 4     | F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

### Wave 1 — FC-3 Foundation + Shared Data Models

- [ ] 1. Extended Data Models for FC-2 DAG and FC-3 Reasoning Traces

  **What to do**:
  - Add `BranchState` enum to `data_models.py` with values: `ACTIVE`, `PRUNED`, `MERGED`
  - Add `traces` field (`List[tuple]`) to `ExplorationGraph` dataclass — adjacency list where each tuple is `(parent_node_index, child_node_index)`, matching the reference implementation's `list[tuple[int,...]]` pattern
  - Add `branch_scores` field (`Dict[str, float]`) to `ExplorationGraph` — maps branch_id to cumulative score
  - Add `branch_states` field (`Dict[str, BranchState]`) to `ExplorationGraph` — tracks which branches are active/pruned/merged
  - Add `visit_counts` field (`Dict[str, int]`) to `ExplorationGraph` — tracks per-node visit counts for MCTS/PUCT
  - Add `score` field (`Optional[float]`) to `NodeRecord` dataclass — stores evaluation score for MCTS
  - Add `branch_state` field (`BranchState`) to `NodeRecord` — default `BranchState.ACTIVE`
  - Verify all existing `ExplorationGraph()` construction sites still work (default empty values)
  - Write TDD tests FIRST: test new fields serialize via `model_to_dict()`, test default construction backward-compatible

  **Must NOT do**:
  - Do NOT import NetworkX
  - Do NOT change `ExperimentNode`, `RunSession`, or any Protocol signature
  - Do NOT add methods to `ExplorationGraph` — it stays a plain dataclass (logic lives in scheduler/service)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file dataclass additions with straightforward TDD — no complex logic
  - **Skills**: []
    - No special skills needed — pure Python dataclass work
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed
    - `git-master`: No git operations in this task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: T5, T6, T7, T8, T9, T10, T11, T12
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `data_models.py:50-75` — Existing `ValueEnum` pattern for `BranchState` enum (follow `RunStatus`/`StepState` pattern)
  - `data_models.py:298-322` — Current `ExplorationGraph`, `NodeRecord`, `GraphEdge` definitions (extend, don't replace)
  - `data_models.py:27-40` — `model_to_dict()` function that must handle new fields (already handles Enum, List, Dict)

  **API/Type References**:
  - `data_models.py:43-47` — `ValueEnum(str, Enum)` base class — use for `BranchState`
  - Current `NodeRecord` fields: `node_id`, `parent_ids`, `proposal_id`, `artifact_id`, `score_id` — add `score: Optional[float] = None` and `branch_state: BranchState = BranchState.ACTIVE`

  **External References**:
  - Metis finding: Reference implementation uses `list[tuple[int,...]]` adjacency list — NOT NetworkX

  **WHY Each Reference Matters**:
  - `ValueEnum` pattern: Ensures `BranchState` serializes to string via `model_to_dict()` like all other enums
  - `ExplorationGraph` existing fields: Must add new fields with defaults so `ExplorationGraph()` still works without arguments (backward compatibility)
  - `model_to_dict()`: Already handles `Enum`, `list`, `dict` — verify it handles `tuple` inside list (may need test)

  **Acceptance Criteria**:

  - [ ] `BranchState` enum exists with 3 values: ACTIVE, PRUNED, MERGED
  - [ ] `ExplorationGraph` has `traces`, `branch_scores`, `branch_states`, `visit_counts` fields
  - [ ] `NodeRecord` has `score` and `branch_state` fields
  - [ ] `ExplorationGraph()` with no args still works (backward compatibility)
  - [ ] `model_to_dict(ExplorationGraph(...))` correctly serializes all new fields
  - [ ] `python -m pytest tests/ -v` → ALL tests pass (0 failures)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Backward-compatible default construction
    Tool: Bash (python -c)
    Preconditions: data_models.py has new fields
    Steps:
      1. python -c "from data_models import ExplorationGraph; g = ExplorationGraph(); assert g.traces == []; assert g.branch_scores == {}; assert g.branch_states == {}; assert g.visit_counts == {}; print('PASS: default construction')"
      2. python -c "from data_models import NodeRecord; n = NodeRecord(node_id='n1'); assert n.score is None; print('PASS: NodeRecord default')"
    Expected Result: Both commands print PASS, exit code 0
    Failure Indicators: ImportError, AttributeError, AssertionError
    Evidence: .sisyphus/evidence/task-1-default-construction.txt

  Scenario: BranchState enum serialization
    Tool: Bash (python -c)
    Preconditions: BranchState enum exists
    Steps:
      1. python -c "from data_models import BranchState, ExplorationGraph, model_to_dict; g = ExplorationGraph(branch_states={'b1': BranchState.ACTIVE, 'b2': BranchState.PRUNED}); d = model_to_dict(g); assert d['branch_states'] == {'b1': 'ACTIVE', 'b2': 'PRUNED'}; print('PASS: serialization')"
    Expected Result: Prints PASS, exit code 0
    Failure Indicators: KeyError, assertion failure, BranchState not serialized to string
    Evidence: .sisyphus/evidence/task-1-enum-serialization.txt

  Scenario: Trace adjacency list stores tuples
    Tool: Bash (python -c)
    Preconditions: ExplorationGraph has traces field
    Steps:
      1. python -c "from data_models import ExplorationGraph, model_to_dict; g = ExplorationGraph(traces=[(0,1),(0,2),(1,3)]); d = model_to_dict(g); assert len(d['traces']) == 3; print('PASS: traces')"
    Expected Result: Prints PASS, exit code 0
    Failure Indicators: TypeError if tuples not handled by model_to_dict
    Evidence: .sisyphus/evidence/task-1-traces.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-default-construction.txt
  - [ ] task-1-enum-serialization.txt
  - [ ] task-1-traces.txt

  **Commit**: YES (group: T1)
  - Message: `feat(models): extend data models for FC-2 DAG and FC-3 reasoning traces`
  - Files: `data_models.py`, `tests/test_data_models_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 2. FC-3 Reasoning Prompt Templates (4 Stages + Virtual Evaluation)

  **What to do**:
  - Add 4 new prompt functions to `llm/prompts.py` following the existing `proposal_prompt()` / `feedback_prompt()` pattern:
    1. `reasoning_analysis_prompt(task_summary, scenario_name, iteration, previous_results, current_scores)` — "Analyze the current solution and its performance. Identify strengths and weaknesses."
    2. `reasoning_identify_prompt(analysis_text, task_summary, scenario_name)` — "Based on the analysis, identify the single most critical problem or bottleneck."
    3. `reasoning_hypothesize_prompt(analysis_text, problem_text, task_summary, scenario_name)` — "Formulate a scientific hypothesis about WHY this problem exists and what change would address it."
    4. `reasoning_design_prompt(analysis_text, problem_text, hypothesis_text, task_summary, scenario_name, iteration)` — "Design a concrete, implementable experiment to test this hypothesis."
  - Add `virtual_eval_prompt(candidates, task_summary, scenario_name, evaluation_criteria)` — "Rank these N candidate proposals by expected performance. Return indices of top K."
  - Each prompt must follow paper's Appendix E structured format: role assignment → context → instruction → output fields
  - Use `_iteration_strategy()` where relevant (in analysis and design stages)
  - Write TDD tests FIRST: each prompt function returns non-empty string, contains expected sections

  **Must NOT do**:
  - Do NOT modify existing `proposal_prompt()`, `coding_prompt()`, `feedback_prompt()` functions
  - Do NOT add LLM calling logic — prompts are pure string builders
  - Do NOT hardcode N=5 or K=2 in prompts — those are caller parameters

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding new functions to existing module following established patterns — no architectural changes
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: T5, T11
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `llm/prompts.py:32-69` — `proposal_prompt()` function: Follow this exact pattern (role assignment, ## sections, output fields)
  - `llm/prompts.py:13-29` — `_iteration_strategy()` function: Reuse in analysis and design prompts for iteration-aware guidance
  - `llm/prompts.py:103-139` — `feedback_prompt()` function: Follow the multi-section evaluation pattern for virtual_eval_prompt

  **External References**:
  - Paper Appendix E.3: 4-stage reasoning structure (analyze → identify → hypothesize → design)
  - Paper Appendix E.3: Virtual evaluation prompt instructs LLM to rank candidates by expected improvement

  **WHY Each Reference Matters**:
  - `proposal_prompt()` pattern: Establishes the prompt structure convention (role → sections → output fields). All new prompts must follow this.
  - `_iteration_strategy()`: Provides iteration-aware context that changes reasoning emphasis at different stages
  - `feedback_prompt()`: Shows how to structure evaluation/ranking prompts with scoring criteria

  **Acceptance Criteria**:

  - [ ] 5 new functions exist: `reasoning_analysis_prompt`, `reasoning_identify_prompt`, `reasoning_hypothesize_prompt`, `reasoning_design_prompt`, `virtual_eval_prompt`
  - [ ] Each function returns `str` with role assignment and `## Output Fields` section
  - [ ] `virtual_eval_prompt` accepts list of candidate dicts and returns ranking prompt
  - [ ] Existing `proposal_prompt`, `coding_prompt`, `feedback_prompt` unchanged
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: All 5 prompt functions callable and return structured strings
    Tool: Bash (python -c)
    Preconditions: llm/prompts.py has new functions
    Steps:
      1. python -c "from llm.prompts import reasoning_analysis_prompt, reasoning_identify_prompt, reasoning_hypothesize_prompt, reasoning_design_prompt, virtual_eval_prompt; p1 = reasoning_analysis_prompt('task', 'ds', 0, [], []); assert '## Output Fields' in p1; p5 = virtual_eval_prompt([{'summary':'a'},{'summary':'b'}], 'task', 'ds', 'accuracy'); assert 'rank' in p5.lower() or 'Rank' in p5; print('PASS: all prompts valid')"
    Expected Result: Prints "PASS: all prompts valid", exit 0
    Failure Indicators: ImportError (function not exported), missing ## Output Fields section
    Evidence: .sisyphus/evidence/task-2-prompt-functions.txt

  Scenario: Existing prompts unchanged (regression check)
    Tool: Bash (python -c)
    Preconditions: llm/prompts.py modified
    Steps:
      1. python -c "from llm.prompts import proposal_prompt; p = proposal_prompt('test task', 'ds', 0); assert 'research scientist' in p.lower(); assert '## Output Fields' in p; print('PASS: proposal_prompt unchanged')"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Changed prompt content, missing role assignment
    Evidence: .sisyphus/evidence/task-2-regression.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-prompt-functions.txt
  - [ ] task-2-regression.txt

  **Commit**: YES (group: T2+T3)
  - Message: `feat(llm): add FC-3 reasoning prompt templates and schemas`
  - Files: `llm/prompts.py`, `tests/test_prompts_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 3. FC-3 Reasoning Schemas (AnalysisResult, HypothesisFormulation, VirtualEvalResult)

  **What to do**:
  - Add new dataclasses to `llm/schemas.py` following the existing `ProposalDraft`/`FeedbackDraft` pattern:
    1. `AnalysisResult` — fields: `strengths: List[str]`, `weaknesses: List[str]`, `current_performance: str`, `key_observations: str`
    2. `ProblemIdentification` — fields: `problem: str`, `severity: str`, `evidence: str`, `affected_component: str`
    3. `HypothesisFormulation` — fields: `hypothesis: str`, `mechanism: str`, `expected_improvement: str`, `testable_prediction: str`
    4. `ExperimentDesign` — fields: `summary: str`, `constraints: List[str]`, `virtual_score: float`, `implementation_steps: List[str]`
    5. `VirtualEvalResult` — fields: `rankings: List[int]`, `reasoning: str`, `selected_indices: List[int]`
  - Each dataclass MUST have `from_dict(cls, data)` classmethod (same pattern as `ProposalDraft.from_dict`)
  - Write TDD tests FIRST: test `from_dict` round-trip, test missing fields use defaults

  **Must NOT do**:
  - Do NOT modify existing `ProposalDraft`, `CodeDraft`, `FeedbackDraft`
  - Do NOT add validation logic — schemas are pure data containers
  - Do NOT add methods beyond `from_dict`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding dataclasses following established pattern — mechanical work
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: T5, T6
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `llm/schemas.py:9-21` — `ProposalDraft` with `from_dict()`: Exact pattern to follow for all 5 new schemas
  - `llm/schemas.py:39-55` — `FeedbackDraft` with more fields: Shows how to handle bool + string fields in `from_dict()`

  **API/Type References**:
  - `VirtualEvalResult.rankings` is `List[int]` — indices into the candidates list, sorted by quality (best first)
  - `VirtualEvalResult.selected_indices` is `List[int]` — the top K indices forwarded to coding stage

  **WHY Each Reference Matters**:
  - `ProposalDraft.from_dict()` pattern: All new schemas must follow this exact pattern for `LLMAdapter.generate_structured()` to work (it calls `schema_cls.from_dict(payload)`)
  - `LLMAdapter._build_schema_hint()` at `llm/adapter.py:123-140`: Reads dataclass fields to build JSON schema hints — new schemas must be standard dataclasses

  **Acceptance Criteria**:

  - [ ] 5 new dataclasses: `AnalysisResult`, `ProblemIdentification`, `HypothesisFormulation`, `ExperimentDesign`, `VirtualEvalResult`
  - [ ] Each has `from_dict()` classmethod
  - [ ] `from_dict({})` returns valid default object (no crashes on missing keys)
  - [ ] `LLMAdapter._build_schema_hint(VirtualEvalResult)` returns valid JSON string
  - [ ] Existing schemas unchanged
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: All schemas constructible from empty dict (defaults)
    Tool: Bash (python -c)
    Preconditions: llm/schemas.py has new dataclasses
    Steps:
      1. python -c "from llm.schemas import AnalysisResult, ProblemIdentification, HypothesisFormulation, ExperimentDesign, VirtualEvalResult; a = AnalysisResult.from_dict({}); p = ProblemIdentification.from_dict({}); h = HypothesisFormulation.from_dict({}); e = ExperimentDesign.from_dict({}); v = VirtualEvalResult.from_dict({}); assert isinstance(v.rankings, list); assert isinstance(v.selected_indices, list); print('PASS: all schemas from empty dict')"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: KeyError on missing field, TypeError
    Evidence: .sisyphus/evidence/task-3-empty-dict.txt

  Scenario: VirtualEvalResult round-trip with real data
    Tool: Bash (python -c)
    Preconditions: VirtualEvalResult exists
    Steps:
      1. python -c "from llm.schemas import VirtualEvalResult; v = VirtualEvalResult.from_dict({'rankings': [2,0,4,1,3], 'reasoning': 'Candidate 2 best', 'selected_indices': [2,0]}); assert v.rankings == [2,0,4,1,3]; assert v.selected_indices == [2,0]; assert v.reasoning == 'Candidate 2 best'; print('PASS: round-trip')"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Type conversion errors, wrong values
    Evidence: .sisyphus/evidence/task-3-roundtrip.txt

  Scenario: Schema hint generation works for new types
    Tool: Bash (python -c)
    Preconditions: New schemas + LLMAdapter exist
    Steps:
      1. python -c "from llm.adapter import LLMAdapter, MockLLMProvider; from llm.schemas import VirtualEvalResult; a = LLMAdapter(MockLLMProvider()); hint = a._build_schema_hint(VirtualEvalResult); assert 'rankings' in hint; assert 'selected_indices' in hint; print('PASS: schema hint')"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Missing field in hint, empty string returned
    Evidence: .sisyphus/evidence/task-3-schema-hint.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-empty-dict.txt
  - [ ] task-3-roundtrip.txt
  - [ ] task-3-schema-hint.txt

  **Commit**: YES (group: T2+T3)
  - Message: `feat(llm): add FC-3 reasoning prompt templates and schemas`
  - Files: `llm/schemas.py`, `tests/test_schemas_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 4. MockLLMProvider Extensions for FC-3 Reasoning Stages

  **What to do**:
  - Extend `MockLLMProvider.complete()` in `llm/adapter.py` to detect and respond to FC-3 prompt types:
    1. **Reasoning analysis** detection: check for `"strengths"` or `"weaknesses"` in output fields → return JSON with `AnalysisResult` shape
    2. **Problem identification** detection: check for `"severity"` or `"affected_component"` → return JSON with `ProblemIdentification` shape
    3. **Hypothesis** detection: check for `"mechanism"` or `"testable_prediction"` → return JSON with `HypothesisFormulation` shape
    4. **Experiment design** detection: check for `"implementation_steps"` → return JSON with `ExperimentDesign` shape
    5. **Virtual evaluation** detection: check for `"rankings"` or `"selected_indices"` → return JSON with `VirtualEvalResult` shape (default: rank candidates 0..N-1, select first K)
  - Follow existing detection pattern: `is_proposal = "proposal:" in prompt or "\`virtual_score\`" in prompt`
  - Ensure mock returns are parseable by `LLMAdapter.generate_structured()` → `schema.from_dict()`
  - Write TDD tests FIRST: test each mock detection produces valid JSON for its schema

  **Must NOT do**:
  - Do NOT change existing proposal/coding/feedback mock behavior (backward compatibility)
  - Do NOT add external dependencies
  - Do NOT hardcode specific test expectations in mock (keep generic)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Extending mock with pattern matching — follows established detection pattern
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: T6, T11
  - **Blocked By**: None (can start immediately — but should be aware of T3's new schemas for shapes)

  **References**:

  **Pattern References**:
  - `llm/adapter.py:43-106` — `MockLLMProvider.complete()`: The entire detection + response pattern to extend. Lines 62-64 show detection: `is_proposal = "proposal:" in prompt or "\`virtual_score\`" in prompt`. Lines 66-75 show response generation.
  - `llm/adapter.py:34-41` — `_extract_section()` helper: Use this to extract context from prompts for richer mock responses

  **API/Type References**:
  - T3's new schemas (`AnalysisResult`, `ProblemIdentification`, `HypothesisFormulation`, `ExperimentDesign`, `VirtualEvalResult`): Mock responses must match these field names exactly
  - `LLMAdapter.generate_structured()` at `llm/adapter.py:167-194`: Calls `schema_cls.from_dict(json.loads(raw))` — mock JSON must be parseable

  **WHY Each Reference Matters**:
  - `MockLLMProvider.complete()` detection pattern: New reasoning stages must follow exactly the same if/elif chain — order matters (check more specific patterns first to avoid false matches)
  - `_extract_section()`: Enables mock to echo back context from prompts, making tests more informative

  **Acceptance Criteria**:

  - [ ] MockLLMProvider detects all 5 new prompt types
  - [ ] Each detection returns valid JSON parseable by corresponding schema's `from_dict()`
  - [ ] Existing proposal/coding/feedback detection unchanged
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Mock produces valid AnalysisResult JSON
    Tool: Bash (python -c)
    Preconditions: MockLLMProvider extended, AnalysisResult schema exists
    Steps:
      1. python -c "from llm.adapter import LLMAdapter, MockLLMProvider; from llm.schemas import AnalysisResult; adapter = LLMAdapter(MockLLMProvider()); result = adapter.generate_structured('Analyze... ## Output Fields\n- \`strengths\`: ...', AnalysisResult); assert hasattr(result, 'strengths'); assert hasattr(result, 'weaknesses'); print(f'PASS: {result}')"
    Expected Result: Prints PASS with AnalysisResult object, exit 0
    Failure Indicators: ValueError (parse failed), missing fields
    Evidence: .sisyphus/evidence/task-4-analysis-mock.txt

  Scenario: Mock produces valid VirtualEvalResult with candidate count
    Tool: Bash (python -c)
    Preconditions: MockLLMProvider extended, VirtualEvalResult schema exists
    Steps:
      1. python -c "from llm.adapter import LLMAdapter, MockLLMProvider; from llm.schemas import VirtualEvalResult; adapter = LLMAdapter(MockLLMProvider()); result = adapter.generate_structured('Rank these 5 candidates... ## Output Fields\n- \`rankings\`: ... - \`selected_indices\`: ...', VirtualEvalResult); assert isinstance(result.rankings, list); assert isinstance(result.selected_indices, list); print(f'PASS: rankings={result.rankings}, selected={result.selected_indices}')"
    Expected Result: Prints PASS with list values, exit 0
    Failure Indicators: Empty rankings, type error
    Evidence: .sisyphus/evidence/task-4-virtual-eval-mock.txt

  Scenario: Existing mock behavior preserved (regression)
    Tool: Bash (python -c)
    Preconditions: MockLLMProvider modified
    Steps:
      1. python -c "from llm.adapter import LLMAdapter, MockLLMProvider; from llm.schemas import ProposalDraft; adapter = LLMAdapter(MockLLMProvider()); result = adapter.generate_structured('You are a research scientist...## Task\nmy task\n## Output Fields\n- \`summary\`: ...\n- \`constraints\`: ...\n- \`virtual_score\`: ...', ProposalDraft); assert result.summary != ''; assert isinstance(result.constraints, list); print(f'PASS: proposal still works: {result.summary}')"
    Expected Result: Prints PASS with non-empty summary, exit 0
    Failure Indicators: Wrong schema detected, empty fields
    Evidence: .sisyphus/evidence/task-4-regression.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-analysis-mock.txt
  - [ ] task-4-virtual-eval-mock.txt
  - [ ] task-4-regression.txt

  **Commit**: YES (group: T4)
  - Message: `test(mock): extend MockLLMProvider for FC-3 reasoning stages`
  - Files: `llm/adapter.py`, `tests/test_mock_*.py`
  - Pre-commit: `python -m pytest tests/`

### Wave 2 — FC-3 Core Implementation

- [ ] 5. FC-3 Reasoning Pipeline Orchestrator

  **What to do**:
  - Create NEW file `core/reasoning/__init__.py` (empty, package marker)
  - Create NEW file `core/reasoning/pipeline.py` containing `ReasoningPipeline` class:
    - Constructor: `__init__(self, llm_adapter: LLMAdapter)` — stores adapter reference
    - Main method: `reason(self, task_summary: str, scenario_name: str, iteration: int, previous_results: List[str], current_scores: List[float], model_config: Optional[ModelSelectorConfig] = None) -> ExperimentDesign`
    - Internal flow (4 stages, 1-2 LLM calls per Metis finding):
      1. **Stage 1 — Analysis**: Call `llm_adapter.generate_structured(reasoning_analysis_prompt(...), AnalysisResult, model_config)` → get `AnalysisResult`
      2. **Stage 2 — Problem ID**: Call `llm_adapter.generate_structured(reasoning_identify_prompt(analysis.key_observations, ...), ProblemIdentification, model_config)` → get `ProblemIdentification`
      3. **Stage 3 — Hypothesis**: Call `llm_adapter.generate_structured(reasoning_hypothesize_prompt(analysis.key_observations, problem.problem, ...), HypothesisFormulation, model_config)` → get `HypothesisFormulation`
      4. **Stage 4 — Design**: Call `llm_adapter.generate_structured(reasoning_design_prompt(analysis.key_observations, problem.problem, hypothesis.hypothesis, ...), ExperimentDesign, model_config)` → get `ExperimentDesign`
    - Return the `ExperimentDesign` from stage 4
    - Add `_build_reasoning_trace(self, analysis, problem, hypothesis, design) -> Dict[str, Any]` — assembles all 4 stages into a trace dict for logging/storage
  - Paper specifies stages 1-3 can be ONE combined LLM call with 3 structured output sections, and stage 4 is separate. Implement as 2 calls: stages 1-3 combined → stage 4 separate. BUT for testability, keep the internal 4-stage structure even if stages 1-3 share a single LLM call.
  - **Implementation choice**: Start with 4 separate calls (simpler, more testable). If latency is a concern, combine stages 1-3 into one call in a future optimization. Comment this design decision in code.
  - Write TDD tests FIRST: test pipeline produces ExperimentDesign with non-empty fields using MockLLMProvider

  **Must NOT do**:
  - Do NOT add asyncio — all calls are synchronous
  - Do NOT modify `ProposalEngine` Protocol signature
  - Do NOT store state between calls (pipeline is stateless per invocation)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core orchestrator with multi-stage LLM interaction pattern — needs careful design
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T6, if Wave 1 complete)
  - **Parallel Group**: Wave 2 (with Tasks 6, 7)
  - **Blocks**: T7
  - **Blocked By**: T1 (data models), T2 (prompts), T3 (schemas)

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:89-117` — `DataScienceProposalEngine.propose()`: Shows current single-step LLM call pattern. Pipeline replaces this pattern with 4-stage internal flow.
  - `llm/adapter.py:167-194` — `LLMAdapter.generate_structured()`: The method pipeline calls for each stage. Handles retries + JSON parsing automatically.

  **API/Type References**:
  - T2's prompt functions: `reasoning_analysis_prompt()`, `reasoning_identify_prompt()`, `reasoning_hypothesize_prompt()`, `reasoning_design_prompt()`
  - T3's schemas: `AnalysisResult`, `ProblemIdentification`, `HypothesisFormulation`, `ExperimentDesign`
  - `service_contracts.ModelSelectorConfig`: Optional model config passed through to each LLM call

  **External References**:
  - Paper Appendix E.3: Structured 4-stage reasoning flow
  - Metis finding #2: "4-stage reasoning is structured prompt sections within 1-2 LLM calls, NOT 4 separate API calls"

  **WHY Each Reference Matters**:
  - `DataScienceProposalEngine.propose()`: This is what pipeline REPLACES internally — understanding current flow ensures correct integration
  - `LLMAdapter.generate_structured()`: Pipeline delegates all LLM interaction to this method — no raw API calls

  **Acceptance Criteria**:

  - [ ] `core/reasoning/pipeline.py` exists with `ReasoningPipeline` class
  - [ ] `pipeline.reason()` returns `ExperimentDesign` with non-empty `summary` and `implementation_steps`
  - [ ] Pipeline calls LLM adapter 4 times (one per stage) — verified via MockLLMProvider call counting
  - [ ] `_build_reasoning_trace()` returns dict with keys: `analysis`, `problem`, `hypothesis`, `design`
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Full 4-stage pipeline produces valid ExperimentDesign
    Tool: Bash (python -c)
    Preconditions: core/reasoning/pipeline.py exists, MockLLMProvider extended (T4)
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.pipeline import ReasoningPipeline
adapter = LLMAdapter(MockLLMProvider())
pipeline = ReasoningPipeline(adapter)
result = pipeline.reason('classify images', 'data_science', 0, [], [])
assert result.summary != '', f'Empty summary: {result}'
assert isinstance(result.constraints, list)
assert isinstance(result.implementation_steps, list)
print(f'PASS: {result.summary[:50]}')
"
    Expected Result: Prints PASS with non-empty summary, exit 0
    Failure Indicators: ImportError, empty ExperimentDesign fields, LLM parse error
    Evidence: .sisyphus/evidence/task-5-pipeline-full.txt

  Scenario: Reasoning trace dict has all 4 stages
    Tool: Bash (python -c)
    Preconditions: pipeline exists with _build_reasoning_trace
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.pipeline import ReasoningPipeline
from llm.schemas import AnalysisResult, ProblemIdentification, HypothesisFormulation, ExperimentDesign
pipeline = ReasoningPipeline(LLMAdapter(MockLLMProvider()))
trace = pipeline._build_reasoning_trace(
    AnalysisResult.from_dict({}), ProblemIdentification.from_dict({}),
    HypothesisFormulation.from_dict({}), ExperimentDesign.from_dict({})
)
assert set(trace.keys()) >= {'analysis', 'problem', 'hypothesis', 'design'}
print(f'PASS: trace keys={list(trace.keys())}')
"
    Expected Result: Prints PASS with 4 trace keys, exit 0
    Failure Indicators: Missing keys, AttributeError
    Evidence: .sisyphus/evidence/task-5-trace-dict.txt

  Scenario: Pipeline fails gracefully on LLM error
    Tool: Bash (python -c)
    Preconditions: pipeline exists
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.pipeline import ReasoningPipeline
bad_provider = MockLLMProvider(responses=['not json', 'not json', 'not json'])
adapter = LLMAdapter(bad_provider)
pipeline = ReasoningPipeline(adapter)
try:
    pipeline.reason('task', 'ds', 0, [], [])
    print('FAIL: should have raised')
except ValueError as e:
    print(f'PASS: raised ValueError as expected: {str(e)[:60]}')
"
    Expected Result: Prints PASS with ValueError message, exit 0
    Failure Indicators: Uncaught exception other than ValueError, or no exception raised
    Evidence: .sisyphus/evidence/task-5-error-handling.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-pipeline-full.txt
  - [ ] task-5-trace-dict.txt
  - [ ] task-5-error-handling.txt

  **Commit**: YES (group: T5+T6)
  - Message: `feat(reasoning): implement 4-stage pipeline and virtual evaluation`
  - Files: `core/reasoning/__init__.py`, `core/reasoning/pipeline.py`, `tests/test_reasoning_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 6. FC-3 Virtual Evaluation — N=5 Candidate Generation + LLM Ranking + K=2 Selection

  **What to do**:
  - Create NEW file `core/reasoning/virtual_eval.py` containing `VirtualEvaluator` class:
    - Constructor: `__init__(self, llm_adapter: LLMAdapter, n_candidates: int = 5, k_forward: int = 2)`
    - Main method: `evaluate(self, task_summary: str, scenario_name: str, iteration: int, previous_results: List[str], current_scores: List[float], model_config: Optional[ModelSelectorConfig] = None) -> List[ExperimentDesign]`
    - Internal flow:
      1. Create `ReasoningPipeline` instance (or receive it via constructor)
      2. Call `pipeline.reason()` N times (n_candidates) with slight prompt variation (add candidate index to context)
      3. Collect N `ExperimentDesign` results
      4. Build candidate summary list: `[{"index": i, "summary": design.summary, "virtual_score": design.virtual_score} for i, design in enumerate(designs)]`
      5. Call `llm_adapter.generate_structured(virtual_eval_prompt(candidates, ...), VirtualEvalResult, model_config)` → get ranking
      6. Return top K `ExperimentDesign` objects selected by `VirtualEvalResult.selected_indices`
    - Add `_diversify_prompt(self, base_task: str, candidate_index: int, n_total: int) -> str` — adds diversity instruction: "This is candidate {i+1} of {n}. Explore a DIFFERENT approach from previous candidates."
  - Paper says N=5, K=2 — use as defaults but make configurable
  - Write TDD tests FIRST: test with MockLLMProvider produces K designs, test N < K edge case

  **Must NOT do**:
  - Do NOT use asyncio for parallel candidate generation — sequential for Phase 1
  - Do NOT modify ReasoningPipeline (composition, not inheritance)
  - Do NOT hardcode N=5/K=2 — use constructor parameters

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Multi-candidate generation with LLM ranking — core FC-3 logic requiring careful orchestration
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, after Wave 1)
  - **Parallel Group**: Wave 2 (with Tasks 5, 7)
  - **Blocks**: T7
  - **Blocked By**: T1 (data models), T3 (schemas), T4 (mock provider)

  **References**:

  **Pattern References**:
  - `core/reasoning/pipeline.py` (T5): `ReasoningPipeline.reason()` — VirtualEvaluator calls this N times to generate candidates
  - `llm/adapter.py:167-194` — `LLMAdapter.generate_structured()`: Used for the final ranking LLM call

  **API/Type References**:
  - T2's `virtual_eval_prompt(candidates, task_summary, scenario_name, evaluation_criteria)` — builds ranking prompt
  - T3's `VirtualEvalResult` schema: `rankings: List[int]`, `selected_indices: List[int]`, `reasoning: str`
  - T3's `ExperimentDesign` schema: The return type of each candidate

  **External References**:
  - Paper Section 3 (FC-3): "generate N candidate ideas, evaluate, forward top K"
  - Metis finding #4: "Paper describes N=5/K=2 but reference implementation omits it → we implement it per '论文精确复现'"

  **WHY Each Reference Matters**:
  - `ReasoningPipeline.reason()`: Each candidate is a full 4-stage reasoning output — VirtualEvaluator orchestrates N of these
  - `virtual_eval_prompt()`: The ranking prompt must clearly present all N candidates for LLM comparison

  **Acceptance Criteria**:

  - [ ] `core/reasoning/virtual_eval.py` exists with `VirtualEvaluator` class
  - [ ] `evaluate()` returns exactly K `ExperimentDesign` objects (default K=2)
  - [ ] N candidates generated internally (verified by mock call count: N*4 pipeline calls + 1 ranking call)
  - [ ] Edge case: if N <= K, returns all N candidates without ranking
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Virtual evaluator produces K=2 designs from N=5 candidates
    Tool: Bash (python -c)
    Preconditions: virtual_eval.py exists, pipeline.py exists, MockLLMProvider extended
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.virtual_eval import VirtualEvaluator
adapter = LLMAdapter(MockLLMProvider())
evaluator = VirtualEvaluator(adapter, n_candidates=5, k_forward=2)
results = evaluator.evaluate('classify images', 'data_science', 0, [], [])
assert len(results) == 2, f'Expected 2, got {len(results)}'
for r in results:
    assert r.summary != '', 'Empty summary in selected design'
print(f'PASS: {len(results)} designs selected')
"
    Expected Result: Prints "PASS: 2 designs selected", exit 0
    Failure Indicators: Wrong count, empty designs, LLM parse errors
    Evidence: .sisyphus/evidence/task-6-n5k2.txt

  Scenario: Edge case — N <= K returns all candidates
    Tool: Bash (python -c)
    Preconditions: virtual_eval.py exists
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.virtual_eval import VirtualEvaluator
adapter = LLMAdapter(MockLLMProvider())
evaluator = VirtualEvaluator(adapter, n_candidates=2, k_forward=3)
results = evaluator.evaluate('task', 'ds', 0, [], [])
assert len(results) == 2, f'Expected 2 (N<K), got {len(results)}'
print(f'PASS: edge case handled, {len(results)} returned')
"
    Expected Result: Prints "PASS: edge case handled, 2 returned", exit 0
    Failure Indicators: IndexError, returning more than N candidates
    Evidence: .sisyphus/evidence/task-6-edge-case.txt

  Scenario: Single candidate mode (N=1, K=1) skips ranking
    Tool: Bash (python -c)
    Preconditions: virtual_eval.py exists
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.virtual_eval import VirtualEvaluator
adapter = LLMAdapter(MockLLMProvider())
evaluator = VirtualEvaluator(adapter, n_candidates=1, k_forward=1)
results = evaluator.evaluate('task', 'ds', 0, [], [])
assert len(results) == 1
print(f'PASS: single candidate mode works')
"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Unnecessary ranking call, empty results
    Evidence: .sisyphus/evidence/task-6-single.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-n5k2.txt
  - [ ] task-6-edge-case.txt
  - [ ] task-6-single.txt

  **Commit**: YES (group: T5+T6)
  - Message: `feat(reasoning): implement 4-stage pipeline and virtual evaluation`
  - Files: `core/reasoning/virtual_eval.py`, `tests/test_virtual_eval_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 7. FC-3 Integration into Scenario ProposalEngines

  **What to do**:
  - Modify `DataScienceProposalEngine.propose()` in `scenarios/data_science/plugin.py`:
    1. Add `reasoning_pipeline: Optional[ReasoningPipeline] = None` and `virtual_evaluator: Optional[VirtualEvaluator] = None` to constructor
    2. In `propose()`: if `virtual_evaluator` is not None, call `virtual_evaluator.evaluate()` → get top K designs → pick first → wrap in `Proposal`
    3. Elif `reasoning_pipeline` is not None, call `pipeline.reason()` → get single `ExperimentDesign` → wrap in `Proposal`
    4. Else: fall back to current single-step LLM call (backward compatibility)
    5. Map `ExperimentDesign` → `Proposal`: `Proposal(proposal_id="proposal-fc3", summary=design.summary, constraints=design.constraints, virtual_score=design.virtual_score)`
  - Same changes to `SyntheticResearchProposalEngine.propose()` in `scenarios/synthetic_research/plugin.py`
  - Update `build_data_science_v1_bundle()` and `build_synthetic_research_bundle()` to optionally accept and wire `ReasoningPipeline`/`VirtualEvaluator`
  - **Do NOT change the `ProposalEngine.propose()` Protocol signature** — only internal implementation changes
  - Write TDD tests: test propose() with pipeline produces valid Proposal, test fallback without pipeline still works

  **Must NOT do**:
  - Do NOT change `ProposalEngine` Protocol in `plugins/contracts.py`
  - Do NOT remove `ReasoningService` from synthetic_research (keep as another fallback)
  - Do NOT make pipeline/evaluator required — must be optional for backward compatibility

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Cross-module integration touching 2 scenario plugins + their bundle builders — needs careful backward compatibility
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after T5 and T6)
  - **Blocks**: T13
  - **Blocked By**: T5 (reasoning pipeline), T6 (virtual evaluator)

  **References**:

  **Pattern References**:
  - `scenarios/data_science/plugin.py:85-117` — `DataScienceProposalEngine`: Current single-step propose() to extend with pipeline fallback chain
  - `scenarios/synthetic_research/plugin.py:83-124` — `SyntheticResearchProposalEngine`: Already has `reasoning_service` fallback pattern — extend with pipeline before reasoning_service
  - `scenarios/data_science/plugin.py:277-304` — `build_data_science_v1_bundle()`: Bundle builder to update with optional pipeline/evaluator parameters

  **API/Type References**:
  - `plugins/contracts.py:42-54` — `ProposalEngine.propose()` signature: FROZEN, do not change
  - `data_models.py:334-342` — `Proposal` dataclass: target output type, map `ExperimentDesign` fields to this
  - T5's `ReasoningPipeline.reason()` → returns `ExperimentDesign`
  - T6's `VirtualEvaluator.evaluate()` → returns `List[ExperimentDesign]`

  **WHY Each Reference Matters**:
  - `DataScienceProposalEngine`: This is the PRIMARY integration point — FC-3 reasoning happens inside `propose()` transparently
  - `SyntheticResearchProposalEngine`: Already demonstrates the fallback pattern (reasoning_service → llm_adapter) — extend it to: virtual_evaluator → reasoning_pipeline → reasoning_service → llm_adapter
  - Bundle builders: Must wire pipeline/evaluator into the constructor chain

  **Acceptance Criteria**:

  - [ ] `DataScienceProposalEngine` accepts optional `ReasoningPipeline` and `VirtualEvaluator`
  - [ ] `SyntheticResearchProposalEngine` accepts optional `ReasoningPipeline` and `VirtualEvaluator`
  - [ ] `propose()` returns valid `Proposal` when using pipeline (FC-3 path)
  - [ ] `propose()` returns valid `Proposal` when pipeline is None (backward-compatible path)
  - [ ] Bundle builders accept optional pipeline/evaluator
  - [ ] All existing tests still pass (zero regression)
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: DataScience propose() with VirtualEvaluator produces valid Proposal
    Tool: Bash (python -c)
    Preconditions: T5, T6 complete, scenario plugins updated
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from core.reasoning.pipeline import ReasoningPipeline
from core.reasoning.virtual_eval import VirtualEvaluator
from scenarios.data_science.plugin import DataScienceProposalEngine
from data_models import ContextPack, Plan
from plugins.contracts import ScenarioContext
from service_contracts import StepOverrideConfig
adapter = LLMAdapter(MockLLMProvider())
pipeline = ReasoningPipeline(adapter)
evaluator = VirtualEvaluator(adapter, n_candidates=3, k_forward=1)
engine = DataScienceProposalEngine(adapter, reasoning_pipeline=pipeline, virtual_evaluator=evaluator)
ctx = ScenarioContext(run_id='r1', scenario_name='ds', input_payload={'loop_index': 0}, task_summary='test task')
proposal = engine.propose('test task', ContextPack(), [], Plan(plan_id='p1'), ctx)
assert proposal.summary != '', f'Empty proposal summary'
print(f'PASS: FC-3 proposal: {proposal.summary[:60]}')
"
    Expected Result: Prints PASS with non-empty proposal summary, exit 0
    Failure Indicators: TypeError (wrong constructor args), empty proposal, AttributeError
    Evidence: .sisyphus/evidence/task-7-ds-fc3.txt

  Scenario: Backward compatibility — propose() without pipeline still works
    Tool: Bash (python -c)
    Preconditions: Scenario plugins updated
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from scenarios.data_science.plugin import DataScienceProposalEngine
from data_models import ContextPack, Plan
from plugins.contracts import ScenarioContext
from service_contracts import StepOverrideConfig
adapter = LLMAdapter(MockLLMProvider())
engine = DataScienceProposalEngine(adapter)
ctx = ScenarioContext(run_id='r1', scenario_name='ds', input_payload={'loop_index': 0}, task_summary='test')
proposal = engine.propose('test', ContextPack(), [], Plan(plan_id='p1'), ctx)
assert proposal.summary != ''
print(f'PASS: backward compatible: {proposal.summary[:50]}')
"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: TypeError (required args), changed behavior
    Evidence: .sisyphus/evidence/task-7-backward-compat.txt

  Scenario: Full test suite regression check
    Tool: Bash (python -m pytest)
    Preconditions: All Wave 1+2 changes applied
    Steps:
      1. python -m pytest tests/ -v --tb=short 2>&1 | tail -20
    Expected Result: All tests pass, 0 failures
    Failure Indicators: Any FAILED test, import errors
    Evidence: .sisyphus/evidence/task-7-regression.txt
  ```

  **Evidence to Capture:**
  - [ ] task-7-ds-fc3.txt
  - [ ] task-7-backward-compat.txt
  - [ ] task-7-regression.txt

  **Commit**: YES (group: T7)
  - Message: `feat(scenarios): integrate FC-3 reasoning into ProposalEngines`
  - Files: `scenarios/data_science/plugin.py`, `scenarios/synthetic_research/plugin.py`, `tests/test_scenario_*.py`
  - Pre-commit: `python -m pytest tests/`

### Wave 3 — FC-2 Core Implementation

- [ ] 8. FC-2 Trace Scheduler — MCTS/PUCT Node Selection

  **What to do**:
  - Create NEW file `exploration_manager/scheduler.py` containing `MCTSScheduler` class:
    - Constructor: `__init__(self, exploration_weight: float = 1.41)` — PUCT exploration constant (√2 ≈ 1.41 is standard UCB1)
    - Main method: `select_node(self, graph: ExplorationGraph) -> Optional[str]` — returns node_id of best node to expand
    - PUCT formula implementation:
      ```
      PUCT(node) = Q(node) + c * sqrt(ln(N_parent) / N_node)
      where:
        Q(node) = average score of node's subtree (exploitation)
        c = exploration_weight
        N_parent = visit count of parent (or total visits for root nodes)
        N_node = visit count of this node
      ```
    - Use `graph.visit_counts` for N values, `NodeRecord.score` for Q values
    - Only consider `ACTIVE` nodes (check `NodeRecord.branch_state`)
    - Handle edge cases: no nodes → return None, all nodes pruned → return None, unvisited nodes → prioritize (infinite PUCT)
    - Add `update_visit_count(self, graph: ExplorationGraph, node_id: str) -> ExplorationGraph` — increments visit count after selection
    - Add `get_all_scores(self, graph: ExplorationGraph) -> Dict[str, float]` — returns node_id → PUCT score map for debugging
  - Write TDD tests FIRST: test PUCT prefers unvisited nodes, test PUCT balances exploration/exploitation, test empty graph returns None

  **Must NOT do**:
  - Do NOT import NetworkX — use graph's adjacency list (`traces`) and `nodes` list
  - Do NOT add asyncio
  - Do NOT modify `ExplorationManager` interface yet (that's T12)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: MCTS/PUCT algorithm implementation requires mathematical precision and edge case handling
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T10, T11 after Wave 1)
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11)
  - **Blocks**: T9, T10, T12
  - **Blocked By**: T1 (data models — needs ExplorationGraph extensions)

  **References**:

  **Pattern References**:
  - `exploration_manager/service.py:27-43` — `select_parents()` stub: Returns `[]` — this is the stub that T12 will wire the scheduler into
  - `data_models.py:298-322` — `ExplorationGraph`, `NodeRecord`: The data structures scheduler operates on (after T1 extends them)

  **API/Type References**:
  - T1's extensions: `ExplorationGraph.traces: List[tuple]`, `ExplorationGraph.visit_counts: Dict[str, int]`, `NodeRecord.score: Optional[float]`, `NodeRecord.branch_state: BranchState`
  - `data_models.py:298-303` — `ExplorationGraph.nodes: List[NodeRecord]`, `ExplorationGraph.edges: List[GraphEdge]`

  **External References**:
  - MCTS/UCB1 formula: Standard exploration bonus = c * sqrt(ln(N_parent) / N_child)
  - Paper: Uses PUCT-based selection per Metis finding #3 — "50% pruning uses MCTS natural selection via PUCT formula"

  **WHY Each Reference Matters**:
  - `select_parents()` stub: Understanding its current return type (`List[str]`) ensures scheduler's output is compatible
  - `ExplorationGraph` structure: Scheduler navigates the graph using `nodes`, `edges`, `traces`, `visit_counts` — must understand all fields
  - PUCT formula: Mathematical correctness is critical — wrong formula means wrong exploration/exploitation balance

  **Acceptance Criteria**:

  - [ ] `exploration_manager/scheduler.py` exists with `MCTSScheduler` class
  - [ ] `select_node()` returns node_id string or None
  - [ ] PUCT formula correctly implemented (unvisited nodes get highest priority)
  - [ ] Only ACTIVE nodes considered (PRUNED/MERGED nodes skipped)
  - [ ] Empty graph → returns None
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: PUCT prioritizes unvisited nodes
    Tool: Bash (python -c)
    Preconditions: scheduler.py exists, data_models extended (T1)
    Steps:
      1. python -c "
from data_models import ExplorationGraph, NodeRecord, BranchState
from exploration_manager.scheduler import MCTSScheduler
graph = ExplorationGraph(
    nodes=[
        NodeRecord(node_id='n1', score=0.5, branch_state=BranchState.ACTIVE),
        NodeRecord(node_id='n2', score=None, branch_state=BranchState.ACTIVE),
    ],
    visit_counts={'n1': 5, 'n2': 0}
)
scheduler = MCTSScheduler()
selected = scheduler.select_node(graph)
assert selected == 'n2', f'Expected unvisited n2, got {selected}'
print('PASS: unvisited node prioritized')
"
    Expected Result: Prints PASS, n2 selected, exit 0
    Failure Indicators: n1 selected instead (exploitation over exploration), None returned
    Evidence: .sisyphus/evidence/task-8-unvisited.txt

  Scenario: PUCT skips pruned nodes
    Tool: Bash (python -c)
    Preconditions: scheduler.py exists
    Steps:
      1. python -c "
from data_models import ExplorationGraph, NodeRecord, BranchState
from exploration_manager.scheduler import MCTSScheduler
graph = ExplorationGraph(
    nodes=[
        NodeRecord(node_id='n1', score=0.5, branch_state=BranchState.PRUNED),
        NodeRecord(node_id='n2', score=0.3, branch_state=BranchState.ACTIVE),
    ],
    visit_counts={'n1': 5, 'n2': 3}
)
scheduler = MCTSScheduler()
selected = scheduler.select_node(graph)
assert selected == 'n2', f'Expected n2 (only active), got {selected}'
print('PASS: pruned node skipped')
"
    Expected Result: Prints PASS, n2 selected, exit 0
    Failure Indicators: n1 (pruned) selected, None returned
    Evidence: .sisyphus/evidence/task-8-pruned-skip.txt

  Scenario: Empty graph returns None
    Tool: Bash (python -c)
    Preconditions: scheduler.py exists
    Steps:
      1. python -c "
from data_models import ExplorationGraph
from exploration_manager.scheduler import MCTSScheduler
scheduler = MCTSScheduler()
result = scheduler.select_node(ExplorationGraph())
assert result is None, f'Expected None, got {result}'
print('PASS: empty graph → None')
"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Exception thrown, non-None returned
    Evidence: .sisyphus/evidence/task-8-empty.txt
  ```

  **Evidence to Capture:**
  - [ ] task-8-unvisited.txt
  - [ ] task-8-pruned-skip.txt
  - [ ] task-8-empty.txt

  **Commit**: YES (group: T8+T10)
  - Message: `feat(exploration): MCTS scheduler and branch pruning`
  - Files: `exploration_manager/scheduler.py`, `tests/test_scheduler_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 9. FC-2 Multi-Branch Loop Engine

  **What to do**:
  - Modify `LoopEngine.run()` in `core/loop/engine.py` to support multi-branch execution:
    1. Add `scheduler: Optional[MCTSScheduler] = None` parameter to `LoopEngine.__init__()` (after existing params)
    2. In the main `while` loop, change behavior when scheduler is present:
       - Instead of single linear iteration: `selected_node_id = self._scheduler.select_node(graph)` if scheduler exists
       - If `selected_node_id` is None and graph has nodes → all branches exhausted → break loop
       - If `selected_node_id` is not None → use as parent for next iteration: `parent_ids = [selected_node_id]`
       - After step execution → `self._scheduler.update_visit_count(graph, node.node_id)`
    3. Support multiple branches per loop iteration:
       - Add `branches_per_iteration: int = 1` to `LoopEngineConfig`
       - Inner loop: for each branch in range(branches_per_iteration), select node + execute step + register node
       - This enables exploring multiple branches per outer loop iteration (sequential execution, but multiple branches)
    4. When scheduler is None → maintain current single-chain behavior (100% backward compatible)
  - Keep existing error handling, event recording, and state management intact
  - Write TDD tests FIRST: test multi-branch produces multiple nodes per iteration, test single-branch backward compatible

  **Must NOT do**:
  - Do NOT add asyncio — branches execute sequentially within each loop iteration
  - Do NOT change LoopEngine.run() signature (same parameters)
  - Do NOT remove any existing functionality
  - Do NOT modify StepExecutor or any Protocol implementation

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Modifying core loop orchestrator — most architecturally sensitive change in entire plan
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T8)
  - **Parallel Group**: Wave 3 (after T8)
  - **Blocks**: T12
  - **Blocked By**: T1 (data models), T8 (scheduler)

  **References**:

  **Pattern References**:
  - `core/loop/engine.py:55-142` — `LoopEngine.run()`: ENTIRE current implementation — extend, don't rewrite. The while loop at line 80 is the target for multi-branch insertion.
  - `core/loop/engine.py:80-132` — Current single-chain iteration: planner → select_parents → memory → step_executor → register_node. Multi-branch wraps an inner loop around the step_executor + register_node section.

  **API/Type References**:
  - T8's `MCTSScheduler.select_node(graph) -> Optional[str]`: Returns node_id to expand
  - T8's `MCTSScheduler.update_visit_count(graph, node_id)`: Updates after execution
  - `core/loop/engine.py:26-31` — `LoopEngineConfig`: Add `branches_per_iteration: int = 1`
  - `data_models.py:119-132` — `NodeRecord` construction at engine.py:119: Must work with scheduler-selected parent

  **External References**:
  - Paper Algorithm 1: The main loop selects traces via PUCT, executes, updates scores
  - Metis finding #5: "Sequential multi-branch for Phase 1" — no asyncio, branches execute one-by-one

  **WHY Each Reference Matters**:
  - `LoopEngine.run()` at lines 80-132: This is the EXACT code being modified. Every line must be understood to avoid breaking error handling, event recording, or state transitions.
  - `LoopEngineConfig`: Adding `branches_per_iteration` here ensures backward compatibility (default=1 = current behavior)

  **Acceptance Criteria**:

  - [ ] `LoopEngine.__init__()` accepts optional `scheduler` parameter
  - [ ] `LoopEngineConfig` has `branches_per_iteration` field (default=1)
  - [ ] With scheduler + branches_per_iteration=2: loop produces 2 nodes per outer iteration
  - [ ] Without scheduler: exact same behavior as before (backward compatible)
  - [ ] Error in one branch doesn't kill other branches (graceful per-branch error handling)
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Multi-branch produces multiple nodes per iteration
    Tool: Bash (python -m pytest specific test)
    Preconditions: engine.py modified, scheduler exists
    Steps:
      1. Run the specific multi-branch test that verifies 2 nodes created per loop iteration using MockLLMProvider + MCTSScheduler
    Expected Result: Test passes, graph has 2+ nodes after 1 outer loop
    Failure Indicators: Only 1 node created, scheduler not called
    Evidence: .sisyphus/evidence/task-9-multi-branch.txt

  Scenario: Backward compatibility — no scheduler = same behavior
    Tool: Bash (python -m pytest)
    Preconditions: engine.py modified
    Steps:
      1. python -m pytest tests/test_integration_loop.py -v --tb=short 2>&1 | tail -20
    Expected Result: ALL existing integration tests pass unchanged
    Failure Indicators: Any failure in existing loop tests
    Evidence: .sisyphus/evidence/task-9-backward-compat.txt

  Scenario: All-branches-exhausted graceful exit
    Tool: Bash (python -c)
    Preconditions: engine.py modified, scheduler returns None
    Steps:
      1. Create test where scheduler always returns None → verify loop exits cleanly without error
    Expected Result: Loop returns LoopContext with 0 iterations completed, no exception
    Failure Indicators: Infinite loop, unhandled exception
    Evidence: .sisyphus/evidence/task-9-exhausted.txt
  ```

  **Evidence to Capture:**
  - [ ] task-9-multi-branch.txt
  - [ ] task-9-backward-compat.txt
  - [ ] task-9-exhausted.txt

  **Commit**: YES (group: T9+T11)
  - Message: `feat(loop): multi-branch engine and trace merging`
  - Files: `core/loop/engine.py`, `tests/test_engine_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 10. FC-2 Branch Pruning Logic

  **What to do**:
  - Create NEW file `exploration_manager/pruning.py` containing `BranchPruner` class:
    - Constructor: `__init__(self, score_threshold: Optional[float] = None, relative_threshold: float = 0.5)` — prune branches scoring below 50% of best branch (per paper's MCTS natural selection)
    - Main method: `prune(self, graph: ExplorationGraph) -> ExplorationGraph` — marks underperforming branches as PRUNED
    - Pruning logic:
      1. Collect all ACTIVE branch scores from graph
      2. Find best score among active branches
      3. If `score_threshold` is set (absolute): prune branches below threshold
      4. If `relative_threshold` is set (default 0.5): prune branches scoring below `best_score * relative_threshold`
      5. Set `NodeRecord.branch_state = BranchState.PRUNED` for pruned nodes
      6. Update `graph.branch_states[branch_id] = BranchState.PRUNED`
    - Add `should_prune(self, graph: ExplorationGraph, node_id: str) -> bool` — check single node
    - Edge cases: single branch → never prune, no scores yet → don't prune, all branches below threshold → keep best one
  - Write TDD tests FIRST: test relative pruning, test absolute pruning, test single-branch-safe, test no-score-safe

  **Must NOT do**:
  - Do NOT prune the best branch (always keep at least 1 active)
  - Do NOT modify ExplorationManager yet (that's T12)
  - Do NOT add complex heuristics — keep pruning simple and predictable

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Score-based pruning with edge cases — moderate complexity, not deep algorithmic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T9, T11)
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 11)
  - **Blocks**: T12
  - **Blocked By**: T1 (data models), T8 (scheduler — shares graph structure understanding)

  **References**:

  **Pattern References**:
  - `data_models.py` (after T1): `BranchState.PRUNED` enum value, `ExplorationGraph.branch_states`, `NodeRecord.branch_state`

  **API/Type References**:
  - T1's `ExplorationGraph.branch_scores: Dict[str, float]` — source of branch quality data
  - T1's `BranchState` enum: `ACTIVE`, `PRUNED`, `MERGED` — pruner sets PRUNED

  **External References**:
  - Paper: "50% pruning" — Metis corrected: MCTS natural selection via PUCT, not explicit 50% cut
  - Default relative_threshold=0.5 matches paper's "bottom 50% pruned" interpretation

  **WHY Each Reference Matters**:
  - `BranchState.PRUNED`: Pruner's primary output — sets this state on underperforming branches
  - `branch_scores`: The data source pruner uses to rank branches — must be populated by T12 integration

  **Acceptance Criteria**:

  - [ ] `exploration_manager/pruning.py` exists with `BranchPruner` class
  - [ ] Relative pruning: branches below 50% of best score get PRUNED
  - [ ] Single branch never pruned (safety)
  - [ ] No scores → no pruning (safety)
  - [ ] At least 1 branch always remains ACTIVE
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Relative pruning removes weak branches
    Tool: Bash (python -c)
    Preconditions: pruning.py exists, data_models extended (T1)
    Steps:
      1. python -c "
from data_models import ExplorationGraph, NodeRecord, BranchState
from exploration_manager.pruning import BranchPruner
graph = ExplorationGraph(
    nodes=[
        NodeRecord(node_id='n1', score=0.9, branch_state=BranchState.ACTIVE),
        NodeRecord(node_id='n2', score=0.3, branch_state=BranchState.ACTIVE),
        NodeRecord(node_id='n3', score=0.6, branch_state=BranchState.ACTIVE),
    ],
    branch_scores={'b1': 0.9, 'b2': 0.3, 'b3': 0.6}
)
pruner = BranchPruner(relative_threshold=0.5)
result = pruner.prune(graph)
active = [n for n in result.nodes if n.branch_state == BranchState.ACTIVE]
pruned = [n for n in result.nodes if n.branch_state == BranchState.PRUNED]
assert len(pruned) >= 1, f'Expected at least 1 pruned, got {len(pruned)}'
assert any(n.node_id == 'n1' for n in active), 'Best node n1 should remain active'
print(f'PASS: {len(active)} active, {len(pruned)} pruned')
"
    Expected Result: Prints PASS with n2 pruned (0.3 < 0.9*0.5=0.45), n1 and n3 active
    Failure Indicators: Best branch pruned, no pruning happened
    Evidence: .sisyphus/evidence/task-10-relative-pruning.txt

  Scenario: Single branch never pruned
    Tool: Bash (python -c)
    Preconditions: pruning.py exists
    Steps:
      1. python -c "
from data_models import ExplorationGraph, NodeRecord, BranchState
from exploration_manager.pruning import BranchPruner
graph = ExplorationGraph(
    nodes=[NodeRecord(node_id='n1', score=0.1, branch_state=BranchState.ACTIVE)],
    branch_scores={'b1': 0.1}
)
pruner = BranchPruner(relative_threshold=0.5)
result = pruner.prune(graph)
assert result.nodes[0].branch_state == BranchState.ACTIVE, 'Single branch must stay active'
print('PASS: single branch preserved')
"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: Single branch got pruned
    Evidence: .sisyphus/evidence/task-10-single-safe.txt
  ```

  **Evidence to Capture:**
  - [ ] task-10-relative-pruning.txt
  - [ ] task-10-single-safe.txt

  **Commit**: YES (group: T8+T10)
  - Message: `feat(exploration): MCTS scheduler and branch pruning`
  - Files: `exploration_manager/pruning.py`, `tests/test_pruning_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 11. FC-2 Multi-Trace Merging via LLM

  **What to do**:
  - Create NEW file `exploration_manager/merging.py` containing `TraceMerger` class:
    - Constructor: `__init__(self, llm_adapter: LLMAdapter)`
    - Main method: `merge(self, traces: List[Dict[str, Any]], task_summary: str, scenario_name: str, model_config: Optional[ModelSelectorConfig] = None) -> ExperimentDesign`
    - Internal flow:
      1. Format each trace as a summary string: extract key learnings, scores, approaches from each trace dict
      2. Build merge prompt: present all trace summaries, ask LLM to synthesize the best elements into ONE unified experiment design
      3. Call `llm_adapter.generate_structured(merge_prompt, ExperimentDesign, model_config)` → merged design
      4. Return the merged `ExperimentDesign`
    - Add `_build_merge_prompt(self, trace_summaries: List[str], task_summary: str, scenario_name: str) -> str` — constructs the LLM prompt
    - Merge prompt structure: "You have N completed research traces. Synthesize the best findings into one final experiment design. Each trace explored: [summaries]. Combine strengths, avoid weaknesses."
  - Add `merge_traces_prompt()` function to `llm/prompts.py` following existing prompt pattern
  - Write TDD tests FIRST: test merge produces valid ExperimentDesign, test single trace returns it unchanged, test empty traces raises

  **Must NOT do**:
  - Do NOT implement embedding similarity — that's FC-4 scope
  - Do NOT add complex trace analysis — keep merging simple: format + LLM call
  - Do NOT modify existing prompts

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: LLM-driven synthesis requires careful prompt construction and multi-trace handling
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T8, T9, T10)
  - **Parallel Group**: Wave 3 (with Tasks 8, 9, 10)
  - **Blocks**: T12
  - **Blocked By**: T1 (data models), T2 (prompts — for merge prompt pattern), T4 (mock — for testing)

  **References**:

  **Pattern References**:
  - `llm/prompts.py:32-69` — `proposal_prompt()`: Follow this pattern for `merge_traces_prompt()` — role → context → instruction → output fields
  - `scenarios/data_science/plugin.py:89-117` — Single LLM call pattern: merger follows same generate_structured() call pattern

  **API/Type References**:
  - `llm/adapter.py:167-194` — `LLMAdapter.generate_structured()`: The merger's single LLM interaction
  - T3's `ExperimentDesign` schema: Output type of merge operation
  - T5's `ReasoningPipeline._build_reasoning_trace()` output dict: Input format for merger (traces are dicts with analysis/problem/hypothesis/design keys)

  **External References**:
  - Paper: "multi-trace merging combines insights from successful branches"
  - Paper uses LLM to synthesize — not algorithmic merging

  **WHY Each Reference Matters**:
  - `proposal_prompt()` pattern: merge prompt must follow same structure for consistency
  - `_build_reasoning_trace()` output: This is what merger receives as input — must understand the dict structure

  **Acceptance Criteria**:

  - [ ] `exploration_manager/merging.py` exists with `TraceMerger` class
  - [ ] `merge_traces_prompt()` added to `llm/prompts.py`
  - [ ] `merge()` returns valid `ExperimentDesign` with non-empty summary
  - [ ] Single trace → returns design based on that trace (no LLM call for merge)
  - [ ] Empty traces → raises ValueError
  - [ ] `python -m pytest tests/ -v` → ALL tests pass

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Merge 3 traces produces unified ExperimentDesign
    Tool: Bash (python -c)
    Preconditions: merging.py exists, MockLLMProvider extended
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from exploration_manager.merging import TraceMerger
adapter = LLMAdapter(MockLLMProvider())
merger = TraceMerger(adapter)
traces = [
    {'analysis': 'good feature eng', 'problem': 'overfitting', 'hypothesis': 'regularize', 'design': 'add L2'},
    {'analysis': 'fast convergence', 'problem': 'low recall', 'hypothesis': 'class weights', 'design': 'weighted loss'},
    {'analysis': 'stable training', 'problem': 'poor generalization', 'hypothesis': 'data augment', 'design': 'add noise'},
]
result = merger.merge(traces, 'classify images', 'data_science')
assert result.summary != '', f'Empty merged summary'
print(f'PASS: merged design: {result.summary[:60]}')
"
    Expected Result: Prints PASS with non-empty merged design, exit 0
    Failure Indicators: LLM parse error, empty result, TypeError
    Evidence: .sisyphus/evidence/task-11-merge-3.txt

  Scenario: Empty traces raises ValueError
    Tool: Bash (python -c)
    Preconditions: merging.py exists
    Steps:
      1. python -c "
from llm.adapter import LLMAdapter, MockLLMProvider
from exploration_manager.merging import TraceMerger
merger = TraceMerger(LLMAdapter(MockLLMProvider()))
try:
    merger.merge([], 'task', 'ds')
    print('FAIL: should have raised ValueError')
except ValueError:
    print('PASS: ValueError raised for empty traces')
"
    Expected Result: Prints PASS, exit 0
    Failure Indicators: No exception raised, wrong exception type
    Evidence: .sisyphus/evidence/task-11-empty-error.txt
  ```

  **Evidence to Capture:**
  - [ ] task-11-merge-3.txt
  - [ ] task-11-empty-error.txt

  **Commit**: YES (group: T9+T11)
  - Message: `feat(loop): multi-branch engine and trace merging`
  - Files: `exploration_manager/merging.py`, `llm/prompts.py` (merge prompt), `tests/test_merging_*.py`
  - Pre-commit: `python -m pytest tests/`

### Wave 4 — Integration Wiring + End-to-End + Documentation

- [ ] 12. FC-2 Integration Wiring — Wire Scheduler, Pruner, Merger into ExplorationManager + LoopEngine

  **What to do**:
  - Modify `exploration_manager/service.py` to replace stubs with real FC-2 logic:
    - Add imports: `MCTSScheduler` (T8), `BranchPruner` (T10), `TraceMerger` (T11)
    - Update `ExplorationManagerConfig`: add `mcts_exploration_weight: float = 1.41` (√2, PUCT standard), `prune_relative_threshold: float = 0.5`, `merge_enabled: bool = True`
    - Update `ExplorationManager.__init__()`: accept `scheduler: MCTSScheduler`, `pruner: BranchPruner`, `merger: TraceMerger`, `llm_adapter: LLMAdapter` as constructor args. Store as `self._scheduler`, `self._pruner`, `self._merger`, `self._llm_adapter`
    - Replace `select_parents()` stub: Call `self._scheduler.select_node(graph)` → return `[selected_node_id]`. If scheduler returns None (empty graph), return `[]` (first iteration behavior).
    - Replace `get_frontier()` stub: Return `[n.node_id for n in graph.nodes if n.branch_state == BranchState.ACTIVE]` — active nodes matching criteria
    - Add NEW method `prune_branches(self, graph: ExplorationGraph) -> ExplorationGraph`: Call `self._pruner.prune(graph)` → return pruned graph. Log how many branches were pruned.
    - Add NEW method `merge_traces(self, graph: ExplorationGraph, task_summary: str, scenario_name: str) -> ExperimentDesign`: Extract traces from completed branches (branch_state == COMPLETED or MERGED), call `self._merger.merge(traces, task_summary, scenario_name)` → return merged design.
  - Modify `core/loop/engine.py` `LoopEngine.run()` to support multi-branch iteration:
    - After each iteration's `register_node()` call (line 130), add: `graph = self._exploration_manager.prune_branches(graph)` — prune after every node registration
    - After the while loop exits (line 135), add merge step: if `len([n for n in graph.nodes if n.branch_state in (BranchState.ACTIVE, BranchState.COMPLETED)]) > 1`, call `merged_design = self._exploration_manager.merge_traces(graph, task_summary, run_session.scenario_name)` and store in `loop_context.merged_result`
    - Add `merged_result: Optional[ExperimentDesign] = None` field to `LoopContext` dataclass in `data_models.py`
    - Keep backward compatibility: if `ExplorationManager` receives None for scheduler/pruner/merger, fall back to original stub behavior (no-op). This is critical for existing tests.
  - Modify `app/runtime.py` `build_runtime()` to instantiate FC-2 components:
    - Import `MCTSScheduler`, `BranchPruner`, `TraceMerger`
    - Create instances: `scheduler = MCTSScheduler(exploration_weight=config.mcts_exploration_weight)`, `pruner = BranchPruner(relative_threshold=config.prune_threshold)`, `merger = TraceMerger(llm_adapter)`
    - Pass to `ExplorationManager(config, scheduler=scheduler, pruner=pruner, merger=merger, llm_adapter=llm_adapter)`
    - Add new config fields to `AppConfig` in `app/config.py`: `mcts_exploration_weight: float`, `prune_threshold: float` with env var mapping `RD_AGENT_MCTS_WEIGHT`, `RD_AGENT_PRUNE_THRESHOLD`
  - Write TDD tests:
    - Test `select_parents()` delegates to scheduler and returns node ID
    - Test `prune_branches()` delegates to pruner
    - Test `merge_traces()` delegates to merger
    - Test backward compat: `ExplorationManager` with None components returns [] / graph unchanged
    - Test `LoopEngine.run()` calls prune after registration (mock verification)

  **Must NOT do**:
  - Do NOT change `select_parents()` or `get_frontier()` method SIGNATURES — only change the implementation body
  - Do NOT add asyncio for multi-branch execution
  - Do NOT break existing 123 tests — backward compat via None defaults is critical
  - Do NOT modify `plugins/contracts.py` Protocol signatures

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Cross-module wiring touching 4+ files, requires careful backward compatibility management and understanding of the full data flow
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction
    - `git-master`: No git operations needed

  **Parallelization**:
  - **Can Run In Parallel**: NO — depends on all Wave 3 outputs
  - **Parallel Group**: Wave 4 (sequential start, then T13 depends on T12)
  - **Blocks**: T13
  - **Blocked By**: T8 (scheduler), T9 (multi-branch engine), T10 (pruner), T11 (merger)

  **References**:

  **Pattern References**:
  - `exploration_manager/service.py:19-78` — Current stub implementation. ALL 3 methods (select_parents, register_node, get_frontier) need body replacement while preserving signatures.
  - `app/runtime.py:61-100` — `build_runtime()`: Current assembly pattern. Add scheduler/pruner/merger instantiation following existing pattern (config → instance → wire).
  - `core/loop/engine.py:80-142` — `LoopEngine.run()` while loop: Insert prune call at line 131 (after register_node), merge call after while loop exits (after line 134).

  **API/Type References**:
  - T8's `MCTSScheduler.select_node(graph: ExplorationGraph) -> Optional[str]` — Returns node_id or None
  - T10's `BranchPruner.prune(graph: ExplorationGraph) -> ExplorationGraph` — Returns graph with updated branch states
  - T11's `TraceMerger.merge(traces, task_summary, scenario_name) -> ExperimentDesign` — Returns merged design
  - `data_models.py:BranchState` enum (from T1): ACTIVE, PRUNED, COMPLETED, MERGED
  - `data_models.py:LoopContext` — Add `merged_result` field here

  **External References**:
  - Paper Algorithm 1: Loop structure with explore → evaluate → prune → merge cycle
  - Metis finding #5: "Keep sequential multi-branch — no asyncio for Phase 1"

  **WHY Each Reference Matters**:
  - `service.py` stubs: These are the EXACT methods being replaced — executor must understand current signatures and docstrings to preserve them
  - `runtime.py` assembly: Follow the exact instantiation pattern (config → constructor → wire) to maintain code style consistency
  - `engine.py` while loop: Insertion points must be precise to maintain existing flow

  **Acceptance Criteria**:

  - [ ] `ExplorationManager.select_parents()` returns node_id from MCTSScheduler (not empty list)
  - [ ] `ExplorationManager.get_frontier()` returns active node IDs from graph
  - [ ] `ExplorationManager.prune_branches()` delegates to BranchPruner
  - [ ] `ExplorationManager.merge_traces()` delegates to TraceMerger
  - [ ] `LoopEngine.run()` calls prune_branches after register_node
  - [ ] `LoopEngine.run()` calls merge_traces after loop completes (if >1 branch)
  - [ ] `app/runtime.py` instantiates MCTSScheduler, BranchPruner, TraceMerger
  - [ ] Backward compat: ExplorationManager with None components still works (123 tests pass)
  - [ ] `python -m pytest tests/ -v` → ALL tests pass (existing 123 + new wiring tests)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: ExplorationManager delegates select_parents to MCTSScheduler
    Tool: Bash (python -c)
    Preconditions: exploration_manager/service.py updated, scheduler.py exists (T8)
    Steps:
      1. python -c "
  from data_models import ExplorationGraph, NodeRecord, BranchState
  from exploration_manager.scheduler import MCTSScheduler
  from exploration_manager.pruning import BranchPruner
  from exploration_manager.merging import TraceMerger
  from exploration_manager.service import ExplorationManager, ExplorationManagerConfig
  from llm.adapter import LLMAdapter, MockLLMProvider
  scheduler = MCTSScheduler(exploration_weight=1.41)
  pruner = BranchPruner(relative_threshold=0.5)
  merger = TraceMerger(LLMAdapter(MockLLMProvider()))
  em = ExplorationManager(
      ExplorationManagerConfig(),
      scheduler=scheduler, pruner=pruner, merger=merger,
      llm_adapter=LLMAdapter(MockLLMProvider())
  )
  graph = ExplorationGraph(
      nodes=[
          NodeRecord(node_id='n1', score=0.8, branch_state=BranchState.ACTIVE, visit_count=3),
          NodeRecord(node_id='n2', score=0.5, branch_state=BranchState.ACTIVE, visit_count=1),
      ]
  )
  from data_models import Plan
  result = em.select_parents(graph, Plan())
  assert len(result) == 1, f'Expected 1 parent, got {len(result)}'
  assert result[0] in ('n1', 'n2'), f'Unexpected parent: {result[0]}'
  print(f'PASS: selected parent={result[0]}')
  "
    Expected Result: Prints PASS with a valid node_id (likely n2 due to PUCT favoring less-visited), exit 0
    Failure Indicators: Empty list returned (stub behavior), KeyError, scheduler not wired
    Evidence: .sisyphus/evidence/task-12-select-parents.txt

  Scenario: Backward compatibility — None components preserve stub behavior
    Tool: Bash (python -c)
    Preconditions: exploration_manager/service.py updated with None defaults
    Steps:
      1. python -c "
  from data_models import ExplorationGraph, Plan
  from exploration_manager.service import ExplorationManager, ExplorationManagerConfig
  em = ExplorationManager(ExplorationManagerConfig())
  graph = ExplorationGraph()
  result = em.select_parents(graph, Plan())
  assert result == [], f'Expected empty list, got {result}'
  pruned = em.prune_branches(graph)
  assert pruned.nodes == graph.nodes, 'Prune with None pruner should be no-op'
  print('PASS: backward compat preserved')
  "
    Expected Result: Prints PASS, exit 0. Old behavior unchanged.
    Failure Indicators: TypeError (None not callable), AttributeError
    Evidence: .sisyphus/evidence/task-12-backward-compat.txt

  Scenario: LoopEngine.run() prunes after each iteration
    Tool: Bash (python -c)
    Preconditions: engine.py updated, all FC-2 components wired
    Steps:
      1. python -c "
  # Verify prune_branches is called by checking graph state after run
  # This is a structural verification using mock counting
  from unittest.mock import MagicMock, patch
  from core.loop.engine import LoopEngine, LoopEngineConfig
  from data_models import RunSession, StopConditions, RunStatus
  engine = LoopEngine(
      config=LoopEngineConfig(),
      planner=MagicMock(),
      exploration_manager=MagicMock(),
      memory_service=MagicMock(),
      step_executor=MagicMock(),
      run_store=MagicMock(),
      event_store=MagicMock(),
  )
  # Setup mocks
  engine._planner.generate_plan.return_value = MagicMock()
  engine._exploration_manager.select_parents.return_value = []
  engine._exploration_manager.register_node.return_value = MagicMock(nodes=[])
  engine._exploration_manager.prune_branches.return_value = MagicMock(nodes=[])
  step_result = MagicMock()
  step_result.experiment.node_id = 'n1'
  step_result.experiment.parent_node_id = None
  step_result.proposal.proposal_id = 'p1'
  step_result.artifact_id = 'a1'
  step_result.score.score_id = 's1'
  engine._step_executor.execute_iteration.return_value = step_result
  engine._memory_service.query_context.return_value = {}
  session = RunSession(run_id='test', scenario_name='ds', stop_conditions=StopConditions(max_loops=2))
  engine.run(session, 'test task')
  prune_calls = engine._exploration_manager.prune_branches.call_count
  assert prune_calls == 2, f'Expected 2 prune calls (one per iteration), got {prune_calls}'
  print(f'PASS: prune_branches called {prune_calls} times')
  "
    Expected Result: Prints PASS with 2 prune calls, exit 0
    Failure Indicators: 0 prune calls (not wired), wrong call count
    Evidence: .sisyphus/evidence/task-12-engine-prune.txt
  ```

  **Evidence to Capture:**
  - [ ] task-12-select-parents.txt
  - [ ] task-12-backward-compat.txt
  - [ ] task-12-engine-prune.txt

  **Commit**: YES
  - Message: `feat(integration): wire FC-2 DAG into exploration manager and loop`
  - Files: `exploration_manager/service.py`, `core/loop/engine.py`, `app/runtime.py`, `app/config.py`, `data_models.py`, `tests/test_integration_wiring_*.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 13. End-to-End Integration Test — FC-2 + FC-3 Full Loop Verification

  **What to do**:
  - Create NEW test file `tests/test_e2e_fc2_fc3.py` — comprehensive integration test exercising FC-2 and FC-3 together through the full loop:
    - Test class `TestFC2FC3Integration`:
      - `test_full_loop_with_reasoning_and_branches()`:
        1. Build full runtime using `MockLLMProvider` (extended by T4) — NOT real LLM
        2. Create `RunSession` with `max_loops=3` and `scenario_name='data_science'`
        3. Build `RunService` using `build_run_service()` pattern from `app/runtime.py`
        4. Call `loop_engine.run(session, 'classify iris dataset', max_loops=3)`
        5. Verify: graph has ≥ 2 nodes registered (multi-iteration creates nodes)
        6. Verify: at least one node has `reasoning_trace` dict with keys `analysis`, `problem`, `hypothesis`, `design` (FC-3 trace from ReasoningPipeline)
        7. Verify: `prune_branches` was called (FC-2 pruning active)
        8. Verify: loop completed without errors (status == COMPLETED)
      - `test_virtual_eval_produces_multiple_candidates()`:
        1. Create `VirtualEvaluator(adapter, n_candidates=3, k_forward=2)` with MockLLMProvider
        2. Call `evaluate('classify images', 'data_science', 0, [], [])`
        3. Verify: returns exactly 2 `ExperimentDesign` objects
        4. Verify: each has non-empty `summary`
      - `test_mcts_selection_with_multiple_nodes()`:
        1. Create `ExplorationGraph` with 5 nodes (various scores + visit counts)
        2. Create `MCTSScheduler` and call `select_node()` multiple times
        3. Verify: selection is not always the same node (PUCT explores)
        4. Verify: high-score + low-visit nodes are favored
      - `test_prune_then_merge_pipeline()`:
        1. Create graph with 4 nodes: 2 high-score active, 2 low-score active
        2. `BranchPruner.prune(graph)` → verify 2 pruned, 2 active
        3. `TraceMerger.merge(active_traces, ...)` → verify merged `ExperimentDesign`
        4. Verify: end-to-end data flow from graph → prune → merge → design
      - `test_backward_compat_all_existing_tests_pass()`:
        1. This is a meta-test: simply run `python -m pytest tests/ -k "not e2e"` programmatically
        2. Verify exit code 0 and zero failures
  - The test uses MockLLMProvider throughout — NO real LLM calls. This ensures deterministic, fast tests.
  - Test file should be self-contained: import from all FC-2 and FC-3 modules to verify they wire together.

  **Must NOT do**:
  - Do NOT make real LLM API calls in this test
  - Do NOT modify existing test files — create new test file only
  - Do NOT test individual components (those are unit tests in T1-T12) — focus on INTEGRATION between components
  - Do NOT add slow tests (each test < 5 seconds with MockLLMProvider)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Integration testing requires understanding of the full system data flow and correct mock setup across multiple modules
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: NO — needs T12 wiring complete
  - **Parallel Group**: Wave 4 (sequential: T12 → T13 → T14)
  - **Blocks**: T14
  - **Blocked By**: T7 (scenario integration), T12 (wiring)

  **References**:

  **Pattern References**:
  - `tests/test_integration_loop.py` — Existing integration test pattern: how RunSession is created, how MockLLMProvider is configured, how assertions verify loop execution. Follow this pattern but extend for FC-2+FC-3.
  - `app/runtime.py:103-132` — `build_run_service()`: Shows how to assemble a full RunService with LoopEngine + StepExecutor. E2E test should mirror this assembly.

  **API/Type References**:
  - T5's `ReasoningPipeline.reason()` → `ExperimentDesign` — FC-3 output
  - T6's `VirtualEvaluator.evaluate()` → `List[ExperimentDesign]` — FC-3 multi-candidate
  - T8's `MCTSScheduler.select_node()` → `Optional[str]` — FC-2 selection
  - T10's `BranchPruner.prune()` → `ExplorationGraph` — FC-2 pruning
  - T11's `TraceMerger.merge()` → `ExperimentDesign` — FC-2 merging
  - T12's wired `ExplorationManager` and `LoopEngine` — integration targets

  **Test References**:
  - `tests/test_integration_loop.py` — Existing loop integration test structure. Follow same mock setup and assertion patterns.
  - `tests/test_costeer.py` — CoSTEER test pattern (multi-round within one iteration)

  **External References**:
  - Paper Algorithm 1: Full loop flow — plan → select branch → propose (FC-3) → code → evaluate → prune → merge

  **WHY Each Reference Matters**:
  - `test_integration_loop.py`: Proves the pattern for mocking the full loop; E2E test extends this with FC-2+FC-3 modules
  - `build_run_service()`: The E2E test must mirror production assembly to be a valid integration test

  **Acceptance Criteria**:

  - [ ] `tests/test_e2e_fc2_fc3.py` exists with ≥ 4 test methods
  - [ ] `test_full_loop_with_reasoning_and_branches` verifies multi-node graph + reasoning traces + pruning
  - [ ] `test_virtual_eval_produces_multiple_candidates` verifies N=3 → K=2 selection
  - [ ] `test_prune_then_merge_pipeline` verifies prune → merge data flow
  - [ ] All tests use MockLLMProvider (no real API calls)
  - [ ] `python -m pytest tests/test_e2e_fc2_fc3.py -v` → ALL pass
  - [ ] `python -m pytest tests/ -v` → ALL pass (zero regression)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: E2E test suite passes with all FC-2 + FC-3 modules wired
    Tool: Bash (python -m pytest)
    Preconditions: All T1-T12 tasks completed and committed
    Steps:
      1. python -m pytest tests/test_e2e_fc2_fc3.py -v --tb=short 2>&1 | tee output.txt
      2. grep -c "PASSED" output.txt
      3. grep -c "FAILED" output.txt
    Expected Result: ≥ 4 PASSED, 0 FAILED, exit 0
    Failure Indicators: Any FAILED test, ImportError (missing module), AttributeError (missing method)
    Evidence: .sisyphus/evidence/task-13-e2e-results.txt

  Scenario: Full test suite regression check — all 123+ tests still pass
    Tool: Bash (python -m pytest)
    Preconditions: E2E tests added, no existing tests modified
    Steps:
      1. python -m pytest tests/ -v --tb=short 2>&1 | tee output.txt
      2. Check that total passed count >= 123 (original) + new tests
      3. Check 0 failures
    Expected Result: 123+ existing tests + N new tests all PASS, 0 failures
    Failure Indicators: Any existing test FAILS (regression), count < 123
    Evidence: .sisyphus/evidence/task-13-full-regression.txt

  Scenario: E2E tests complete in < 30 seconds (no real LLM calls)
    Tool: Bash (python -m pytest)
    Preconditions: MockLLMProvider used throughout
    Steps:
      1. time python -m pytest tests/test_e2e_fc2_fc3.py -v 2>&1 | tee output.txt
      2. Extract elapsed time from pytest output
    Expected Result: Total time < 30 seconds
    Failure Indicators: > 30 seconds (likely real LLM calls or infinite loops)
    Evidence: .sisyphus/evidence/task-13-timing.txt
  ```

  **Evidence to Capture:**
  - [ ] task-13-e2e-results.txt
  - [ ] task-13-full-regression.txt
  - [ ] task-13-timing.txt

  **Commit**: YES
  - Message: `test(e2e): end-to-end integration test for FC-2 + FC-3 full loop`
  - Files: `tests/test_e2e_fc2_fc3.py`
  - Pre-commit: `python -m pytest tests/`

- [ ] 14. Documentation Updates — Paper Gap Analysis + Design Docs

  **What to do**:
  - Update `dev_doc/paper_gap_analysis.md`:
    - FC-2 section (line ~103): Change `### Gap Rating: **CRITICAL**` → `### Gap Rating: **SIGNIFICANT**`
    - Update FC-2 Evidence section: Add "Implemented: MCTS/PUCT scheduler, branch pruning, trace merging. Remaining: async parallel execution (Phase 2), advanced pruning heuristics"
    - FC-3 section (line ~153): Change `### Gap Rating: **MAJOR**` → `### Gap Rating: **MINOR**`
    - Update FC-3 Evidence section: Add "Implemented: 4-stage reasoning pipeline, virtual evaluation (N=5, K=2), integrated into both ProposalEngines. Remaining: prompt tuning with real data"
    - Add a "Implementation Status" subsection under each updated FC with date and branch reference
  - Update `dev_doc/reverse_engineered_architecture.md`:
    - Add `core/reasoning/` module description under the appropriate section
    - Add `exploration_manager/scheduler.py`, `exploration_manager/pruning.py`, `exploration_manager/merging.py` descriptions
    - Update the ExplorationManager section to reflect real implementation (no longer a stub)
  - Add NEW ADR `dev_doc/adr/006-mcts-puct-over-networkx.md`:
    - Title: "Use MCTS/PUCT with adjacency list over NetworkX DAG"
    - Context: Paper uses MCTS natural selection (PUCT formula), reference implementation uses simple adjacency list, not NetworkX
    - Decision: Follow reference implementation pattern — adjacency list `list[tuple[int,...]]` + PUCT formula for node selection
    - Consequences: Simpler dependency footprint, no graph library needed, PUCT provides principled exploration/exploitation balance
    - Status: Accepted
    - Follow format of existing ADRs in `dev_doc/adr/`
  - Write TDD tests: N/A (documentation task)

  **Must NOT do**:
  - Do NOT rewrite entire gap analysis — only update FC-2 and FC-3 sections
  - Do NOT change other FC ratings (FC-1, FC-4, FC-5, FC-6 untouched)
  - Do NOT add implementation details to docs (that's in the code) — keep at architecture level
  - Do NOT create a new architecture doc — patch existing one

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Pure documentation task — updating existing markdown files and creating ADR
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction
    - `git-master`: No git operations

  **Parallelization**:
  - **Can Run In Parallel**: NO — needs T13 to confirm implementation is correct before documenting
  - **Parallel Group**: Wave 4 (sequential: T12 → T13 → T14)
  - **Blocks**: F1-F4 (Final Verification)
  - **Blocked By**: T13 (E2E test confirms implementation is correct)

  **References**:

  **Pattern References**:
  - `dev_doc/paper_gap_analysis.md:60-115` — FC-1 and FC-2 sections: Shows the exact structure (Paper Vision → Current State → Gap Rating → Evidence → Impact) to update
  - `dev_doc/adr/001-sqlite-for-mvp.md` — Existing ADR format: Title, Status, Context, Decision, Consequences. Follow this exactly.
  - `dev_doc/reverse_engineered_architecture.md` — Module descriptions pattern. Add new modules following existing description style.

  **API/Type References**:
  - T8's `MCTSScheduler` → describe in architecture doc
  - T5's `ReasoningPipeline` → describe in architecture doc
  - T6's `VirtualEvaluator` → describe in architecture doc

  **External References**:
  - Paper Section 3: FC-2 and FC-3 descriptions for accurate gap rating updates

  **WHY Each Reference Matters**:
  - `paper_gap_analysis.md` format: MUST follow exact same section structure so the document remains consistent
  - ADR format: Existing ADRs set the convention — new ADR must match

  **Acceptance Criteria**:

  - [ ] `dev_doc/paper_gap_analysis.md` FC-2 rating changed from CRITICAL to SIGNIFICANT
  - [ ] `dev_doc/paper_gap_analysis.md` FC-3 rating changed from MAJOR to MINOR
  - [ ] Both FC sections have updated Evidence with "Implemented: ..." summary
  - [ ] `dev_doc/reverse_engineered_architecture.md` includes `core/reasoning/` and new `exploration_manager/` files
  - [ ] `dev_doc/adr/006-mcts-puct-over-networkx.md` exists with correct ADR format
  - [ ] No other FC ratings changed (FC-1, FC-4, FC-5, FC-6 unchanged)
  - [ ] Document formatting consistent with existing style

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Gap analysis ratings updated correctly
    Tool: Bash (grep)
    Preconditions: dev_doc/paper_gap_analysis.md updated
    Steps:
      1. grep -n "Gap Rating" dev_doc/paper_gap_analysis.md
      2. Verify FC-2 line shows SIGNIFICANT (was CRITICAL)
      3. Verify FC-3 line shows MINOR (was MAJOR)
      4. Verify FC-1 still shows MAJOR (unchanged)
      5. Verify FC-4 still shows MAJOR (unchanged)
      6. Verify FC-5 still shows SIGNIFICANT (unchanged)
      7. Verify FC-6 still shows SIGNIFICANT (unchanged)
    Expected Result: FC-2=SIGNIFICANT, FC-3=MINOR, all others unchanged
    Failure Indicators: Wrong rating, missing section, other FCs accidentally changed
    Evidence: .sisyphus/evidence/task-14-ratings.txt

  Scenario: ADR 006 exists and follows format
    Tool: Bash (cat + grep)
    Preconditions: dev_doc/adr/006-mcts-puct-over-networkx.md created
    Steps:
      1. cat dev_doc/adr/006-mcts-puct-over-networkx.md
      2. Verify contains: Title, Status (Accepted), Context, Decision, Consequences
      3. Verify mentions PUCT formula and adjacency list
      4. Verify does NOT mention NetworkX as chosen solution
    Expected Result: ADR exists with all required sections, references PUCT + adjacency list
    Failure Indicators: Missing file, missing sections, mentions NetworkX as the chosen approach
    Evidence: .sisyphus/evidence/task-14-adr.txt

  Scenario: Architecture doc includes new modules
    Tool: Bash (grep)
    Preconditions: reverse_engineered_architecture.md updated
    Steps:
      1. grep -c "ReasoningPipeline\|core/reasoning" dev_doc/reverse_engineered_architecture.md
      2. grep -c "MCTSScheduler\|scheduler.py" dev_doc/reverse_engineered_architecture.md
      3. grep -c "BranchPruner\|pruning.py" dev_doc/reverse_engineered_architecture.md
      4. grep -c "TraceMerger\|merging.py" dev_doc/reverse_engineered_architecture.md
    Expected Result: Each grep returns ≥ 1 match (all new modules documented)
    Failure Indicators: Any grep returns 0 (module not documented)
    Evidence: .sisyphus/evidence/task-14-arch-doc.txt
  ```

  **Evidence to Capture:**
  - [ ] task-14-ratings.txt
  - [ ] task-14-adr.txt
  - [ ] task-14-arch-doc.txt

  **Commit**: YES
  - Message: `docs: update gap analysis and design docs for FC-2 + FC-3 implementation`
  - Files: `dev_doc/paper_gap_analysis.md`, `dev_doc/reverse_engineered_architecture.md`, `dev_doc/adr/006-mcts-puct-over-networkx.md`
  - Pre-commit: —

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run test command). For each "Must NOT Have": search codebase for forbidden patterns (NetworkX import, asyncio import in core/, changed Protocol signatures). Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/` + check for: `as any`/type ignores, empty catches, console.log/print in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify all new files have docstrings and clear single responsibility.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (FC-3 reasoning feeds into FC-2 branches). Test edge cases: empty graph, all branches fail, single iteration. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Group | Message | Files | Pre-commit |
|-------|---------|-------|------------|
| T1 | `feat(models): extend data models for FC-2 DAG and FC-3 reasoning traces` | `data_models.py`, `tests/test_data_models_*.py` | `python -m pytest tests/` |
| T2+T3 | `feat(llm): add FC-3 reasoning prompt templates and schemas` | `llm/prompts.py`, `llm/schemas.py`, `tests/test_prompts_*.py`, `tests/test_schemas_*.py` | `python -m pytest tests/` |
| T4 | `test(mock): extend MockLLMProvider for FC-3 reasoning stages` | `llm/adapter.py`, `tests/test_mock_*.py` | `python -m pytest tests/` |
| T5+T6 | `feat(reasoning): implement 4-stage pipeline and virtual evaluation` | `core/reasoning/`, `tests/test_reasoning_*.py` | `python -m pytest tests/` |
| T7 | `feat(scenarios): integrate FC-3 reasoning into ProposalEngines` | `scenarios/*/plugin.py`, `tests/test_scenario_*.py` | `python -m pytest tests/` |
| T8+T10 | `feat(exploration): MCTS scheduler and branch pruning` | `exploration_manager/`, `tests/test_exploration_*.py` | `python -m pytest tests/` |
| T9+T11 | `feat(loop): multi-branch engine and trace merging` | `core/loop/engine.py`, `exploration_manager/merging.py`, `tests/test_engine_*.py` | `python -m pytest tests/` |
| T12 | `feat(integration): wire FC-2 DAG into exploration manager and loop` | `exploration_manager/service.py`, `core/loop/engine.py`, `app/runtime.py`, `app/config.py`, `data_models.py`, `tests/test_integration_wiring_*.py` | `python -m pytest tests/` |
| T13 | `test(e2e): end-to-end integration test for FC-2 + FC-3 full loop` | `tests/test_integration_*.py` | `python -m pytest tests/` |
| T14 | `docs: update gap analysis and design docs for FC-2 + FC-3 implementation` | `dev_doc/*.md` | — |

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -v  # Expected: ALL pass (123 existing + N new), 0 failures
python -c "from core.reasoning.pipeline import ReasoningPipeline; print('FC-3 import OK')"
python -c "from exploration_manager.scheduler import MCTSScheduler; print('FC-2 scheduler OK')"
python -c "from exploration_manager.merging import TraceMerger; print('FC-2 merger OK')"
python -c "from data_models import ExplorationGraph; g = ExplorationGraph(); print(f'traces: {g.traces}')"
```

### Final Checklist
- [ ] All "Must Have" features present and tested
- [ ] All "Must NOT Have" guardrails verified (no NetworkX, no asyncio, no Protocol changes)
- [ ] All 123 existing tests still pass (zero regression)
- [ ] New test count ≥ 40 (covering all FC-2 and FC-3 components)
- [ ] No `# TODO` or `# FIXME` left without ticket reference
- [ ] `dev_doc/paper_gap_analysis.md` updated with new ratings
