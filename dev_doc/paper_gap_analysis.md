# RDAgent Paper Gap Analysis: 6 Framework Components

**Date**: 2026-03-07  
**Base Commit**: `6a12d592428d2f7e743923949225cdb1eb6729e6`  
**Purpose**: Compare the original RDAgent paper's 6 Framework Components against the current my-RDagent implementation to identify capability gaps and prioritize development efforts.

---

## Methodology & Caveats

### Rating Methodology
This gap analysis is based on:
- Close reading of the RDAgent paper (33 pages, including Algorithm 1, Framework Component definitions, Appendix E prompts, and ablation studies)
- Line-by-line code review of the current my-RDagent implementation
- Subjective assessment by the project maintainer

**Important limitations:**
- **Ablation data applicability**: The paper's ablation study was conducted on their complete system. Our implementation differs significantly in architecture and completeness. Ablation impact percentages from the paper are provided for reference but may not directly translate to our system.
- **Snapshot in time**: File paths and implementation details are accurate as of commit `6a12d592`. Future refactoring may change these references.
- **Design choices vs capability gaps**: This document focuses on capability gaps (missing functionality that blocks paper's vision) rather than different design choices (alternative implementations that achieve similar goals).

---

## Severity Rating Definitions

- **CRITICAL**: Paper's core capability completely missing. Expected largest performance impact (paper's ablation shows >20% drop). Blocks implementing the paper's full vision.
- **MAJOR**: Significant capability gap with partial workarounds but limited effectiveness. Paper's ablation shows 10-20% drop, or capability is foundational for other FCs.
- **SIGNIFICANT**: Capability exists but incomplete, needs enhancement. Paper's ablation shows <10% drop or not tested separately. Has clear implementation path.
- **MINOR**: Detail difference with limited impact on core functionality. Nice-to-have but not blocking.

---

## FC-1: Planning (Dynamic Time-Aware Strategy)

### Paper Vision

The paper's FC-1 Planning implements dynamic time-aware strategy that adapts as the research competition progresses:

- **Early stage** (little time elapsed): Limited budget, encourage novelty, exploratory methods
- **Later stage** (approaching deadline): Allow expensive methods (ensembles, cross-validation)
- **Adaptive tradeoff**: Manages exploration/exploitation balance over time
- **Cost awareness**: Tracks computational budget and adjusts method selection accordingly

The paper's prompt (Appendix E.1) explicitly references "time budget" and "elapsed time" to guide the LLM's planning decisions.

### Current State — **Partial Implementation**

Time-aware planning with basic budget tracking, but missing core algorithm:

- **Location**: `planner/service.py` (176 lines), `app/config.py`
- **Capability**: Partial time-aware planning infrastructure
- **Implemented**:
   - Time-based stage classification: early (<0.33), mid (0.33-0.66), late (>0.66)
   - `BudgetLedger` tracks `elapsed_time`, `iteration_durations`, `estimated_remaining`
   - `LoopEngine` measures wall-clock time per iteration
   - Config-driven enablement: `RD_AGENT_LLM_PLANNING` env var
   - Moving average of last 3 iterations for estimated remaining time

### Gap Rating: **SIGNIFICANT** (Remaining: Algorithm 1 time budget loop, method cost estimation, strategy switching)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T5 (planning service), T11 (LoopEngine time tracking + wiring)
- **Tests**: 19+ tests covering time-aware planning, strategy generation, budget tracking, config wiring

**Evidence**:
- Partial: Basic time tracking exists, but lacks Algorithm 1 integration
- Missing: Dynamic method cost estimation for different approaches
- Missing: Automatic strategy switching based on progress and deadline

**Impact**:
- Time budget is tracked but not actively used to adjust method selection
- Cannot adapt exploration intensity based on time remaining
- Requires manual tuning rather than automatic deadline-aware adaptation

---

## FC-2: Exploration Path Structuring (Adaptive DAG-Based Exploration)

### Paper Vision

FC-2 is the paper's most impactful component (28% performance drop when removed):

