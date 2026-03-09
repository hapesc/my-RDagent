# FC-1 Planning: Dynamic Time-Aware Budget Allocation
## Comprehensive Implementation Analysis for RD-Agent

**Source Papers**: arxiv 2404.11276 (RD2-Agent)  
**Codebase**: my-RDagent  
**Analysis Date**: 2026-03-09  
**Status**: SIGNIFICANT gap (infrastructure ~80% complete, algorithmic enforcement missing)

---

## Executive Summary

### What's Implemented ✅
- **Time measurement**: Wall-clock iteration timing using `time.monotonic()`
- **Progress tracking**: `progress = elapsed_time / total_time_budget`
- **Stage mapping**: 3-stage classification (early/mid/late) based on progress thresholds
- **Exploration decay**: Linear formula `exploration_strength = 1.0 - progress`
- **Budget structure**: `BudgetLedger` with elapsed_time, iteration_durations, estimated_remaining
- **Planning infrastructure**: LLM planning capability with PlanningStrategy schema
- **Remaining time estimation**: Moving average of last 3 iterations

### What's Missing ❌
- **Budget allocation enforcement**: Created but never applied to execution
- **Method cost estimation**: No tracking of method computational cost
- **Dynamic method selection**: Cannot choose expensive/cheap methods based on budget
- **Urgency detection**: No mechanism to detect "running out of time"
- **Per-stage budget limits**: Budget not propagated to proposal/coding/evaluation timeouts

### Gap Classification
- **MAJOR infrastructure gaps** in cost estimation and urgency handling
- **CRITICAL execution gap** in budget consumption enforcement
- Implementation is 70-80% functional for infrastructure, 0% functional for enforcement

---

## Part 1: Complete Implementation Details

### 1.1 Time Tracking (LoopEngine)

**Location**: `core/loop/engine.py:105-244`

```python
# Iteration timing loop
while loop_state.iteration < target_iteration:
    iter_start = time.monotonic()  # Line 105
    
    # ... execute proposal + coding + evaluation ...
    
    # Time accounting (lines 238-244)
    iter_elapsed = time.monotonic() - iter_start
    budget.elapsed_time += iter_elapsed
    budget.iteration_durations.append(iter_elapsed)
    
    # Moving average estimation
    recent = budget.iteration_durations[-3:]
    avg_duration = sum(recent) / len(recent)
    remaining_iters = max(0, target_iteration - loop_state.iteration - 1)
    budget.estimated_remaining = avg_duration * remaining_iters
    
    loop_state.iteration += 1
```

**Measurement Strategy**:
- Uses `time.monotonic()` (not affected by system clock adjustments)
- Measures wall-clock time including all nested operations
- Appends to history for moving average calculation
- Recalculates remaining time every iteration

### 1.2 Budget Data Model

**Location**: `data_models.py:396-401`

```python
@dataclass
class BudgetLedger:
    """Tracks time and resource usage for the loop."""
    total_time_budget: float              # From run_session.stop_conditions.max_duration_sec
    elapsed_time: float = 0.0             # Cumulative seconds spent
    iteration_durations: List[float] = field(default_factory=list)  # Per-iteration times
    estimated_remaining: float = 0.0      # Projected remaining time
```

**Initialization**:
```python
budget = BudgetLedger(
    total_time_budget=float(run_session.stop_conditions.max_duration_sec),
    elapsed_time=0.0
)
```

### 1.3 Progress Calculation

**Location**: `planner/service.py:132-144`

```python
def _compute_progress(self, total_budget: float, elapsed: float) -> float:
    """
    progress = min(max(0.0, elapsed / total_budget), 1.0)
    
    Range: [0.0, 1.0] (clipped at boundaries)
    """
    if total_budget <= 0:
        logger.warning("planner.invalid_budget total=%.2f", total_budget)
        return 1.0
    progress = max(0.0, min(1.0, elapsed / total_budget))
    return progress

def _stage_from_progress(self, progress: float) -> str:
    """
    Stage boundaries:
        [0.0, 0.33)  → "early"
        [0.33, 0.66) → "mid"
        [0.66, 1.0]  → "late"
    """
    if progress < 0.33:
        return "early"
    if progress < 0.66:
        return "mid"
    return "late"
```

