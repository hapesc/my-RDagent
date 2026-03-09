# FC-1456 Implementation — Learnings

## [2026-03-09] Session Initialization

### Working Directory
- PRIMARY: `/Users/michael-liang/Code/my-RDagent-quant` (git worktree, `feat/quant-scenario` branch)
- PLAN REPO: `/Users/michael-liang/Code/my-RDagent` (has .sisyphus/)

### Completed Tasks
- **T1**: ContextPack extended (branch_id, source_type, timestamp), DebugConfig added to data_models.py, PlanningStrategy.budget_allocation added to llm/schemas.py, planning_strategy_prompt() updated in llm/prompts.py — VERIFIED: `python3 -c "from data_models import ContextPack, DebugConfig; ..."` prints OK
- **T2**: `dev_doc/fc_contract_table.md` created with all FC rows

### Test Suite State
- 739 tests pass as of T1 completion
- Run: `python3 -m pytest tests/ -q --tb=no` in `/Users/michael-liang/Code/my-RDagent-quant`

### Key File Locations (in /Users/michael-liang/Code/my-RDagent-quant/)
- `data_models.py` — ContextPack at line ~430, DebugConfig at line ~442
- `llm/schemas.py` — PlanningStrategy with budget_allocation
- `llm/prompts.py` — planning_strategy_prompt() updated
- `llm/adapter.py` — MockLLMProvider
- `app/runtime.py` — build_runtime() assembles ScenarioContext — DebugConfig NOT YET injected
- `scenarios/data_science/plugin.py` — ProposalEngine at lines 108-110 STILL has `_ = context; _ = plan`
- `scenarios/quant/plugin.py` — same discard pattern at lines 107-109
- `scenarios/synthetic_research/plugin.py` — same pattern
- `memory_service/interaction_kernel.py` — COMPLETE, unused
- `memory_service/hypothesis_selector.py` — COMPLETE, unwired
- `evaluation_service/stratified_splitter.py` — COMPLETE, uncalled
- `evaluation_service/validation_selector.py` — COMPLETE, unwired
- `core/loop/engine.py:106` — passes `history_summary={}` (empty, needs fix in T13)

### Guardrails (NEVER violate)
- NO changes to 6 Protocol signatures in `plugins/contracts.py`
- NO runtime mock fallbacks
- NO new vector databases
- Plan budget MUST NOT override explicit user step_overrides
- debug_mode=False MUST be zero behavior change

### Scope Creep Files (DO NOT COMMIT)
- `.dockerignore`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `QUICKSTART.md`, `pyproject.toml`
- `FC4_IMPLEMENTATION_INDEX.md`, `FC4_MEMORY_CONTEXT_ANALYSIS.md`
- `.sisyphus/plans/oss-maturity.md`
- Modified `requirements.txt` (+34 lines) — revert before final commit

## [2026-03-09] T3 DebugConfig Runtime Injection + Runner Debug Sampling

### What was actually required to wire `ScenarioContext.config["debug_config"]`
- `ScenarioContext` originally had no `config` field; added `config: Dict[str, Any] = field(default_factory=dict)` in `plugins/contracts.py`.
- Runtime-level debug flags are converted to `DebugConfig` in `app/runtime.py::build_run_service()` and passed into `StepExecutor`.
- The actual place where `ScenarioContext` is instantiated is `core/loop/step_executor.py` (not `app/runtime.py`), so injection is done immediately after `build_context(...)`.

### Per-scenario behavior implemented
- `data_science` runner:
  - Reads `scenario.config.get("debug_config")`.
  - If `debug_mode` + `supports_debug_sampling`, creates a sampled CSV (`*.debug_sample.csv`), rewrites `pipeline.py` data source path, logs sampling activation.
  - `debug_mode=False` keeps original behavior unchanged.
- `quant` runner:
  - Reads `scenario.config.get("debug_config")`.
  - If debug sampling enabled, reduces both date universe and symbol universe by `sample_fraction`, logs sampling activation.
  - `debug_mode=False` remains no-op.
- `synthetic_research` runner:
  - Reads `scenario.config.get("debug_config")` gracefully with no sampling behavior.
  - `supports_debug_sampling` is injected as `False` for this scenario from StepExecutor.