- **Adaptive DAG**: Directed acyclic graph with multiple parallel branches
- **Layer-0 diversity**: First layer maximizes solution diversity (different initial approaches)
- **Within-branch exploitation**: Greedily exploit best paths within each branch
- **Pruning**: Remove sub-optimal branches to focus compute
- **Multi-trace merging**: Final stage merges insights from multiple successful paths

The paper's prompt (Appendix E.2) instructs the LLM to maintain a "trace tree" and select parent nodes for branching.

### Current State — **Fully Implemented**

Paper-faithful adaptive exploration is now implemented in the current architecture:

- **Location**: `exploration_manager/scheduler.py`, `exploration_manager/service.py`, `core/loop/engine.py`, `app/runtime.py`
- **Capability**: MCTS/PUCT-guided sequential DAG exploration with backpropagation, branch pruning, trace merging, and Layer-0 diversity
- **Implementation**:
  - **PUCT scheduler** with node-level `visits`, `total_value`, `avg_value`
  - **Reward integration** via `RewardCalculator` (`score_based` and `decision_based`)
  - **Backpropagation** from expanded child to all ancestors through `parent_ids`
  - **Layer-0 diversity** through `VirtualEvaluator` + `generate_diverse_roots()`
  - **Branch pruning** via `BranchPruner`
  - **Trace merging** via `TraceMerger`
  - **LoopEngine integration**: `observe_feedback()` replaces legacy visit-count bumping and feeds real execution scores back into MCTS

**Architecture**: Branches still execute sequentially in one worker, but the paper-critical search structure is present: multiple root candidates, branch expansion, reward-based backprop, pruning, and merge-ready traces.

### Gap Rating: **MINOR** (Remaining: async multi-worker execution, more advanced pruning heuristics)

**Evidence**:
- Ablation study shows **-28% performance** when removed (largest impact of all 6 FCs)
- Implemented: PUCT selection, reward calculation, backpropagation, and node statistics in `exploration_manager/scheduler.py`
- Implemented: graph edges, tree traversal helpers, `observe_feedback()`, and `generate_diverse_roots()` in `exploration_manager/service.py`
- Implemented: LoopEngine MCTS flow integration in `core/loop/engine.py`
- Implemented: runtime/config wiring for `c_puct`, reward mode, Layer-0 candidate count, and top-K forwarding in `app/runtime.py` and `app/config.py`
- Verified by unit, integration, and E2E tests including backpropagation and Layer-0 diverse roots

**Impact**:
- Core DAG-based multi-branch exploration now functional (sequential execution)
- PUCT formula balances exploration/exploitation per paper's Algorithm 1
- Branch pruning filters low-scoring paths; trace merging synthesizes best ideas
- Parallel execution across branches deferred to Phase 2 (currently sequential)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-08
- **Tasks**: T1, T3, T5, T9, T10, T11, T12, T13
- **Tests**: scheduler, exploration manager, engine integration, runtime wiring, and E2E coverage for backpropagation / Layer-0 diversity

---

## FC-3: Reasoning Pipeline (Scientific Multi-Step Reasoning)

### Paper Vision

FC-3 implements structured scientific reasoning with virtual evaluation:

**4-step reasoning pipeline**:
1. **Analyze**: Understand current solution and its performance
2. **Identify problem**: Find the critical bottleneck or failure mode
3. **Formulate hypothesis**: Reason about WHY the method works/fails
4. **Output idea**: Generate implementable improvement

**Virtual evaluation**:
- Generate N candidate ideas (e.g., N=5)
- LLM evaluates each candidate's promise
- Forward only the top K ideas to the expensive coding stage
- Filters out low-quality ideas before compute investment

The paper's prompt (Appendix E.3) structures this as a multi-turn dialogue with the LLM.

### Current State — **Fully Implemented**

Structured scientific reasoning is now implemented end-to-end:

