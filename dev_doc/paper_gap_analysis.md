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

### Current State

Our implementation has basic iteration-aware prompts but no time budget tracking:

- **Location**: `llm/prompts.py` → `_iteration_strategy()` function
- **Capability**: Simple 3-tier iteration logic (early/mid/late stages)
- **Limitations**:
  - No actual time budget tracking or elapsed time measurement
  - No cost tracking for different methods
  - No dynamic method selection based on remaining time
  - Static thresholds (iteration < 3, iteration < 7) rather than time-based

The `_iteration_strategy()` function uses hardcoded iteration counts to return stage labels ("early", "middle", "late"), which is a simplified stand-in, not the paper's full time-aware planning.

### Gap Rating: **MAJOR**

**Evidence**:
- Missing: Time budget loop structure from Algorithm 1
- Missing: Dynamic method cost estimation
- Missing: Time-based strategy switching

**Impact**:
- Cannot optimize method selection based on time constraints
- Wastes expensive compute on exploratory methods when deadline approaches
- Cannot prioritize quick wins early vs. thorough search later

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

### Current State

Our implementation uses a single sequential chain only:

- **Location**: `core/loop/step_executor.py` → StepExecutor executes one proposal at a time
- **Capability**: Sequential iteration through proposal → code → evaluate cycle
- **Limitations**:
  - `BranchTraceStore` exists in design documents but **not implemented** in code
  - No parallel branch execution
  - No path merging logic
  - No pruning based on scores
  - Cannot explore multiple solution directions simultaneously

**Architecture**: The 6-stage plugin pipeline (`build_context → propose → generate → develop → run → summarize`) runs linearly, advancing one step at a time. There is no DAG scheduler or branch manager.

### Gap Rating: **SIGNIFICANT**

**Evidence**:
- Ablation study shows **-28% performance** when removed (largest impact of all 6 FCs)
- Implemented: MCTS/PUCT scheduler (`exploration_manager/scheduler.py`), branch pruning (`exploration_manager/pruning.py`), trace merging via LLM (`exploration_manager/merging.py`)
- Wired into `ExplorationManager`, `LoopEngine`, and `app/runtime.py` with config-driven enablement
- Remaining: async parallel execution (Phase 2), advanced pruning heuristics

**Impact**:
- Core DAG-based multi-branch exploration now functional (sequential execution)
- PUCT formula balances exploration/exploitation per paper's Algorithm 1
- Branch pruning filters low-scoring paths; trace merging synthesizes best ideas
- Parallel execution across branches deferred to Phase 2 (currently sequential)

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T1 (data models), T8 (MCTS scheduler), T9 (multi-branch engine), T10 (pruning), T11 (merging), T12 (wiring)
- **Tests**: 53+ tests covering scheduler, pruning, merging, engine, and integration wiring

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

### Current State

Our implementation uses single-step LLM generation:

- **Location**: `scenarios/*/plugin.py` → `ProposalEngine.propose()` method
- **Capability**: Direct one-shot LLM call to generate proposal
- **Limitations**:
  - No 4-step decomposition pipeline
  - No problem identification phase
  - No hypothesis formulation
  - No virtual evaluation before coding
  - `ProposalEngine` directly returns a `ProposalDraft` without multi-candidate evaluation

**Current prompt structure** (`llm/prompts.py:proposal_prompt()`): Single unified prompt with task summary, previous proposals, and iteration strategy. No structured reasoning steps, no multi-candidate generation.

### Gap Rating: **MINOR**

**Evidence**:
- Implemented: 4-stage scientific reasoning pipeline (`core/reasoning/pipeline.py`) — Analyze → Identify → Hypothesize → Design
- Implemented: Virtual evaluation with N=5 candidates, K=2 forward selection (`core/reasoning/virtual_eval.py`)
- Integrated into both `DataScienceProposalEngine` and `SyntheticResearchProposalEngine`
- Prompt structure follows Appendix E.3 multi-turn dialogue pattern
- Remaining: prompt tuning with real data, production LLM validation

**Impact**:
- Proposals now go through structured scientific reasoning before generation
- Virtual evaluation filters low-quality ideas before expensive coding stage
- Multi-candidate generation with LLM ranking reduces wasted compute
- Quality gap vs. paper primarily in prompt refinement, not architecture

#### Implementation Status
- **Branch**: `feat/paper-fc-implementation`
- **Date**: 2026-03-07
- **Tasks**: T2 (prompts), T3 (schemas), T4 (mock), T5 (pipeline), T6 (virtual eval), T7 (scenario integration)
- **Tests**: 77+ tests covering schemas, prompts, mock, pipeline, virtual eval, and scenario integration

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

### Current State

Our implementation has a basic failure-case store with no cross-branch communication:

- **Location**: `memory_service/service.py` → 145-line SQLite implementation
- **Capability**: Stores failed experiment attempts within a single run
- **Limitations**:
  - No cross-branch communication (because we have no branches)
  - No interaction kernel or embedding-based similarity
  - No hypothesis reuse across different runs or branches
  - No adaptive selection mechanism
  - Simple key-value store, not a knowledge graph

**Current schema**: `MemoryService` stores `(experiment_id, failure_type, error_message, timestamp)` tuples. No embeddings, no similarity search, no probabilistic sampling.

### Gap Rating: **MAJOR**

**Evidence**:
- Paper shows **-9% performance** when removed (smallest drop, but still significant)
- Missing: Embedding-based hypothesis storage
- Missing: Interaction kernel for similarity + performance weighting
- Missing: Algorithm 2 adaptive hypothesis selection
- Missing: Cross-branch knowledge sharing (dependent on FC-2 branches existing first)

**Impact**:
- Cannot leverage knowledge from parallel exploration paths
- Each branch relearns lessons independently (wasteful)
- No semantic search over past hypotheses
- However: This FC has smallest ablation impact, so lower priority than FC-2/FC-3

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

### Current State

Our implementation has multi-round iteration but no debug mode optimizations:

- **Location**: `core/loop/costeer.py` → CoSTEER multi-round code evolution (49 lines)
- **Capability**: Iterative code improvement loop (generate → execute → feedback → refine)
- **Limitations**:
  - No debug mode flag or configuration
  - No 10% data sampling for fast debugging
  - No timing estimation
  - `EvaluationService` does basic pass/fail, no multi-stage evaluation checks
  - Always runs full evaluation (expensive)

**Current CoSTEER logic**: Calls `self.coder.develop()` → `self.runner.run()` → `self.feedback_analyzer.summarize()` in a loop. No fast debug path.

### Gap Rating: **SIGNIFICANT**

**Evidence**:
- Has iteration capability (core loop exists)
- Missing: Debug mode with 10% sampling
- Missing: Timing estimation
- Missing: Multi-stage evaluation checks

**Impact**:
- Slower debug cycles (always run full evaluation)
- Higher compute cost (no fast iteration path)
- However: Paper didn't test FC-5 ablation separately, suggesting lower priority than FC-2/FC-3

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

### Current State

Our implementation has basic evaluation but no automation:

- **Location**: `EvaluationService` in service layer + scenario plugins
- **Capability**: Scenarios define custom evaluation methods
- **Limitations**:
  - No automated train/test data splitting
  - No grading script generation
  - No ValidationSelector for multi-candidate comparison
  - Each scenario manually implements evaluation logic
  - No standardization across scenarios

**Current approach**: Each scenario plugin's `FeedbackAnalyzer.summarize()` method manually computes metrics. No shared evaluation framework.

### Gap Rating: **SIGNIFICANT**

**Evidence**:
- Basic evaluation exists (scenarios can compute scores)
- Missing: Automated data splitting
- Missing: Grading script generation
- Missing: ValidationSelector multi-candidate ranking

**Impact**:
- Cannot reliably compare multiple solution candidates
- Risk of overfitting to single train/test split
- Manual evaluation is error-prone and inconsistent
- However: Not tested separately in ablation, suggesting lower priority

---

## Summary Table

| Component | Rating | Paper Key Features | Current State | Ablation Impact |
|-----------|--------|-------------------|---------------|-----------------|
| **FC-1 Planning** | MAJOR | Time-aware dynamic strategy | Static 3-tier iteration (`_iteration_strategy()`) | Not tested separately |
| **FC-2 Exploration Path** | **CRITICAL** | Parallel DAG + pruning + merging | Single sequential chain only | **-28%** (largest) |
| **FC-3 Reasoning Pipeline** | MAJOR | 4-step reasoning + virtual eval | Single-step LLM generation | Not tested separately |
| **FC-4 Memory Context** | MAJOR | Cross-branch kernel + embeddings | SQLite failure store (145 lines) | -9% (smallest) |
| **FC-5 Coding Workflow** | SIGNIFICANT | Debug mode + multi-stage eval | CoSTEER iteration (49 lines), no debug mode | Not tested separately |
| **FC-6 Evaluation Strategy** | SIGNIFICANT | Automated split + grading + ValidationSelector | Manual scenario evaluation | Not tested separately |

**Key insight**: FC-2 (Exploration Path) is the single largest gap, with 28% performance impact in the paper's ablation. FC-4 (Memory Context) has the smallest impact (9%) despite its architectural sophistication.

---

## Prioritized Implementation Roadmap

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

**Document Version**: 1.0  
**Last Updated**: 2026-03-07  
**Status**: Initial gap analysis complete. Roadmap subject to revision based on implementation experience.