### Verification snapshot
- LSP diagnostics clean on changed files (`app/runtime.py`, `core/loop/step_executor.py`, `plugins/contracts.py`, scenario plugin files).
- `python3 -m pytest tests/ -q --tb=no` => **739 passed**.
- `grep -n "debug_config" app/runtime.py` => matches present.
- `grep -n "debug_mode" scenarios/data_science/plugin.py` => match present.

## [2026-03-09] T4 Planner Step-Level Time Budgets

### Implementation summary
- `planner/service.py` now calls `generate_strategy(context)` first inside `generate_plan()` and prefers `strategy.budget_allocation` only when it is a valid four-step seconds map for `proposal/coding/running/feedback`.
- Invalid or missing LLM budget payloads now fall back to `_build_budget_allocation(total_budget, elapsed_time)`, which uses `context.budget.total_time_budget`, defaults invalid totals to `600`, computes `remaining=max(0,total-elapsed)`, equal-splits remaining across four steps, and returns `1.0` second per step when remaining is exhausted.

### Acceptance summary
- Added focused FC-1 tests covering valid LLM budget preference, invalid LLM budget fallback, default-600 handling, and exhausted-budget minimum fallback.
- Verification passed: `python3 -m pytest tests/test_fc1_planning.py -q --tb=no` => `10 passed`; LSP diagnostics clean on changed planner/test files.

## [2026-03-09] T5 MemoryService query_context kernel ranking

### Implementation summary
- `memory_service/service.py::query_context()` now keeps legacy `failure_cases` retrieval, but excludes control-only query keys like `branch_id` from metadata SQL filtering.
- When hypothesis storage is enabled, it loads same-branch hypotheses via `query_hypotheses(branch_id=...)` plus cross-branch candidates via `get_cross_branch_hypotheses(...)`; without a branch it falls back to the existing global hypothesis query.
- Ranked hypothesis context now reuses existing `HypothesisSelector.adaptive_select(...)` / `select_hypothesis(...)` APIs to derive a reference hypothesis, then uses `InteractionKernel.compute(...)` through `rank_by_kernel(...)` for descending relevance ranking.
- `ContextPack.scored_items` is now populated as `(hypothesis_text, kernel_score)` and `ContextPack.highlights` prefers top-ranked summarized hypothesis text when available; `source_type` is conservatively set to `"memory"` whenever hypothesis results exist.
- Selector/kernel failures are handled with `logger.warning(..., exc_info=True)` and graceful fallback to stored hypothesis ordering/scores instead of crashing retrieval.

### Acceptance summary
- Verification passed in `/Users/michael-liang/Code/my-RDagent-quant`: `python3 -m pytest tests/test_memory_service.py tests/test_fc4_memory.py tests/test_fc4_interaction_kernel.py -q --tb=no` => `41 passed`.
- LSP diagnostics clean on changed Python file: `memory_service/service.py`.

## [2026-03-09] T6 ProposalEngine 消费 context + plan + parent_ids

### Implementation summary
- `scenarios/data_science/plugin.py::DataScienceProposalEngine.propose`
  - 移除 `_ = context/_ = plan/_ = parent_ids` 丢弃写法。
  - 新增三段注入文本：
    - `Prior Context`: `context.highlights` + `context.scored_items`（top-3，含 score；异常分数回退 `N/A`）
    - `Strategic Guidance`: `plan.guidance` 列表拼接；空值回退 `No specific guidance`
    - `Parent Branch Continuity`: `parent_ids` 拼接；空值回退 `None`
  - 将 enriched summary 同时用于 FC3 分支（`virtual_evaluator.evaluate` / `reasoning_pipeline.reason`）和 LLM fallback `proposal_prompt(...)`，确保不仅 fallback 路径可见上下文。

- `scenarios/quant/plugin.py::QuantProposalEngine.propose`
  - 移除 `_ = context/_ = plan/_ = parent_ids`。
  - 在 `FACTOR_PROPOSAL_USER_TEMPLATE` 渲染结果后追加统一三段（Prior Context / Strategic Guidance / Parent Branch Continuity）。
  - 保持 propose 签名与输出 `Proposal` 结构不变。