**Example Values**:
| Elapsed | Total | Progress | Stage |
|---------|-------|----------|-------|
| 10s | 100s | 0.10 | early |
| 30s | 100s | 0.30 | early |
| 50s | 100s | 0.50 | mid |
| 70s | 100s | 0.70 | late |
| 100s | 100s | 1.00 | late |

### 1.4 Budget Allocation Formula

**Location**: `planner/service.py:146-153`

```python
def _build_budget_allocation(self, progress: float) -> Dict[str, float]:
    """
    Formulas:
        exploration   = 1.0 - progress
        exploitation  = progress
    
    Constraint: exploration + exploitation = 1.0
    """
    allocation = {}
    allocation["exploration"] = 1.0 - progress
    allocation["exploitation"] = progress
    return allocation
```

**Allocation Over Time**:
| Progress | Stage | Exploration | Exploitation | Strategy |
|----------|-------|-------------|--------------|----------|
| 0.10 | early | 0.90 | 0.10 | High exploration |
| 0.33 | early→mid | 0.67 | 0.33 | More exploration |
| 0.50 | mid | 0.50 | 0.50 | Balanced |
| 0.66 | mid→late | 0.34 | 0.66 | More exploitation |
| 0.90 | late | 0.10 | 0.90 | High exploitation |

### 1.5 Exploration Strength (Exploration/Exploitation Balance)

**Location**: `planner/service.py:87-89`

```python
strategy = self.generate_strategy(context)  # Optional LLM call
if strategy is not None:
    # Use LLM-provided exploration weight
    exploration_strength = max(0.0, min(1.0, strategy.exploration_weight))
else:
    # Use heuristic: linearly decrease exploration
    exploration_strength = max(0.0, self._config.max_exploration_strength * (1.0 - progress))
    # With default max_exploration_strength=1.0:
    # exploration_strength = 1.0 - progress
```

**Two Modes**:
1. **Heuristic** (no LLM): `exploration_strength = 1.0 - progress`
2. **LLM-guided**: `exploration_strength = strategy.exploration_weight` (can be any [0,1])

### 1.6 Planning Context

**Location**: `data_models.py:404-410` and `planner/service.py:37-65`

```python
@dataclass
class PlanningContext:
    loop_state: LoopState
    budget: BudgetLedger
    history_summary: Dict[str, str] = field(default_factory=dict)

# Used in generate_strategy():
def generate_strategy(self, context: PlanningContext) -> Optional[PlanningStrategy]:
    budget = context.budget
    progress = self._compute_progress(budget.total_time_budget, budget.elapsed_time)
    stage = self._stage_from_progress(progress)
    budget_remaining = max(0.0, budget.total_time_budget - budget.elapsed_time)
    
    prompt = planning_strategy_prompt(
        task_summary="R&D exploration task",
        scenario_name="default",
        progress=progress,
        stage=stage,
        iteration=context.loop_state.iteration,
        history_summary=context.history_summary,
        budget_remaining=budget_remaining,
    )
    
    strategy = self._llm_adapter.generate_structured(prompt, PlanningStrategy)
    return strategy
```

### 1.7 Plan Generation

**Location**: `planner/service.py:67-113`

```python
def generate_plan(self, context: PlanningContext) -> Plan:
    loop_state = context.loop_state
    budget = context.budget
    progress = self._compute_progress(budget.total_time_budget, budget.elapsed_time)
    stage = self._stage_from_progress(progress)
    
    strategy = self.generate_strategy(context)
    if strategy is not None:
        exploration_strength = max(0.0, min(1.0, strategy.exploration_weight))
    else:
        exploration_strength = max(0.0, self._config.max_exploration_strength * (1.0 - progress))
    
    budget_allocation = self._build_budget_allocation(progress)
    guidance = self._build_guidance(stage, progress, context.history_summary)
    
    return Plan(
        plan_id=f"plan-{loop_state.loop_id}-{loop_state.iteration}",
        exploration_strength=exploration_strength,
        budget_allocation=budget_allocation,
        guidance=guidance,
    )
```

