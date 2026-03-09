# Quant Scenario — Learnings

## [2026-03-09] Session Bootstrap

### Working Directory
ALL code goes to: `/Users/michael-liang/Code/my-RDagent-quant/` (git worktree, branch `feat/quant-scenario`)

### Plugin Interface Contracts (from plugins/contracts.py)
- `ScenarioContext`: dataclass — `run_id, scenario_name, input_payload, task_summary, step_config`
- `PluginBundle`: dataclass — `scenario_name, scenario_plugin, proposal_engine, experiment_generator, coder, runner, feedback_analyzer, scene_usefulness_validator, default_step_overrides`
- `artifacts_ref` MUST be `json.dumps(list_of_paths)` — CommonUsefulnessGate parses this
- `step_config` must be propagated via `StepOverrideConfig.from_dict(input_payload.get("step_config"))`
- `scene_usefulness_validator` returns `None` = pass, `str` = rejection reason

### Runner Pattern (data_science plugin, lines 283-309)
```python
class DataScienceRunner(Runner):
    def __init__(self, backend: DockerExecutionBackend) -> None:
        self._backend = backend

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        backend_result = self._backend.execute(...)
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=backend_result.exit_code,
            logs_ref=logs,
            artifacts_ref=json.dumps(backend_result.artifact_paths),  # MUST be json.dumps
            ...
        )
```

### FeedbackAnalyzer Pattern (data_science, lines 312-354)
```python
class DataScienceFeedbackAnalyzer(FeedbackAnalyzer):
    def summarize(self, experiment, result, score=None) -> FeedbackRecord:
        usefulness_eligible = result.resolve_outcome().usefulness_eligible
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=draft.decision and usefulness_eligible,
            acceptable=draft.acceptable and usefulness_eligible,
            reason=draft.reason,
            observations=draft.observations,
            code_change_summary=draft.code_change_summary,
        )
```

### usefulness_validator Pattern (data_science, lines 357-377)
```python
def _validate_data_science_usefulness(gate_input: UsefulnessGateInput) -> Optional[str]:
    payload = gate_input.structured_payload
    if not isinstance(payload, dict): return "missing structured payload"
    # Check for required keys, return None if all checks pass
    return None  # None = pass, str = rejection reason
```

### build_bundle Pattern (data_science, lines 437-471)
```python
def build_data_science_v1_bundle(config=None, llm_adapter=None, ...) -> PluginBundle:
    plugin_config = config or DataScienceV1Config()
    adapter = llm_adapter or LLMAdapter(provider=MockLLMProvider(), ...)
    return PluginBundle(
        scenario_name="data_science",
        scenario_plugin=DataScienceScenarioPlugin(),
        proposal_engine=...,
        experiment_generator=...,
        coder=...,
        runner=...,
        feedback_analyzer=...,
        scene_usefulness_validator=_validate_data_science_usefulness,
        default_step_overrides=plugin_config.default_step_overrides,
    )
```

### scenarios/__init__.py Pattern
Must add to `scenarios/__init__.py`:
```python
from .quant import QuantConfig, build_quant_bundle, default_quant_step_overrides
```

### Data Models (from plan)
- `Proposal`: fields = `proposal_id, summary, constraints, virtual_score` (NOT `description`)
- `ExperimentNode`: fields = `node_id, run_id, branch_id, parent_node_id, loop_index, step_state, hypothesis, workspace_ref, result_ref, feedback_ref`
- `StepState`: enum, use `StepState.EXPERIMENT_READY`

### Key Constraints
- Only stdlib + numpy + pandas — NO other dependencies
- No modifications to core/ or app/ — only scenarios/ and plugins/
- Quant Runner: use local Python execution, NOT Docker (backtest runs inline)
- Primary metric: Sharpe; constraint metrics: IC, ICIR, MDD

### Test Infrastructure
- pytest at root: `python3 -m pytest tests/ -q`
- 638 existing tests that must not regress
- Test files go in `tests/` directory