- `scenarios/synthetic_research/plugin.py::SyntheticResearchProposalEngine.propose`
  - 移除 fallback 路径中的 `_ = context/_ = plan/_ = parent_ids`。
  - 构造 enriched summary 并注入三段上下文信息。
  - FC3 路径（virtual evaluator / reasoning pipeline）改用 enriched summary，满足“不要只在 fallback LLM 路径里用 context/plan”约束。
  - LLM proposal_prompt 与 placeholder Proposal 也复用 enriched summary，保证行为一致。

### Verification snapshot
- `python3 -m pytest tests/test_task_13_data_science_plugin_v1.py tests/test_quant_plugin.py tests/test_fc1456_wiring.py -q --tb=no`
  - 结果：`31 passed`
- `grep -rn "_ = context\|_ = plan\|_ = parent_ids" scenarios/`
  - 结果：无命中
- LSP diagnostics
  - `scenarios/data_science/plugin.py`: clean
  - `scenarios/quant/plugin.py`: clean
  - `scenarios/synthetic_research/plugin.py`: clean

## [2026-03-09] T6 Retry (my-RDagent-quant) — real fix + re-verify

### Root cause
- 上次修改发生在 `/Users/michael-liang/Code/my-RDagent`，而本次失败报告针对的是 `/Users/michael-liang/Code/my-RDagent-quant`，导致“声称已修复但目标仓仍有 `_ = context/_ = plan/_ = parent_ids`”。

### Fix applied (only proposal methods)
- `scenarios/data_science/plugin.py`
  - 删除 propose 中 `_ = context/_ = parent_ids/_ = plan`。
  - 构造并注入：Prior Context（highlights + top scored_items）、Strategic Guidance（plan.guidance 或 `No specific guidance`）、Parent Branch Continuity（parent_ids 或 `None`）。
  - FC3 `virtual_evaluator.evaluate(...)` 与 `reasoning_pipeline.reason(...)` 改为消费 enriched summary；fallback `proposal_prompt(...)` 同步消费。

- `scenarios/quant/plugin.py`
  - 删除 propose 中 `_ = context/_ = parent_ids/_ = plan`。
  - 在 `FACTOR_PROPOSAL_USER_TEMPLATE` 渲染结果后追加三段注入（Prior Context / Strategic Guidance / Parent Branch Continuity）。

- `scenarios/synthetic_research/plugin.py`
  - 删除 propose fallback 中 `_ = context/_ = parent_ids/_ = plan`。
  - FC3 路径与 LLM fallback 统一消费 enriched summary；placeholder proposal summary 也使用 enriched summary。

### Verification (my-RDagent-quant)
- `grep -rn "_ = context|_ = plan|_ = parent_ids" scenarios/ --include='*.py'` => no matches
- `python3 -m pytest tests/test_task_13_data_science_plugin_v1.py tests/test_quant_plugin.py tests/test_fc1456_wiring.py -q --tb=no` => `31 passed`

## [2026-03-09] T7 Debug Mode Config Alignment Verification

### Verification Scope
Reviewed T7 requirement: "Runners respect debug_mode config"
- Checked all three scenario runners: data_science, quant, synthetic_research
- Verified implementation against plan criteria

### Implementation Status: FULLY COMPLIANT

#### data_science Runner (lines 317-347)
- ✅ Reads `scenario.config.get("debug_config")` 
- ✅ Conditional: `debug_mode=True AND supports_debug_sampling=True`
- ✅ Action: Creates sampled CSV (sample_fraction of rows), rewrites pipeline.py data_source path
- ✅ Logging: `logger.info("Debug mode active: sampling %.0f%% of data", sample_fraction * 100)`
- ✅ Fallback: When `debug_mode=False`, zero behavior change (transparent)

#### quant Runner (lines 286-305)
- ✅ Reads `scenario.config.get("debug_config")`
- ✅ Conditional: `debug_mode=True AND supports_debug_sampling=True`
- ✅ Action: Reduces date_universe and symbol_universe by sample_fraction
- ✅ Logging: `logger.info("Debug mode active: sampling %.0f%% of data", sample_fraction * 100)`
- ✅ Fallback: When `debug_mode=False`, zero behavior change (transparent)

#### synthetic_research Runner (lines 304-305)
- ✅ Reads `scenario.config.get("debug_config")`
- ✅ No-op pattern: `_ = debug_config` (gracefully ignores, no sampling)
- ✅ Correct: supports_debug_sampling injected as False by StepExecutor

