"""Synthetic Research scenario plugin bundle."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
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
from llm import CodeDraft, FeedbackDraft, LLMAdapter, LLMAdapterConfig, MockLLMProvider, ProposalDraft
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
from reasoning_service import ReasoningService, ReasoningServiceConfig
from service_contracts import ModelSelectorConfig, RunningStepConfig, StepOverrideConfig


def default_synthetic_research_step_overrides(timeout_sec: int = 300) -> StepOverrideConfig:
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(provider="mock", model="synthetic-proposal-default", max_retries=2),
        coding=ModelSelectorConfig(
            provider="mock",
            model="synthetic-coding-default",
            max_retries=2,
            max_tokens=512,
        ),
        running=RunningStepConfig(timeout_sec=timeout_sec),
        feedback=ModelSelectorConfig(provider="mock", model="synthetic-feedback-default", max_retries=2),
    )


@dataclass
class SyntheticResearchConfig:
    """Configuration for the formal synthetic research scenario."""

    workspace_root: str = "/tmp/rd_agent_workspace"
    default_step_overrides: StepOverrideConfig = field(
        default_factory=default_synthetic_research_step_overrides
    )


class SyntheticResearchScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: Dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


class SyntheticResearchProposalEngine(ProposalEngine):
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
        summary = task_summary or scenario.task_summary or "synthetic research task"
        if self._llm_adapter is not None:
            draft = self._llm_adapter.generate_structured(
                f"proposal:{summary}",
                ProposalDraft,
                model_config=scenario.step_config.proposal,
            )
            return Proposal(
                proposal_id="proposal-llm",
                summary=draft.summary,
                constraints=draft.constraints + ["synthetic_research"],
                virtual_score=draft.virtual_score,
            )
        return self._reasoning_service.generate_proposal(
            task_summary=summary,
            context=context,
            parent_ids=parent_ids,
            plan=plan,
        )


class SyntheticResearchExperimentGenerator(ExperimentGenerator):
    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = Path(workspace_root)

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: List[str],
    ) -> ExperimentNode:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        parent_node_id: Optional[str] = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{branch_id}-{loop_state.iteration}"
        workspace_ref = self._workspace_root / run_session.run_id / node_id
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary, "component": "synthetic_research"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "research_summary.json"),
            feedback_ref="",
        )


class SyntheticResearchCoder(Coder):
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None) -> None:
        self._llm_adapter = llm_adapter

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)
        brief_lines = [
            f"# Synthetic Research Brief",
            "",
            f"Task: {proposal.summary}",
        ]
        topics = scenario.input_payload.get("reference_topics", [])
        if isinstance(topics, list) and topics:
            brief_lines.extend(["", "Reference Topics:"])
            brief_lines.extend([f"- {topic}" for topic in topics])
        brief_text = "\n".join(brief_lines) + "\n"
        artifact_description = proposal.summary
        if self._llm_adapter is not None:
            draft = self._llm_adapter.generate_structured(
                f"coding:{proposal.summary}",
                CodeDraft,
                model_config=scenario.step_config.coding,
            )
            (workspace / "research_notes.txt").write_text(draft.description, encoding="utf-8")
            artifact_id = draft.artifact_id
            artifact_description = draft.description
        else:
            artifact_id = f"artifact-{experiment.node_id}"
        (workspace / "research_brief.md").write_text(brief_text, encoding="utf-8")
        return CodeArtifact(
            artifact_id=artifact_id,
            description=artifact_description,
            location=str(workspace),
        )


class SyntheticResearchRunner(Runner):
    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        workspace = Path(artifact.location)
        summary_path = workspace / "research_summary.json"
        topics = scenario.input_payload.get("reference_topics", [])
        if not isinstance(topics, list):
            topics = []
        payload = {
            "scenario": scenario.scenario_name,
            "task_summary": scenario.task_summary,
            "topic_count": len(topics),
            "topics": topics,
            "artifact_id": artifact.artifact_id,
        }
        summary_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref="synthetic research complete",
            artifacts_ref=json.dumps([str(summary_path)]),
        )


class SyntheticResearchFeedbackAnalyzer(FeedbackAnalyzer):
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
            feedback_config = ModelSelectorConfig.from_dict(
                experiment.hypothesis.get("_feedback_model_config")
                if isinstance(experiment.hypothesis, dict)
                else None
            )
            draft = self._llm_adapter.generate_structured(
                f"feedback:exit_code={result.exit_code};score={score_text}",
                FeedbackDraft,
                model_config=feedback_config,
            )
            return FeedbackRecord(
                feedback_id=f"fb-{experiment.node_id}",
                decision=draft.decision,
                acceptable=draft.acceptable,
                reason=draft.reason,
                observations=draft.observations,
                code_change_summary=draft.code_change_summary,
            )

        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=result.exit_code == 0,
            acceptable=result.exit_code == 0,
            reason=f"synthetic exit_code={result.exit_code}",
            observations=f"artifacts_ref={result.artifacts_ref}",
            code_change_summary=experiment.hypothesis.get("text", ""),
        )


def build_synthetic_research_bundle(config: Optional[SyntheticResearchConfig] = None) -> PluginBundle:
    """Build the formal synthetic research plugin bundle."""

    plugin_config = config or SyntheticResearchConfig()
    reasoning_service = ReasoningService(
        ReasoningServiceConfig(reasoning_policy="synthetic_research_pipeline")
    )
    llm_adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=2))
    return PluginBundle(
        scenario_name="synthetic_research",
        scenario_plugin=SyntheticResearchScenarioPlugin(),
        proposal_engine=SyntheticResearchProposalEngine(reasoning_service, llm_adapter=llm_adapter),
        experiment_generator=SyntheticResearchExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=SyntheticResearchCoder(llm_adapter=llm_adapter),
        runner=SyntheticResearchRunner(),
        feedback_analyzer=SyntheticResearchFeedbackAnalyzer(llm_adapter=llm_adapter),
        default_step_overrides=plugin_config.default_step_overrides,
    )
