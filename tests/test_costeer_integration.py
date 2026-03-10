from __future__ import annotations

import json
import os
from importlib import util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.loop.costeer import CoSTEEREvolver
from core.loop.step_executor import StepExecutor
from data_models import (
    CodeArtifact,
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from llm.schemas import StructuredFeedback
from plugins.contracts import PluginBundle, ScenarioContext
from service_contracts import StepOverrideConfig


def _load_data_science_coder_class():
    plugin_path = Path(__file__).resolve().parents[1] / "scenarios" / "data_science" / "plugin.py"
    spec = util.spec_from_file_location("costeer_ds_plugin", plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load data science plugin module")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.DataScienceCoder


def _base_inputs(tmp_path) -> tuple[ExperimentNode, Proposal, ScenarioContext]:
    experiment = ExperimentNode(
        node_id="node-costeer",
        run_id="run-costeer",
        branch_id="main",
        hypothesis={"text": "baseline"},
        workspace_ref=str(tmp_path / "workspace"),
    )
    proposal = Proposal(proposal_id="proposal-costeer", summary="Build a robust feature pipeline")
    scenario = ScenarioContext(
        run_id="run-costeer",
        scenario_name="data_science",
        input_payload={"data_source": str(tmp_path / "train.csv")},
    )
    return experiment, proposal, scenario


def _eligible_execution_result(tmp_path) -> ExecutionResult:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({"status": "ok", "row_count": 20, "accuracy": 0.92}), encoding="utf-8")
    return ExecutionResult(
        run_id="run-costeer",
        exit_code=0,
        logs_ref=json.dumps({"status": "ok", "row_count": 20, "accuracy": 0.92}),
        artifacts_ref=json.dumps([str(metrics_path)]),
    )


def _make_step_executor(tmp_path, costeer_max_rounds: int) -> StepExecutor:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir(parents=True, exist_ok=True)

    scenario_plugin = MagicMock()
    scenario_plugin.build_context.return_value = ScenarioContext(
        run_id="run-step",
        scenario_name="data_science",
        input_payload={"task_summary": "costeer", "loop_index": 0},
        step_config=StepOverrideConfig(),
    )

    proposal_engine = MagicMock()
    proposal_engine.propose.return_value = Proposal(proposal_id="proposal-step", summary="summary")

    experiment_generator = MagicMock()
    experiment_generator.generate.return_value = ExperimentNode(
        node_id="node-step",
        run_id="run-step",
        branch_id="main",
        hypothesis={"text": "baseline"},
        workspace_ref=str(workspace_path),
    )

    coder = MagicMock()
    coder.develop.return_value = CodeArtifact(
        artifact_id="artifact-step",
        description="artifact description",
        location=str(workspace_path),
    )

    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)

    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.return_value = FeedbackRecord(
        feedback_id="fb-step",
        decision=True,
        acceptable=True,
        reason="acceptable",
    )

    plugin_bundle = PluginBundle(
        scenario_name="data_science",
        scenario_plugin=scenario_plugin,
        proposal_engine=proposal_engine,
        experiment_generator=experiment_generator,
        coder=coder,
        runner=runner,
        feedback_analyzer=feedback_analyzer,
    )

    evaluation_service = MagicMock()
    evaluation_service.evaluate_run.return_value = SimpleNamespace(
        score=Score(score_id="score-step", value=0.8, metric_name="acc")
    )

    workspace_manager = MagicMock()
    workspace_manager.create_workspace.return_value = str(workspace_path)
    workspace_manager.inject_files.return_value = None
    workspace_manager.create_checkpoint.return_value = None

    event_store = MagicMock()
    event_store.append_event.return_value = None

    return StepExecutor(
        plugin_bundle=plugin_bundle,
        evaluation_service=evaluation_service,
        workspace_manager=workspace_manager,
        event_store=event_store,
        costeer_max_rounds=costeer_max_rounds,
    )