- **Location**: `core/reasoning/pipeline.py`, `core/reasoning/virtual_eval.py`, `core/loop/costeer.py`, `llm/prompts.py`, `llm/schemas.py`
- **Capability**: 4-stage reasoning, virtual evaluation, reasoning trace persistence, structured feedback, and knowledge self-generation
- **Implementation**:
  - **4-stage reasoning pipeline**: Analyze -> Identify -> Hypothesize -> Design
  - **Virtual evaluation**: generate N candidates and forward top K to coding
  - **Trace persistence**: `ReasoningTrace` stored through injected `trace_store`
  - **Structured feedback**: CoSTEER asks the LLM for execution / return-checking / code-quality feedback
  - **Knowledge self-generation**: successful CoSTEER rounds distill reusable knowledge into `MemoryService.write_memory(...)`
  - **Scenario integration**: both proposal engines use the upgraded reasoning path

### Gap Rating: **MINOR** (Remaining: prompt tuning and validation against production LLM behavior)

**Evidence**:
- Implemented: 4-stage scientific reasoning pipeline in `core/reasoning/pipeline.py`
- Implemented: virtual evaluation with candidate generation and top-K forwarding in `core/reasoning/virtual_eval.py`
- Implemented: trace persistence through injected trace store in `core/reasoning/pipeline.py`
- Implemented: CoSTEER structured feedback and knowledge self-generation in `core/loop/costeer.py`
- Integrated into both `DataScienceProposalEngine` and `SyntheticResearchProposalEngine`
- Verified by unit, scenario integration, and E2E tests covering structured feedback, trace recording, and knowledge writes

**Impact**:
- Proposals now go through structured scientific reasoning before generation
- Virtual evaluation filters low-quality ideas before expensive coding stage
- Multi-candidate generation with LLM ranking reduces wasted compute
- Quality gap vs. paper primarily in prompt refinement, not architecture

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-08
- **Tasks**: T2, T4, T6, T7, T8, T12, T14
- **Tests**: schemas, prompts, pipeline, virtual evaluation, CoSTEER, scenario integration, and new E2E coverage

---

## FC-4: Memory Context (Collaborative Cross-Branch Memory)

### Paper Vision

FC-4 enables knowledge sharing across parallel branches via an interaction kernel:

**3 hypothesis sources**:
- **hc**: Current branch's hypothesis
- **h⋆**: Globally optimal hypothesis (best across all branches)
- **hs**: Probabilistically sampled hypothesis from other branches

**Interaction kernel** (Appendix D):
- Formula: `K(hi, hj) = α * cosine(embed(hi), embed(hj)) + β * (score(hi) - score(hj)) + γ * decay(time)`
- Combines semantic similarity, performance difference, and temporal decay
- Used to weight which external hypotheses to incorporate

**Algorithm 2** (Adaptive hypothesis selection):
- LLM chooses from three actions: **Select** (use external hypothesis as-is), **Modify** (adapt external hypothesis), **Generate** (create new hypothesis)
- Enables dynamic knowledge transfer between branches

### Current State — **Partial Implementation**

Cross-branch memory structure with basic storage, but missing core algorithm components:

- **Location**: `memory_service/` (4 modules: `service.py`, `interaction_kernel.py`, `hypothesis_selector.py`)
- **Capability**: Storage infrastructure exists, but missing interaction kernel and Algorithm 2
- **Implemented**:
   - SQLite-backed hypothesis storage with cross-branch queries
   - Basic `get_cross_branch_hypotheses()` function
   - Config-driven: `RD_AGENT_HYPOTHESIS_STORAGE` env var, `enable_hypothesis_storage` flag
   - Hypothesis selector module exists

- **Missing (Blocking Algorithm 2)**:
   - Interaction kernel computation: K(hi, hj) = α·cosine(embed) + β·δscore + γ·decay(time)
   - Embedding-based similarity scoring (TF-IDF vectorizer referenced but not integrated)
   - Adaptive hypothesis selection (Select/Modify/Generate based on progress)
   - LLM integration for modify/generate actions

### Gap Rating: **SIGNIFICANT** (Remaining: interaction kernel, embedding similarity, Algorithm 2 adaptive selection)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T6 (interaction kernel), T7 (hypothesis selector), T8 (memory service extension), T11 (wiring)
- **Tests**: 48+ tests covering TF-IDF, cosine similarity, interaction kernel, hypothesis selector, memory storage, cross-branch queries