**Returned Plan Structure**:
```python
Plan(
    plan_id="plan-loop-abc-3",
    exploration_strength=0.45,  # From heuristic or LLM
    budget_allocation={
        "exploration": 0.55,      # NOT USED anywhere! ⚠️
        "exploitation": 0.45      # NOT USED anywhere! ⚠️
    },
    guidance=[
        "stage:mid",
        "progress:0.55",
        "focus:balance",
        "budget:moderate",
        "history:available"
    ]
)
```

---

## Part 2: Critical Gaps

### Gap 1: Budget Allocation is Created but Never Consumed

**Problem**:
```python
# The plan creates budget allocation...
plan.budget_allocation = {"exploration": 0.7, "exploitation": 0.3}

# But it's never used in execution! These don't exist:
# - step_executor.execute_iteration doesn't receive plan.budget_allocation
# - No timeouts are set based on allocation percentages
# - No per-stage resource limits
```

**Evidence**:
- `Plan.budget_allocation` is created in `planner/service.py:111`
- Never referenced in `core/loop/engine.py` or `core/loop/step_executor.py`
- StepExecutor signature doesn't include budget allocation
- No code constrains proposal/coding/evaluation time by allocation

**Impact**: Exploration/exploitation balance is only advisory (in `guidance`), not enforced.

### Gap 2: No Method Cost Estimation

**Problem**:
```python
# No data structure for method costs:
# ❌ method_costs = {"ensemble": 25.0, "single_model": 5.0, ...}

# No function to estimate cost:
# ❌ def estimate_cost(method: str) -> float

# Cannot decide if method is feasible:
# ❌ if estimate_cost(method) < budget_remaining: use_method(method)
```

**Paper's Vision**:
- Select fast methods (iterative fitting) when time is short
- Select expensive methods (ensembles, cross-validation) when time is abundant
- Current implementation has no way to track this distinction

**Impact**: All methods treated equally regardless of computational cost.

### Gap 3: No Urgency Detection

**Problem**:
```python
# Current: Always use same strategy, just change exploration weight
exploration_strength = 1.0 - progress  # Linear, always decreases

# Missing: Detect urgency and switch behavior
if estimated_remaining < 10.0:
    # Switch to fast-only methods
    # Disable expensive validations
    # Simplify proposal generation
```

**Paper's Vision** (Appendix E.1):
- At "late" stage with low `budget_remaining`: refuse expensive methods
- Cannot be handled by current linear formula

**Impact**: Cannot adapt method selection to time constraints.

### Gap 4: No Per-Stage Budget Limits

**Problem**:
```python
# Current: All stages have same timeout
RD_AGENT_SANDBOX_TIMEOUT_SEC=300  # Global timeout

# Missing: Dynamic per-stage timeouts based on plan
proposal_timeout = plan.budget_allocation["exploration"] * estimated_remaining_per_stage
coding_timeout = plan.budget_allocation["exploitation"] * estimated_remaining_per_stage
evaluation_timeout = plan.budget_allocation["evaluation"] * estimated_remaining_per_stage
```

**Impact**: Budget is not distributed across proposal/coding/evaluation phases.

---

## Part 3: Numeric Example (5-Iteration Run)

**Setup**:
- Total budget: 100 seconds
- Max loops: 5
- Actual durations: [25s, 23s, 24s, 26s, 22s] (totals 120s)

**Iteration 1** (elapsed=0→25s):
```
iter_elapsed = 25.0
budget.elapsed_time = 25.0
budget.iteration_durations = [25.0]
progress = 25.0 / 100 = 0.25
stage = "early"
estimated_remaining = 25.0 × 3 = 75.0s

Plan:
  exploration_strength = 1.0 - 0.25 = 0.75
  budget_allocation = {"exploration": 0.75, "exploitation": 0.25}
  guidance = ["stage:early", "progress:0.25", "focus:novelty", ...]
```

**Iteration 2** (elapsed=25→48s):
```
iter_elapsed = 23.0
budget.elapsed_time = 48.0
budget.iteration_durations = [25.0, 23.0]
progress = 48.0 / 100 = 0.48
stage = "mid"
recent = [25.0, 23.0]
avg_duration = 24.0
estimated_remaining = 24.0 × 2 = 48.0s

Plan:
  exploration_strength = 1.0 - 0.48 = 0.52
  budget_allocation = {"exploration": 0.52, "exploitation": 0.48}
```