def _run_step_executor_once(step_executor: StepExecutor) -> None:
    run_session = RunSession(
        run_id="run-step",
        scenario="data_science",
        status=RunStatus.CREATED,
        stop_conditions=StopConditions(max_loops=1, max_duration_sec=30),
        entry_input={"task_summary": "costeer integration"},
        active_branch_ids=["main"],
    )
    loop_state = LoopState(loop_id="loop-step", iteration=0, status=RunStatus.RUNNING)
    plan = Plan(plan_id="plan-step")
    step_executor.execute_iteration(
        run_session=run_session,
        loop_state=loop_state,
        task_summary="costeer integration",
        plan=plan,
        parent_ids=[],
        context_pack=ContextPack(),
    )


def test_costeer_single_round_bypasses_evolver(tmp_path) -> None:
    step_executor = _make_step_executor(tmp_path, costeer_max_rounds=1)
    with patch("core.loop.step_executor.CoSTEEREvolver") as evolver_cls:
        _run_step_executor_once(step_executor)
    evolver_cls.assert_not_called()


def test_costeer_multi_round_calls_develop_multiple_times(tmp_path) -> None:
    experiment, proposal, scenario = _base_inputs(tmp_path)
    coder = MagicMock()
    round_counter = {"value": 0}

    def _develop(**_kwargs):
        round_counter["value"] += 1
        return CodeArtifact(
            artifact_id=f"artifact-round-{round_counter['value']}",
            description=f"import pandas as pd\n# round {round_counter['value']}",
            location=str(tmp_path / f"round-{round_counter['value']}"),
        )

    coder.develop.side_effect = _develop
    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)
    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.side_effect = [
        FeedbackRecord(feedback_id="fb-1", decision=False, acceptable=False, reason="round-1 bad"),
        FeedbackRecord(feedback_id="fb-2", decision=False, acceptable=False, reason="round-2 bad"),
    ]
    evolver = CoSTEEREvolver(coder, runner, feedback_analyzer, max_rounds=3)

    evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

    assert coder.develop.call_count == 3


def test_costeer_feedback_injected_to_hypothesis(tmp_path) -> None:
    experiment, proposal, scenario = _base_inputs(tmp_path)
    coder = MagicMock()
    coder.develop.side_effect = [
        CodeArtifact("artifact-1", "code-v1", str(tmp_path / "v1")),
        CodeArtifact("artifact-2", "code-v2", str(tmp_path / "v2")),
    ]
    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)
    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.side_effect = [
        FeedbackRecord(feedback_id="fb-1", decision=False, acceptable=False, reason="needs fixes"),
        FeedbackRecord(feedback_id="fb-2", decision=True, acceptable=True, reason="acceptable"),
    ]
    llm_adapter = MagicMock()
    llm_adapter.generate_structured.return_value = StructuredFeedback(
        execution="runtime failed",
        code="replace template code with real feature engineering",
        reasoning="overall issue found",
        final_decision=False,
    )
    evolver = CoSTEEREvolver(coder, runner, feedback_analyzer, max_rounds=3, llm_adapter=llm_adapter)

    evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

    assert experiment.hypothesis.get("_costeer_feedback") == "overall issue found"


def test_costeer_stops_on_acceptable_feedback(tmp_path) -> None:
    experiment, proposal, scenario = _base_inputs(tmp_path)
    coder = MagicMock()
    coder.develop.return_value = CodeArtifact("artifact-1", "code-v1", str(tmp_path / "v1"))
    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)
    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.return_value = FeedbackRecord(
        feedback_id="fb-1", decision=True, acceptable=True, reason="good"
    )
    evolver = CoSTEEREvolver(coder, runner, feedback_analyzer, max_rounds=4)

    evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

    assert coder.develop.call_count == 1
    assert runner.run.call_count == 1