**Evidence**:
- Partial: Storage infrastructure exists but Algorithm 2 selection logic incomplete
- Missing: Full interaction kernel (embedding similarity + performance weighting + temporal decay)
- Missing: Adaptive selection mechanism for Select/Modify/Generate actions
- Missing: LLM-driven hypothesis modification for adaptive branch knowledge transfer

**Impact**:
- Hypotheses can be stored and retrieved, but not intelligently weighted
- No semantic similarity scoring between cross-branch ideas
- Cannot adaptively choose between selecting/modifying/generating new hypotheses
- Knowledge transfer between branches lacks the paper's interactive scoring mechanism

---

## FC-5: Coding Workflow (Efficient Iterative Debug)

### Paper Vision

FC-5 optimizes the expensive code execution cycle with debug mode:

**Debug mode features**:
- **10% data sampling**: Run on small data subset for fast debugging
- **Epoch reduction**: Fewer training epochs during debug
- **Timing estimation**: Estimate full-run time from debug run

**Multi-stage evaluation** (Appendix E.5):
1. **Execution success**: Does the code run without errors?
2. **Competition alignment**: Does the output match competition format?
3. **Debug compliance**: Does it respect debug mode constraints (time, memory)?
4. **Submission authenticity**: Is the submission valid for leaderboard?

### Current State — **Partial Implementation**

Multi-stage evaluation framework exists, but debug mode integration incomplete:

- **Location**: `evaluation_service/service.py`, `app/config.py`
- **Capability**: Multi-stage evaluation structure with config flags, debug sampling not fully integrated
- **Implemented**:
   - Multi-stage evaluation: 4 stages with weighted scoring (execution, alignment, compliance, authenticity)
   - Duration tracking: `ExecutionResult.duration_sec` and `timed_out` fields
   - Debug config flags: `debug_mode`, `debug_sample_fraction` (10%), `debug_max_epochs` (5)
   - Config-driven env vars: `RD_AGENT_DEBUG_MODE`, `RD_AGENT_DEBUG_SAMPLE_FRACTION`, `RD_AGENT_DEBUG_MAX_EPOCHS`
   
- **Missing (Blocking actual debug iteration)**:
   - Data sampling integration: 10% data sampling not applied to scenario execution
   - Timing estimation: Full-run time extrapolation from debug runs not implemented
   - Debug mode enforcement: Scenario runners do not respect debug sampling constraints

### Gap Rating: **SIGNIFICANT** (Remaining: actual sampling integration, timing extrapolation)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T1 (ExecutionResult extensions), T9 (debug mode + multi-stage evaluation), T11 (config wiring)
- **Tests**: 16+ tests covering multi-stage evaluation, debug config, duration tracking

**Evidence**:
- Partial: Config and evaluation stages exist, execution not integrated
- Missing: Data sampling enforcement in scenario runners (10% sampling not applied)
- Missing: Timing estimation from debug run to full run
- Missing: Multi-stage evaluation checks integrated with actual execution

**Impact**:
- Debug mode configuration exists but has no effect on actual execution
- Cannot run fast debug cycles with reduced data
- No timing extrapolation to estimate full-run duration
- Slower iteration during development (always full evaluation)

---

## FC-6: Evaluation Strategy (Automated Data Splitting & Validation)

### Paper Vision

FC-6 automates evaluation infrastructure:

**Automated data splitting**:
- 90/10 stratified train/test split
- Ensures fair evaluation across candidates
- Maintains class distribution in both splits

**Standardized grading scripts**:
- Auto-generated evaluation code
- Consistent metrics across experiments
- Competition-specific scoring functions

**ValidationSelector** (Appendix E.6):
- Multi-candidate re-validation on consistent holdout set
- Ranks solutions by validation performance
- Prevents overfitting to any single train/test split

### Current State — **Partial Implementation**

Basic evaluation infrastructure with framework for validation selection, but missing automated data splitting:

- **Location**: `evaluation_service/stratified_splitter.py`, `evaluation_service/validation_selector.py`, `evaluation_service/service.py`
- **Capability**: Validation ranking framework, but data splitting and auto-grading not integrated
- **Implemented**:
   - ValidationSelector: Ranks multiple candidates by holdout validation scores
   - Leaderboard: `get_leaderboard()` returns sorted (branch_id, score) tuples
   - Branch aggregation: `aggregate_branch_scores()` computes average scores
   - Stratified splitter class: 90/10 split logic with deterministic seed support

