"""Minimal loadable Data Science plugin bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
from development_service import DevelopmentService, DevelopmentServiceConfig
from execution_service import ExecutionService, ExecutionServiceConfig
from llm import CodeDraft, FeedbackDraft, LLMAdapter, LLMAdapterConfig, MockLLMProvider, ProposalDraft
from reasoning_service import ReasoningService, ReasoningServiceConfig

from ..contracts import (
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
class MinimalDataSciencePluginConfig:
    """Optional config for minimal data science plugin."""

    workspace_root: str = "/tmp/rd_agent_workspace"


class MinimalScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: Dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "")),
        )


class MinimalProposalEngine(ProposalEngine):
    def __init__(
        self,
        reasoning_service: ReasoningService,
        llm_adapter: Optional[LLMAdapter] = None,
    ) -> None:
        self._reasoning_service = reasoning_service
        self._llm_adapter = llm_adapter

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: List[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        summary = task_summary or scenario.task_summary or "data science task"
        if self._llm_adapter is not None:
            draft = self._llm_adapter.generate_structured(f"proposal:{summary}", ProposalDraft)
            return Proposal(
                proposal_id="proposal-llm",
                summary=draft.summary,
                constraints=draft.constraints,
                virtual_score=draft.virtual_score,
            )
        return self._reasoning_service.generate_proposal(
            task_summary=summary,
            context=context,
            parent_ids=parent_ids,
            plan=plan,
        )


class MinimalExperimentGenerator(ExperimentGenerator):
    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: List[str],
    ) -> ExperimentNode:
        parent_node_id: Optional[str] = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{loop_state.iteration}"
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=run_session.active_branch_ids[0] if run_session.active_branch_ids else "main",
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "baseline"},
            workspace_ref=f"artifacts/{run_session.run_id}/{node_id}/workspace",
            result_ref=f"artifacts/{run_session.run_id}/{node_id}/result",
            feedback_ref="",
        )


class MinimalCoder(Coder):
    def __init__(
        self,
        development_service: DevelopmentService,
        llm_adapter: Optional[LLMAdapter] = None,
    ) -> None:
        self._development_service = development_service
        self._llm_adapter = llm_adapter

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        _ = experiment
        _ = scenario
        if self._llm_adapter is not None:
            draft = self._llm_adapter.generate_structured(f"coding:{proposal.summary}", CodeDraft)
            return CodeArtifact(
                artifact_id=draft.artifact_id,
                description=draft.description,
                location=draft.location,
            )
        return self._development_service.build_solution(proposal)


class MinimalRunner(Runner):
    def __init__(self, execution_service: ExecutionService) -> None:
        self._execution_service = execution_service

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        _ = scenario
        return self._execution_service.execute_artifact(artifact)


class MinimalFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None) -> None:
        self._llm_adapter = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Optional[Score] = None,
    ) -> FeedbackRecord:
        if self._llm_adapter is not None:
            score_text = "none" if score is None else f"{score.metric_name}:{score.value:.4f}"
            draft = self._llm_adapter.generate_structured(
                f"feedback:exit_code={result.exit_code};score={score_text}",
                FeedbackDraft,
            )
            return FeedbackRecord(
                feedback_id=f"fb-{experiment.node_id}",
                decision=draft.decision,
                acceptable=draft.acceptable,
                reason=draft.reason,
                observations=draft.observations,
                code_change_summary=draft.code_change_summary,
            )

        improved = score is None or score.value >= 0.0
        reason_parts = [f"exit_code={result.exit_code}"]
        if score is not None:
            reason_parts.append(f"{score.metric_name}={score.value:.4f}")
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=result.exit_code == 0,
            acceptable=result.exit_code == 0 and improved,
            reason="; ".join(reason_parts),
            observations=f"logs_ref={result.logs_ref}",
            code_change_summary=experiment.hypothesis.get("text", ""),
        )


def build_minimal_data_science_bundle(config: Optional[MinimalDataSciencePluginConfig] = None) -> PluginBundle:
    """Build a minimal data science plugin bundle that can be loaded by registry."""

    plugin_config = config or MinimalDataSciencePluginConfig()
    reasoning_service = ReasoningService(ReasoningServiceConfig())
    development_service = DevelopmentService(
        DevelopmentServiceConfig(workspace_root=plugin_config.workspace_root)
    )
    execution_service = ExecutionService(ExecutionServiceConfig(max_runtime_seconds=300))
    llm_adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=2))

    return PluginBundle(
        scenario_name="data_science",
        scenario_plugin=MinimalScenarioPlugin(),
        proposal_engine=MinimalProposalEngine(reasoning_service, llm_adapter=llm_adapter),
        experiment_generator=MinimalExperimentGenerator(),
        coder=MinimalCoder(development_service, llm_adapter=llm_adapter),
        runner=MinimalRunner(execution_service),
        feedback_analyzer=MinimalFeedbackAnalyzer(llm_adapter=llm_adapter),
    )