def test_costeer_max_rounds_caps_iterations(tmp_path) -> None:
    experiment, proposal, scenario = _base_inputs(tmp_path)
    coder = MagicMock()
    coder.develop.side_effect = [
        CodeArtifact("artifact-1", "code-v1", str(tmp_path / "v1")),
        CodeArtifact("artifact-2", "code-v2", str(tmp_path / "v2")),
        CodeArtifact("artifact-3", "code-v3", str(tmp_path / "v3")),
        CodeArtifact("artifact-4", "code-v4", str(tmp_path / "v4")),
    ]
    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)
    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.return_value = FeedbackRecord(
        feedback_id="fb-bad",
        decision=False,
        acceptable=False,
        reason="still template-only",
    )
    evolver = CoSTEEREvolver(coder, runner, feedback_analyzer, max_rounds=4)

    evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

    assert coder.develop.call_count == 4
    assert runner.run.call_count == 3


def test_costeer_data_science_coder_reads_feedback(tmp_path) -> None:
    data_science_coder = _load_data_science_coder_class()
    llm_adapter = MagicMock()
    llm_adapter.generate_structured.return_value = SimpleNamespace(
        artifact_id="artifact-ds",
        description="mock generated code",
    )
    coder = data_science_coder(llm_adapter=llm_adapter)
    experiment = ExperimentNode(
        node_id="node-ds",
        run_id="run-ds",
        branch_id="main",
        hypothesis={
            "text": "baseline",
            "_costeer_feedback": "Focus on leakage checks and robust null handling.",
        },
        workspace_ref=str(tmp_path / "workspace-ds"),
    )
    proposal = Proposal(
        proposal_id="proposal-ds",
        summary="Train a baseline model and compare with regularized alternatives",
    )
    scenario = ScenarioContext(
        run_id="run-ds",
        scenario_name="data_science",
        input_payload={"data_source": str(tmp_path / "train.csv")},
        step_config=StepOverrideConfig(),
    )

    artifact = coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
    pipeline_text = (tmp_path / "workspace-ds" / "pipeline.py").read_text(encoding="utf-8")
    coding_prompt_text = llm_adapter.generate_structured.call_args.args[0]

    assert "Previous round feedback" in coding_prompt_text
    assert "leakage checks" in coding_prompt_text
    assert "RandomForestClassifier" in pipeline_text


def test_costeer_knowledge_save_called(tmp_path) -> None:
    experiment, proposal, scenario = _base_inputs(tmp_path)
    coder = MagicMock()
    coder.develop.side_effect = [
        CodeArtifact("artifact-1", "code-v1", str(tmp_path / "v1")),
        CodeArtifact("artifact-2", "code-v2", str(tmp_path / "v2")),
    ]
    runner = MagicMock()
    runner.run.return_value = _eligible_execution_result(tmp_path)
    feedback_analyzer = MagicMock()
    feedback_analyzer.summarize.side_effect = [
        FeedbackRecord(feedback_id="fb-1", decision=False, acceptable=False, reason="fail first"),
        FeedbackRecord(feedback_id="fb-2", decision=True, acceptable=True, reason="pass second"),
    ]
    llm_adapter = MagicMock()
    llm_adapter.complete.return_value = "knowledge"
    memory_service = MagicMock()
    evolver = CoSTEEREvolver(
        coder,
        runner,
        feedback_analyzer,
        max_rounds=3,
        llm_adapter=llm_adapter,
        memory_service=memory_service,
    )

    with patch.object(evolver, "_save_knowledge", wraps=evolver._save_knowledge) as save_mock:
        evolver.evolve(experiment=experiment, proposal=proposal, scenario=scenario)

    assert save_mock.call_count == 1


def test_costeer_single_round_backward_compat(tmp_path) -> None:
    with patch.dict(os.environ, {"RD_AGENT_COSTEER_MAX_ROUNDS": "1"}, clear=False):
        configured_costeer_max_rounds = int(os.environ["RD_AGENT_COSTEER_MAX_ROUNDS"])
    assert configured_costeer_max_rounds == 1

    step_executor = _make_step_executor(tmp_path, costeer_max_rounds=configured_costeer_max_rounds)
    with patch("core.loop.step_executor.CoSTEEREvolver") as evolver_cls:
        _run_step_executor_once(step_executor)
    evolver_cls.assert_not_called()