- **Missing (Blocking FC-6 automation)**:
   - Automated data splitting: not called by evaluation pipeline
   - Stratified label preservation: code exists but not enforced in scenarios
   - Auto-generated grading scripts: no script generation per scenario
   - Validation-driven candidate ranking: splitter exists but not integrated with execution

### Gap Rating: **SIGNIFICANT** (Remaining: automated split integration, grading script generation)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T10 (stratified splitter + ValidationSelector), T11 (wiring)
- **Tests**: 25+ tests covering stratified splitting, deterministic seeds, validation ranking, leaderboard

**Evidence**:
- Partial: Splitter and selector exist as standalone modules
- Missing: Automated data splitting called during evaluation pipeline
- Missing: Grading script generation per scenario
- Missing: Integration of stratified splitting with actual data loading

**Impact**:
- Manual data splitting required; cannot guarantee consistency across candidates
- No scenario-specific auto-grading scripts
- Risk of overfitting to single train/test split
- Validation selection logic cannot execute without automated splitting infrastructure

---

## Summary Table

| Component | Rating | Paper Key Features | Current State | Ablation Impact |
|-----------|--------|-------------------|---------------|-----------------|
| **FC-1 Planning** | SIGNIFICANT | Time-aware dynamic strategy | Partial: time tracking exists, missing Algorithm 1 integration and cost-aware strategy switching | Not tested separately |
| **FC-2 Exploration Path** | MINOR | Parallel DAG + pruning + merging | Fully implemented: PUCT, reward, backprop, Layer-0 diversity, pruning, merging (single-worker sequential execution) | **-28%** (largest) |
| **FC-3 Reasoning Pipeline** | MINOR | 4-step reasoning + virtual eval | Fully implemented: 4-stage pipeline, virtual eval N=5/K=2, trace persistence, structured feedback, knowledge self-generation | Not tested separately |
| **FC-4 Memory Context** | SIGNIFICANT | Cross-branch kernel + embeddings | Partial: storage exists, missing interaction kernel and Algorithm 2 adaptive selection | -9% (smallest) |
| **FC-5 Coding Workflow** | SIGNIFICANT | Debug mode + multi-stage eval | Partial: config and evaluation stages exist, missing data sampling enforcement and timing extrapolation | Not tested separately |
| **FC-6 Evaluation Strategy** | SIGNIFICANT | Automated split + grading + ValidationSelector | Partial: selector logic exists, missing automated split integration and auto-grading scripts | Not tested separately |

**Key insight**: FC-2 and FC-3 are fully implemented with paper-critical behaviors in code and tests. FC-1, FC-4, FC-5, FC-6 have infrastructure in place but are missing core algorithmic integration or execution enforcement. Remaining significant gaps require: Algorithm 1 time budget loop (FC-1), interaction kernel + Algorithm 2 (FC-4), sampling enforcement (FC-5), and split pipeline integration (FC-6). Phase 2 concerns include async multi-worker parallelism and production LLM validation.

---

## Prioritized Implementation Roadmap (Archived)

This roadmap is kept for historical context. The FC-2 / FC-3 items below are completed on `feat/paper-fc-implementation`; any remaining bullets should be read as Phase 2 enhancements rather than open core capability gaps.

**Priority order**: Ablation impact (where available) + dependency analysis

### P0: CRITICAL — Exploration Path (FC-2)

**Why first**: Largest ablation impact (-28%), foundational for other FCs

**Action items**:
- Implement DAG-based branch structure in `core/loop/`
- Add parallel branch executor
- Implement diversity-first layer-0 generation logic
- Add path pruning based on evaluation scores
- Implement multi-trace merging (combine best ideas from successful branches)

**Dependencies**: None — can be implemented independently

---

### P1: MAJOR — Reasoning Pipeline (FC-3)

**Why second**: Foundational for proposal quality, independent of branches