**Iteration 3** (elapsed=48→72s):
```
iter_elapsed = 24.0
budget.elapsed_time = 72.0
progress = 72.0 / 100 = 0.72
stage = "late"
recent = [25.0, 23.0, 24.0]
avg_duration = 24.0
estimated_remaining = 24.0 × 1 = 24.0s

Plan:
  exploration_strength = 1.0 - 0.72 = 0.28
  budget_allocation = {"exploration": 0.28, "exploitation": 0.72}
```

**Iteration 4** (elapsed=72→98s):
```
iter_elapsed = 26.0
budget.elapsed_time = 98.0
progress = 98.0 / 100 = 0.98
stage = "late"
recent = [23.0, 24.0, 26.0]
avg_duration = 24.33
estimated_remaining = 24.33 × 0 = 0.0s ⚠️ OUT OF TIME

Plan:
  exploration_strength = 1.0 - 0.98 = 0.02
  budget_allocation = {"exploration": 0.02, "exploitation": 0.98}
```

**Iteration 5** (elapsed=98→120s, OVER BUDGET):
```
iter_elapsed = 22.0
budget.elapsed_time = 120.0 ⚠️ EXCEEDS TOTAL
progress = min(120.0 / 100, 1.0) = 1.0
```

**Key Observations**:
1. Budget is not hard-enforced; iteration 5 runs despite exceeding total
2. Planning warns through guidance but doesn't force early termination
3. Allocation is created but not used to constrain execution
4. Moving average smooths iteration variance: [25, 23, 24] → avg=24

---

## Part 4: Paper Reference

### FC-1 Definition (Section 3.1, Page ~4-5)

> FC-1 Planning implements **dynamic time-aware strategy** that adapts as the research competition progresses:
> - **Early stage** (little time elapsed): Limited budget, encourage novelty, exploratory methods
> - **Later stage** (approaching deadline): Allow expensive methods (ensembles, cross-validation)
> - **Adaptive tradeoff**: Manages exploration/exploitation balance over time
> - **Cost awareness**: Tracks computational budget and adjusts method selection accordingly

### Algorithm 1 (Page 5)

Planning stage of Algorithm 1:
1. Read current `time_budget` and `elapsed_time`
2. Compute remaining time and progress ratio
3. Select strategy (exploration weight, method selection) based on progress
4. Allocate budget across branches/methods

### Appendix E.1: Planning Prompt (Page ~24-25)

Planning prompt sent to LLM includes:
```
Time budget: {total_time_budget} seconds
Elapsed time: {elapsed_time} seconds
Remaining: {budget_remaining} seconds
Progress: {progress*100:.1f}%
Stage: {stage}

Choose planning strategy considering time constraints:
- Early stage, lots of time: maximize novelty (exploration_weight=0.8-1.0)
- Mid stage: balance (exploration_weight=0.4-0.6)
- Late stage, little time: focus on refining (exploration_weight=0.0-0.2)

Return JSON:
{
  "strategy_name": "...",
  "method_selection": "...",
  "exploration_weight": <0.0 to 1.0>,
  "reasoning": "..."
}
```

---

## Part 5: Implementation Status Summary

### ✅ Fully Implemented (FC-1 Foundation)

| Component | Status | Code | Notes |
|-----------|--------|------|-------|
| Time measurement | ✅ | `engine.py:105,238` | Uses `time.monotonic()` |
| Elapsed time tracking | ✅ | `engine.py:239` | Cumulative sum per iteration |
| Iteration duration history | ✅ | `engine.py:240` | List for moving average |
| Estimated remaining | ✅ | `engine.py:244` | Moving avg × remaining iters |
| Progress calculation | ✅ | `planner.py:132` | `progress = elapsed / total` |
| Stage mapping | ✅ | `planner.py:139` | 3 stages based on thresholds |
| Exploration/exploitation | ✅ | `planner.py:146` | Linear: `1.0 - progress` |
| Planning context | ✅ | `planner.py:37-65` | Passes budget info to LLM |
| Strategy schema | ✅ | `llm/schemas.py` | PlanningStrategy dataclass |
| Planning prompt | ✅ | `llm/prompts.py` | LLM prompt template |
| MockLLMProvider | ✅ | `llm/adapter.py` | Test mock responses |