### Plan Requirement Checklist
- [x] debug_mode=False → zero behavior change (all three runners)
- [x] debug_mode=True + supports_debug_sampling=True → sampling active (data_science, quant)
- [x] synthetic_research → no-op (correctly implemented)
- [x] At least one debug activation log (present in data_science and quant)
- [x] max_epochs handling: **NOT APPLICABLE** — none of the three runners control epochs:
  - data_science: executes single command (no epoch loop)
  - quant: backtest on fixed date range (no iteration control)
  - synthetic_research: generates static research brief (no iteration)

### Test Verification
- `python3 -m pytest tests/test_task_13_data_science_plugin_v1.py tests/test_quant_plugin.py tests/test_fc1456_wiring.py -q --tb=no`
- Result: **31 passed** ✅

### Conclusion
**NO CODE CHANGES REQUIRED** — T7 implementation is complete and compliant with all applicable plan criteria.

## [2026-03-09] T8 CoSTEER Multi-Round Feedback Injection

### Implementation summary
- **Goal**: Consume `experiment.hypothesis['_costeer_feedback']` written by `CoSTEEREvolver` (costeer.py lines 88-94) and inject it into Coder prompt generation for multi-round evolution awareness.
- **Three Coder implementations updated**:

#### DataScienceCoder (scenarios/data_science/plugin.py)
  - Added `_enrich_proposal_with_feedback(proposal, experiment)` helper method (lines 292-299)
  - In `develop()`, replaced bare `proposal.summary` with enriched version containing feedback
  - Prompt injection: `proposal_summary=proposal_summary_with_feedback` passed to `coding_prompt()`
  - Feedback format: `"{proposal.summary}\n\nPrevious round feedback:\n{feedback_text}"` when present

#### QuantCoder (scenarios/quant/plugin.py)
  - Added `_enrich_hypothesis_with_feedback(hypothesis, experiment)` helper method (lines 220-227)
  - Modified `_generate_factor_code()` signature to accept `experiment` parameter
  - Updated `develop()` call from `_generate_factor_code(proposal, scenario)` to include `experiment`
  - Prompt injection: `factor_hypothesis=factor_hypothesis_enriched` in `FACTOR_CODE_USER_TEMPLATE.format()` (line 231)
  - Same feedback format as DataScience

#### SyntheticResearchCoder (scenarios/synthetic_research/plugin.py)
  - Added `_enrich_proposal_with_feedback(proposal, experiment)` helper method (lines 256-263)
  - In `develop()`, replaced bare `proposal.summary` with enriched version
  - Prompt injection: `proposal_summary=proposal_summary_with_feedback` passed to `coding_prompt()`
  - Same feedback format as DataScience

### Safety features implemented
- **Type-safe extraction**: `if isinstance(experiment.hypothesis, dict)` guards against type mismatch
- **Null-safe**: `experiment.hypothesis.get("_costeer_feedback")` returns None if missing (first round)
- **String validation**: `if feedback_text and isinstance(feedback_text, str) and feedback_text.strip()` ensures non-empty text
- **First-round unchanged**: When `_costeer_feedback` absent, original `proposal.summary` used unchanged
- **Protocol signatures unchanged**: All Coder.develop() signatures remain (experiment, proposal, scenario) → CodeArtifact

### Verification snapshot
- Grep confirmation: `grep -rn "costeer_feedback\|Previous round feedback" scenarios/ --include='*.py'`
  - ✅ data_science/plugin.py: lines 294, 297
  - ✅ quant/plugin.py: lines 223, 226
  - ✅ synthetic_research/plugin.py: lines 260, 263
- pytest: `python3 -m pytest tests/test_task_13_data_science_plugin_v1.py tests/test_quant_plugin.py tests/test_fc1456_wiring.py -q --tb=no` => **31 passed** ✅
- LSP diagnostics clean on all three modified plugin files

### Context (why T8 matters)
- CoSTEER evolver runs multiple rounds: generate → execute → collect feedback → next round
- Each round now passes feedback to the next coder iteration via experiment.hypothesis
- This enables the LLM to see execution errors, data issues, and prior reasoning before re-coding
- Previously, feedback was lost between rounds (multi-round signal broken)
- T8 restores the information flow: costeer feedback → coder prompt → improved code generation
