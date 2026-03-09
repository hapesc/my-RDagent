"""Data Science scenario plugin v1."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.execution import DockerExecutionBackend, DockerExecutionBackendConfig
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
    Score,
    StepState,
)
from llm import (
    CodeDraft,
    FeedbackDraft,
    LLMAdapter,
    ProposalDraft,
    coding_prompt,
    feedback_prompt,
    proposal_prompt,
)
from plugins.contracts import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    PluginBundle,
    ProposalEngine,
    Runner,
    ScenarioContext,
    ScenarioPlugin,
    UsefulnessGateInput,
)
from service_contracts import ModelSelectorConfig, RunningStepConfig, StepOverrideConfig

if TYPE_CHECKING:
    from core.reasoning.pipeline import ReasoningPipeline
    from core.reasoning.virtual_eval import VirtualEvaluator


def default_data_science_step_overrides(timeout_sec: int = 300) -> StepOverrideConfig:
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(provider="mock", model="ds-proposal-default", max_retries=2),
        coding=ModelSelectorConfig(
            provider="mock",
            model="ds-coding-default",
            max_retries=2,
            max_tokens=2048,
        ),
        running=RunningStepConfig(timeout_sec=timeout_sec),
        feedback=ModelSelectorConfig(provider="mock", model="ds-feedback-default", max_retries=2),
    )


@dataclass
class DataScienceV1Config:
    """Configuration for Data Science plugin v1."""

    workspace_root: str = "/tmp/rd_agent_workspace"
    trace_storage_path: str = "/tmp/rd_agent_trace/events.jsonl"
    docker_image: str = "python:3.11-slim"
    prefer_docker: bool = True
    allow_local_execution: bool = False
    default_step_overrides: StepOverrideConfig = field(default_factory=default_data_science_step_overrides)


class DataScienceScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


class DataScienceProposalEngine(ProposalEngine):
    def __init__(
        self,
        llm_adapter: LLMAdapter,
        reasoning_pipeline: ReasoningPipeline | None = None,
        virtual_evaluator: VirtualEvaluator | None = None,
    ) -> None:
        self._llm_adapter = llm_adapter
        self._reasoning_pipeline = reasoning_pipeline
        self._virtual_evaluator = virtual_evaluator

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: list[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        _ = context
        _ = parent_ids
        _ = plan
        summary = task_summary or scenario.task_summary or "data science task"
        iteration = int(scenario.input_payload.get("loop_index", 0))

        if self._virtual_evaluator is not None:
            from core.reasoning.virtual_eval import VirtualEvaluator

            evaluator = self._virtual_evaluator
            if isinstance(evaluator, VirtualEvaluator):
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                designs = evaluator.evaluate(
                    task_summary=summary,
                    scenario_name=scenario.scenario_name,
                    iteration=iteration,
                    previous_results=previous_results,
                    current_scores=current_scores,
                    model_config=scenario.step_config.proposal,
                )
                if designs:
                    best = designs[0]
                    constraints = list(best.constraints)
                    if scenario.step_config.proposal.model:
                        constraints.append(f"model:{scenario.step_config.proposal.model}")
                    return Proposal(
                        proposal_id="proposal-ds-fc3",
                        summary=best.summary,
                        constraints=constraints,
                        virtual_score=best.virtual_score,
                    )

        if self._reasoning_pipeline is not None:
            from core.reasoning.pipeline import ReasoningPipeline

            pipeline = self._reasoning_pipeline
            if isinstance(pipeline, ReasoningPipeline):
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                design = pipeline.reason(
                    task_summary=summary,
                    scenario_name=scenario.scenario_name,
                    iteration=iteration,
                    previous_results=previous_results,
                    current_scores=current_scores,
                    model_config=scenario.step_config.proposal,
                )
                constraints = list(design.constraints)
                if scenario.step_config.proposal.model:
                    constraints.append(f"model:{scenario.step_config.proposal.model}")
                return Proposal(
                    proposal_id="proposal-ds-fc3-pipeline",
                    summary=design.summary,
                    constraints=constraints,
                    virtual_score=design.virtual_score,
                )

        prompt = proposal_prompt(
            task_summary=summary,
            scenario_name=scenario.scenario_name,
            iteration=iteration,
        )
        draft = self._llm_adapter.generate_structured(
            prompt,
            ProposalDraft,
            model_config=scenario.step_config.proposal,
        )
        return Proposal(
            proposal_id="proposal-ds-v1",
            summary=draft.summary,
            constraints=draft.constraints,
            virtual_score=draft.virtual_score,
        )


class DataScienceExperimentGenerator(ExperimentGenerator):
    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = Path(workspace_root)

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: list[str],
    ) -> ExperimentNode:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        parent_node_id: str | None = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{branch_id}-{loop_state.iteration}"
        workspace_ref = self._workspace_root / run_session.run_id / node_id
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "DataScience"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "result"),
            feedback_ref="",
        )


class DataScienceCoder(Coder):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm_adapter = llm_adapter

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)

        data_source = str(scenario.input_payload.get("data_source", ""))
        pipeline_script = self._build_pipeline_script(data_source=data_source)
        readme_text = proposal.summary
        artifact_id = f"artifact-{experiment.node_id}"
        (workspace / "pipeline.py").write_text(pipeline_script, encoding="utf-8")
        if self._llm_adapter is not None:
            prompt = coding_prompt(
                proposal_summary=proposal.summary,
                constraints=proposal.constraints,
                experiment_node_id=experiment.node_id,
                workspace_ref=experiment.workspace_ref,
                scenario_name=scenario.scenario_name,
            )
            code_draft = self._llm_adapter.generate_structured(
                prompt,
                CodeDraft,
                model_config=scenario.step_config.coding,
            )
            artifact_id = code_draft.artifact_id
            readme_text = code_draft.description
        (workspace / "README.txt").write_text(readme_text, encoding="utf-8")

        return CodeArtifact(
            artifact_id=artifact_id,
            description=readme_text,
            location=str(workspace),
        )

    def _build_pipeline_script(self, data_source: str) -> str:
        return (
            "import csv\n"
            "import json\n"
            "import os\n"
            f"data_source = {data_source!r}\n"
            "row_count = 0\n"
            "column_count = 0\n"
            "if data_source and os.path.exists(data_source):\n"
            "    with open(data_source, newline='', encoding='utf-8') as handle:\n"
            "        reader = csv.DictReader(handle)\n"
            "        column_count = len(reader.fieldnames or [])\n"
            "        row_count = sum(1 for _ in reader)\n"
            "metrics = {'row_count': row_count, 'column_count': column_count, 'status': 'ok'}\n"
            "with open('metrics.json', 'w', encoding='utf-8') as handle:\n"
            "    json.dump(metrics, handle)\n"
            "print(json.dumps(metrics))\n"
        )


class DataScienceRunner(Runner):
    def __init__(self, backend: DockerExecutionBackend) -> None:
        self._backend = backend

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        loop_index = int(scenario.input_payload.get("loop_index", 0))
        branch_id = str(scenario.input_payload.get("branch_id", "main"))
        command = str(scenario.input_payload.get("command", "python3 pipeline.py"))
        backend_result = self._backend.execute(
            run_id=scenario.run_id,
            branch_id=branch_id,
            loop_index=loop_index,
            workspace_path=artifact.location,
            command=command,
            timeout_sec=scenario.step_config.running.timeout_sec,
        )
        logs = backend_result.stdout if backend_result.stdout else backend_result.stderr
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=backend_result.exit_code,
            logs_ref=logs,
            artifacts_ref=json.dumps(backend_result.artifact_paths),
            duration_sec=backend_result.duration_sec,
            timed_out=backend_result.timed_out,
            artifact_manifest=backend_result.artifact_manifest,
            outcome=backend_result.outcome,
        )


class DataScienceFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Score | None = None,
    ) -> FeedbackRecord:
        score_text = "none" if score is None else f"{score.metric_name}:{score.value:.4f}"
        hypothesis_text = (
            experiment.hypothesis.get("text", "")
            if isinstance(experiment.hypothesis, dict)
            else str(experiment.hypothesis)
        )
        iteration = experiment.loop_index
        feedback_config = ModelSelectorConfig.from_dict(
            experiment.hypothesis.get("_feedback_model_config") if isinstance(experiment.hypothesis, dict) else None
        )
        prompt = feedback_prompt(
            hypothesis_text=hypothesis_text,
            exit_code=result.exit_code,
            score_text=score_text,
            logs_summary=result.logs_ref,
            iteration=iteration,
        )
        draft = self._llm_adapter.generate_structured(
            prompt,
            FeedbackDraft,
            model_config=feedback_config,
        )
        usefulness_eligible = result.resolve_outcome().usefulness_eligible
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=draft.decision and usefulness_eligible,
            acceptable=draft.acceptable and usefulness_eligible,
            reason=draft.reason,
            observations=draft.observations,
            code_change_summary=draft.code_change_summary,
        )


def _validate_data_science_usefulness(gate_input: UsefulnessGateInput) -> str | None:
    payload = gate_input.structured_payload
    if not isinstance(payload, dict):
        return "missing structured payload"
    if "status" not in payload:
        return "missing key field: status"
    if "row_count" not in payload:
        return "missing key field: row_count"
    status_value = str(payload.get("status", "")).strip().lower()
    if status_value in {"", "todo", "tbd", "placeholder"}:
        return "template-only status"
    row_count = payload.get("row_count")
    if not isinstance(row_count, int):
        return "row_count must be integer"
    if row_count < 0:
        return "row_count cannot be negative"
    if _is_row_count_only_payload(payload):
        return "row-count-only payload"
    if not _has_informative_metrics(payload):
        return "missing informative metrics"
    return None


_DS_NON_INFORMATIVE_KEYS = {
    "status",
    "row_count",
    "result",
    "outcome",
    "message",
    "ok",
    "success",
    "state",
    "detail",
}

_DS_PLACEHOLDER_VALUES = {
    "",
    "todo",
    "tbd",
    "placeholder",
    "template",
    "n/a",
    "na",
    "unknown",
    "null",
}


def _is_row_count_only_payload(payload: dict[str, Any]) -> bool:
    keys = {str(key).strip().lower() for key in payload}
    return bool(keys) and keys.issubset({"status", "row_count"})


def _has_informative_metrics(payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in _DS_NON_INFORMATIVE_KEYS:
            continue
        if _is_informative_value(value):
            return True
    return False


def _is_informative_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        return bool(normalized) and normalized not in _DS_PLACEHOLDER_VALUES
    if isinstance(value, dict):
        return any(_is_informative_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_is_informative_value(item) for item in value)
    return False


def build_data_science_v1_bundle(
    config: DataScienceV1Config | None = None,
    llm_adapter: LLMAdapter | None = None,
    reasoning_pipeline: ReasoningPipeline | None = None,
    virtual_evaluator: VirtualEvaluator | None = None,
) -> PluginBundle:
    """Build Data Science plugin v1 bundle."""

    plugin_config = config or DataScienceV1Config()
    if llm_adapter is None:
        raise RuntimeError(
            "llm_adapter is required for build_data_science_v1_bundle(). "
            "Configure a real LLM provider, e.g.: "
            "LLMAdapter(provider=LiteLLMProvider("
            "api_key=os.environ['OPENAI_API_KEY'], model='gpt-4o-mini'"
            "), config=LLMAdapterConfig(max_retries=2))"
        )
    adapter = llm_adapter
    backend = DockerExecutionBackend(
        DockerExecutionBackendConfig(
            docker_image=plugin_config.docker_image,
            prefer_docker=plugin_config.prefer_docker,
            allow_local_execution=plugin_config.allow_local_execution,
            default_timeout_sec=plugin_config.default_step_overrides.running.timeout_sec or 300,
            trace_storage_path=plugin_config.trace_storage_path,
        )
    )

    return PluginBundle(
        scenario_name="data_science",
        scenario_plugin=DataScienceScenarioPlugin(),
        proposal_engine=DataScienceProposalEngine(
            adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        experiment_generator=DataScienceExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=DataScienceCoder(adapter),
        runner=DataScienceRunner(backend),
        feedback_analyzer=DataScienceFeedbackAnalyzer(adapter),
        scene_usefulness_validator=_validate_data_science_usefulness,
        default_step_overrides=plugin_config.default_step_overrides,
    )