### ❌ Missing (Critical Gaps)

| Component | Status | Blocking | Severity |
|-----------|--------|----------|----------|
| Budget allocation enforcement | ❌ | Step executor | CRITICAL |
| Method cost matrix | ❌ | Method selection | CRITICAL |
| Dynamic cost estimation | ❌ | Time-aware selection | CRITICAL |
| Urgency detection | ❌ | Late-stage behavior | MAJOR |
| Per-stage timeouts | ❌ | Resource distribution | MAJOR |
| Cost-aware feasibility | ❌ | Method availability | MAJOR |

---

## Part 6: How to Complete FC-1

### Step 1: Method Cost Matrix

```python
# Add to planner/service.py or new planner/costs.py
METHOD_COST_MATRIX = {
    "single_model": 5.0,           # 5 seconds
    "simple_ensemble": 15.0,       # 15 seconds
    "cross_validation": 20.0,      # 20 seconds
    "hyperparameter_tuning": 30.0, # 30 seconds
    "feature_engineering": 25.0,   # 25 seconds
}

def estimate_method_cost(method: str) -> float:
    return METHOD_COST_MATRIX.get(method, 10.0)

def is_method_feasible(method: str, budget_remaining: float) -> bool:
    cost = estimate_method_cost(method)
    return cost < budget_remaining
```

### Step 2: Extend BudgetLedger

```python
@dataclass
class BudgetLedger:
    total_time_budget: float
    elapsed_time: float = 0.0
    iteration_durations: List[float] = field(default_factory=list)
    estimated_remaining: float = 0.0
    
    # NEW: Per-stage tracking
    proposal_time: float = 0.0
    coding_time: float = 0.0
    evaluation_time: float = 0.0
```

### Step 3: Wire Budget into StepExecutor

```python
# In core/loop/engine.py, pass plan budget to step_executor:
step_result = self._step_executor.execute_iteration(
    ...,
    plan=plan,  # Already passed
    budget=budget,  # NEW: pass budget too
)

# In step_executor, compute stage timeouts:
proposal_timeout = plan.budget_allocation["proposal"] * budget.estimated_remaining_per_stage
coding_timeout = plan.budget_allocation["coding"] * budget.estimated_remaining_per_stage
```

### Step 4: Add Urgency Detection

```python
def should_use_expensive_methods(self, budget_remaining: float, total_budget: float) -> bool:
    # Use expensive methods only if >20% budget remains
    return (budget_remaining / total_budget) > 0.2

def get_urgency_level(self, progress: float) -> str:
    if progress < 0.33:
        return "relaxed"
    if progress < 0.66:
        return "moderate"
    if progress < 0.90:
        return "urgent"
    return "critical"
```

---

## Part 7: Configuration

**Current Environment Variables**:
```bash
RD_AGENT_LLM_PLANNING=true              # Enable LLM strategy generation (used by Planner)
RD_AGENT_COSTEER_MAX_ROUNDS=1           # Coding iterations (not related to FC-1)
RD_AGENT_SANDBOX_TIMEOUT_SEC=300        # Global timeout (not FC-1 budget)
```

**PlannerConfig**:
```python
@dataclass
class PlannerConfig:
    max_exploration_strength: float = 1.0  # Scale for exploration formula
    default_budget_allocation: Optional[Dict[str, float]] = None  # Can override defaults
    use_llm_planning: bool = False  # Control whether to call LLM for strategy
```

---

## Final Assessment

| Metric | Score | Comments |
|--------|-------|----------|
| **Infrastructure completeness** | 80% | Time tracking, progress, stages, allocation formulas all working |
| **Algorithm integration** | 40% | Budget allocation created but not enforced |
| **Cost-awareness** | 0% | No method cost estimation exists |
| **Enforcement** | 0% | No per-stage timeout enforcement |
| **Paper fidelity** | 50% | Foundation implemented, algorithmic core missing |

**Overall Status**: SIGNIFICANT gap. Foundation is solid (time tracking, formulas), but the actual budget allocation mechanism that should drive resource distribution across stages is incomplete.

**Time to Completion**: ~2-3 work-days for experienced developer (Tasks T1, T5, T11 from project plan).

