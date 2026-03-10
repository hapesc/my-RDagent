# FC Data Flow Contract Reference

## How to Read This Table

This table maps the data flow for each Framework Component (FC) through the RDAgent system:
- **Producer**: The function or module that generates the data contract
- **Consumer**: The function that receives and uses that data
- **Data Type**: The structured object being passed
- **Fallback Behavior**: What happens if producer returns `None`, empty, or fails

For integration work (T6, T13), cross-reference the FC, trace through producer → consumer chain, and verify fallback paths are safe.

---

## FC-1: Planning (Iteration-Level Budget Allocation)

| FC | Producer Function | Consumer Function | Data Type | Fallback Behavior |
|----|-------------------|-------------------|-----------|-------------------|
| FC-1 | `planner.service.Planner.generate_plan()` | `core.loop.step_executor.StepExecutor.execute_iteration()` | `Plan` (with `budget_allocation`) | When `budget_allocation` is `None`, `_resolve_step_config()` applies global `AppConfig.sandbox_timeout_sec` as default soft timeout |
| FC-1 | `planner.service.Planner.generate_strategy()` | `planner.service.Planner.generate_plan()` | `PlanningStrategy` (with `exploration_weight` + `budget_allocation`) | When LLM fails to generate strategy, returns `None`; `generate_plan()` computes heuristic exploration strength from `(1.0 - progress)` |

---

## FC-4: Memory Context (Proposal Engine Integration)

| FC | Producer Function | Consumer Function | Data Type | Fallback Behavior |
|----|-------------------|-------------------|-----------|-------------------|
| FC-4 | `memory_service.service.MemoryService.query_context()` | `plugins.contracts.ProposalEngine.propose()` | `ContextPack` (with `items[]`, `highlights[]`, `scored_items[]`) | Empty `ContextPack` (all fields empty) → proposal prompt omits prior context section entirely; LLM still generates proposal without memory hints |
| FC-4 | `core.loop.engine.LoopEngine` | `memory_service.service.MemoryService.query_context()` | Query dict `{"run_id": str, "iteration": str}` | No fallback; query always succeeds; returns max `config.max_context_items` items or empty list |

---

## FC-5: Coding Workflow (Multi-Round Feedback + Debug Mode)

| FC | Producer Function | Consumer Function | Data Type | Fallback Behavior |
|----|-------------------|-------------------|-----------|-------------------|
| FC-5 | `core.loop.costeer.CoSTEEREvolver.evolve()` | `scenarios/*/plugin.Coder.develop()` | `ExperimentNode.hypothesis` dict (with `_costeer_feedback`, `_costeer_feedback_execution`, `_costeer_round` keys) | First round has no feedback keys → fallback adds no feedback section to coding prompt; subsequent rounds (round_idx >= 1) inject structured feedback or plain reason text |
| FC-5 | `app.config.AppConfig.debug_mode` | `scenarios/*/plugin.Runner.run()` | Boolean `debug_mode` (passed via `ScenarioContext.step_config.debug_mode`) | `debug_mode=False` → zero behavior change, no sampling applied; `debug_mode=True` → runner applies `config.debug_sample_fraction` (e.g., 0.1) to data sampling, max epochs capped at `debug_max_epochs` |
| FC-5 | `core.loop.step_executor.StepExecutor._resolve_step_config()` | All plugins (`Coder`, `Runner`, `FeedbackAnalyzer`) | `StepOverrideConfig` (per-step model, timeout, budget) | When requested overrides missing or invalid, uses `default_step_overrides` from `PluginBundle`; when PluginBundle defaults also missing, falls back to global `AppConfig` (e.g., `llm_model`, `sandbox_timeout_sec`) |

---

## FC-6: Evaluation Strategy (Data Splitting + Leaderboard)

| FC | Producer Function | Consumer Function | Data Type | Fallback Behavior |
|----|-------------------|-------------------|-----------|-------------------|
| FC-6 | `evaluation_service.stratified_splitter.StratifiedSplitter.split()` | `scenarios/*/plugin.ScenarioPlugin.build_context()` | `DataSplitManifest` (with `train_ids[]`, `val_ids[]`, `test_ids[]`, `seed`) | When `labels=None` or mismatch with `data_ids` → splits randomly instead of stratified; when `data_ids=[]` → returns empty manifest with all empty lists |
| FC-6 | `evaluation_service.service.EvaluationService.evaluate_run()` | EvaluationService internal leaderboard dict | `Score` (populated into `self._leaderboard` dict) | First run has empty leaderboard → `evaluate_run()` initializes with first score entry; subsequent calls append/update; if `execution_result.exit_code != 0`, execution_score=0.0 but score still recorded |
| FC-6 | `evaluation_service.service.EvaluationService.evaluate_run()` | `core.loop.engine.LoopEngine` (step result aggregation) | `EvalResult` (with `score` + `report_ref`) | Always returns `EvalResult` even on malformed execution_result; uses 0.0 scores for missing/null fields; no exception raised |

---

## Cross-FC Integration Notes

### FC-1 → FC-5
The `Plan.budget_allocation` from FC-1 flows into `_resolve_step_config()`, which merges it with per-step overrides. This soft timeout then guides `Runner.run()` in FC-5 (e.g., for Docker sandbox timeout).

### FC-4 → FC-5
The `ContextPack` from FC-4 is passed to `ProposalEngine.propose()`, which embeds it in the proposal prompt. This influences which code strategies the `Coder` (FC-5) receives in the `Proposal.reasoning` or `Proposal.design` fields.

### FC-5 ↔ FC-6
The `CodeArtifact` from `CoSTEEREvolver.evolve()` (FC-5) is executed, producing `ExecutionResult`. This result feeds into `EvaluationService.evaluate_run()` (FC-6), which scores it and updates the leaderboard.

### FC-6 → Loop
The leaderboard in EvaluationService is consulted by the `ExplorationManager` (MCTS) to rank branches and prune low-scoring ones, feeding back into the planning phase of the next iteration.
