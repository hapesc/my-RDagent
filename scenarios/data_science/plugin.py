"""Data Science scenario plugin v1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from llm import FeedbackDraft, LLMAdapter, LLMAdapterConfig, MockLLMProvider, ProposalDraft
from plugins.contracts import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    PluginBundle,
    ProposalEngine,
    Runner,
    ScenarioContext,
    ScenarioPlugin,
)


@dataclass
class DataScienceV1Config:
    """Configuration for Data Science plugin v1."""

    workspace_root: str = "/tmp/rd_agent_workspace"
    trace_storage_path: str = "/tmp/rd_agent_trace/events.jsonl"
    docker_image: str = "python:3.11-slim"
    prefer_docker: bool = True


class DataScienceScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: Dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "")),
        )


class DataScienceProposalEngine(ProposalEngine):
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: List[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        _ = context
        _ = parent_ids
        _ = plan
        summary = task_summary or scenario.task_summary or "data science task"
        draft = self._llm_adapter.generate_structured(f"proposal:{summary}", ProposalDraft)
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
        parent_ids: List[str],
    ) -> ExperimentNode:
        parent_node_id: Optional[str] = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{loop_state.iteration}"
        workspace_ref = self._workspace_root / run_session.run_id / node_id
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=run_session.active_branch_ids[0] if run_session.active_branch_ids else "main",
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "DataScience"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "result"),
            feedback_ref="",
        )


class DataScienceCoder(Coder):
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
        (workspace / "pipeline.py").write_text(pipeline_script, encoding="utf-8")
        (workspace / "README.txt").write_text(proposal.summary, encoding="utf-8")

        return CodeArtifact(
            artifact_id=f"artifact-{experiment.node_id}",
            description=proposal.summary,
            location=str(workspace),
        )

    def _build_pipeline_script(self, data_source: str) -> str:
        return (
            "import csv\n"
            "import json\n"
            "import os\n"
            f"data_source = {data_source!r}\n"
            "row_count = 0\n"
            "if data_source and os.path.exists(data_source):\n"
            "    with open(data_source, newline='', encoding='utf-8') as handle:\n"
            "        reader = csv.DictReader(handle)\n"
            "        row_count = sum(1 for _ in reader)\n"
            "metrics = {'row_count': row_count, 'status': 'ok'}\n"
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
        )
        logs = backend_result.stdout if backend_result.stdout else backend_result.stderr
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=backend_result.exit_code,
            logs_ref=logs,
            artifacts_ref=json.dumps(backend_result.artifact_paths),
        )


class DataScienceFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Optional[Score] = None,
    ) -> FeedbackRecord:
        _ = score
        prompt = f"feedback:exit_code={result.exit_code};logs={result.logs_ref[:120]}"
        draft = self._llm_adapter.generate_structured(prompt, FeedbackDraft)
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=draft.decision and result.exit_code == 0,
            acceptable=draft.acceptable and result.exit_code == 0,
            reason=draft.reason,
            observations=draft.observations,
            code_change_summary=draft.code_change_summary,
        )


def build_data_science_v1_bundle(config: Optional[DataScienceV1Config] = None) -> PluginBundle:
    """Build Data Science plugin v1 bundle."""

    plugin_config = config or DataScienceV1Config()
    llm_adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=2))
    backend = DockerExecutionBackend(
        DockerExecutionBackendConfig(
            docker_image=plugin_config.docker_image,
            prefer_docker=plugin_config.prefer_docker,
            trace_storage_path=plugin_config.trace_storage_path,
        )
    )

    return PluginBundle(
        scenario_name="data_science",
        scenario_plugin=DataScienceScenarioPlugin(),
        proposal_engine=DataScienceProposalEngine(llm_adapter),
        experiment_generator=DataScienceExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=DataScienceCoder(),
        runner=DataScienceRunner(backend),
        feedback_analyzer=DataScienceFeedbackAnalyzer(llm_adapter),
    )