**Action items**:
- Refactor `ProposalEngine` to 4-stage pipeline (analyze → identify → hypothesize → generate)
- Add problem analysis step before proposal generation
- Implement hypothesis formulation (LLM reasons about WHY methods work)
- Add virtual evaluation: generate N=5 candidates, LLM ranks, forward top K=2 to coding

**Dependencies**: None — can be implemented independently, will benefit all proposals (single-chain or multi-branch)

---

### P1: MAJOR — Planning (FC-1)

**Why third**: Enables time-aware optimization, low implementation complexity

**Action items**:
- Add time budget tracking to loop executor (track `elapsed_time()` and `deadline`)
- Implement dynamic method selection based on remaining time ratio
- Add cost estimation for different methods (fast iterative vs. expensive ensemble)
- Integrate with FC-2 branching (allocate time budget across branches)

**Dependencies**: Benefits from FC-2 (time allocation across branches), but can be implemented without it

---

### P1: MAJOR — Memory Context (FC-4)

**Why fourth**: Smallest ablation impact (-9%), requires FC-2 branches to be most effective

**Action items**:
- Implement embedding-based hypothesis storage
- Add interaction kernel computation (similarity + score delta + temporal decay)
- Implement Algorithm 2 adaptive hypothesis selection (Select/Modify/Generate)
- Wire cross-branch hypothesis sharing (requires FC-2 DAG to be implemented first)

**Dependencies**: **Requires FC-2** — cross-branch memory has no value without branches

---

### P2: Enhancement — Coding Workflow (FC-5)

**Why fifth**: Has iteration already, missing optimizations

**Action items**:
- Add debug mode flag to CoSTEER configuration
- Implement 10% data sampling for fast debugging
- Add timing estimation (extrapolate full-run time from debug time)
- Implement multi-stage evaluation checks (execution → alignment → compliance → authenticity)

**Dependencies**: None — can be implemented independently

---

### P2: Enhancement — Evaluation Strategy (FC-6)

**Why sixth**: Lowest priority, no ablation data, incremental improvement

**Action items**:
- Implement automated train/test data splitter (90/10 stratified)
- Generate standardized grading scripts per scenario
- Implement ValidationSelector for multi-candidate ranking
- Add holdout set management (consistent across all candidates)

**Dependencies**: Benefits from FC-3 (multi-candidate generation), but can be implemented independently

---

## Appendix: Paper Reference

**Full Citation**:
- Paper: RDAgent: A Research and Development Agent for Autonomous AI-Driven Research
- (Full bibliographic details: authors, year, venue — available in paper PDF)

**Key Sections**:
- **Algorithm 1**: Page 5 (core 6-step loop: Planning → Exploration → Memory → Reasoning → Coding → Evaluation)
- **FC Definitions**: Section 3 (pages 4-6) — detailed descriptions of all 6 Framework Components
- **Appendix E**: Pages 23-28 — complete prompts for all 6 FCs, including specific LLM instructions
- **Ablation Studies**:
  - Table 3 (page 7): Research phase ablation — FC-2 removal = -28%, FC-4 removal = -9%
  - Figure 3 (page 9): Development phase ablation — CoSTEER iteration impact
- **Computational Efficiency**: Appendix C — $21/competition with GPT-5, 12h runtime, single V100
- **RAG Negative Result**: Section 4.3 — RAG hurts overall performance (35.1% → 32.0%), only helps on high-difficulty tasks

**Additional Findings**:
- Best model config: GPT-5 only (35.1%) or o3(Research) + GPT-4.1(Development) hybrid (29.7%)
- MLE-Bench: 35 Kaggle competitions, success rate = fraction with valid submissions
- Case study: Jigsaw Toxic Comment Classification (pages 29-33) — detailed trace of RDAgent's exploration path

---

**Document Version**: 2.1  
**Last Updated**: 2026-03-08  
**Status**: FC-2 and FC-3 fully implemented (paper-critical behaviors). FC-1, FC-4, FC-5, FC-6 have partial implementations with significant gaps in algorithmic integration and execution enforcement. Remaining work focuses on algorithm 1 integration, interaction kernel, sampling enforcement, and pipeline wiring.
