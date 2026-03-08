"""Synthetic Research scenario plugin bundle."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

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
    LLMAdapterConfig,
    MockLLMProvider,
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
)
from service_contracts import ModelSelectorConfig, RunningStepConfig, StepOverrideConfig

if TYPE_CHECKING:
    from core.reasoning.pipeline import ReasoningPipeline
    from core.reasoning.virtual_eval import VirtualEvaluator


def default_synthetic_research_step_overrides(timeout_sec: int = 300) -> StepOverrideConfig:
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(provider="mock", model="synthetic-proposal-default", max_retries=2),
        coding=ModelSelectorConfig(
            provider="mock",
            model="synthetic-coding-default",
            max_retries=2,
            max_tokens=2048,
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
        llm_adapter: Optional[LLMAdapter] = None,
        reasoning_pipeline: Optional["ReasoningPipeline"] = None,
        virtual_evaluator: Optional["VirtualEvaluator"] = None,
        fallback_policy: str = "synthetic_research_pipeline",
    ) -> None:
        self._llm_adapter = llm_adapter
        self._reasoning_pipeline = reasoning_pipeline
        self._virtual_evaluator = virtual_evaluator
        self._fallback_policy = fallback_policy

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: List[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        summary = task_summary or scenario.task_summary or "synthetic research task"
        iteration = int(scenario.input_payload.get("loop_index", 0))

        if self._virtual_evaluator is not None:
            from core.reasoning.virtual_eval import VirtualEvaluator

            evaluator = self._virtual_evaluator
            if isinstance(evaluator, VirtualEvaluator):
                previous_results = [
                    str(result) for result in scenario.input_payload.get("previous_results", [])
                ]
                current_scores = [
                    float(score) for score in scenario.input_payload.get("current_scores", [])
                ]
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
                        proposal_id="proposal-synthetic-fc3",
                        summary=best.summary,
                        constraints=constraints,
                        virtual_score=best.virtual_score,
                    )

        if self._reasoning_pipeline is not None:
            from core.reasoning.pipeline import ReasoningPipeline

            pipeline = self._reasoning_pipeline
            if isinstance(pipeline, ReasoningPipeline):
                previous_results = [
                    str(result) for result in scenario.input_payload.get("previous_results", [])
                ]
                current_scores = [
                    float(score) for score in scenario.input_payload.get("current_scores", [])
                ]
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
                    proposal_id="proposal-synthetic-fc3-pipeline",
                    summary=design.summary,
                    constraints=constraints,
                    virtual_score=design.virtual_score,
                )

        if self._llm_adapter is not None:
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
                proposal_id="proposal-llm",
                summary=draft.summary,
                constraints=draft.constraints + ["synthetic_research"],
                virtual_score=draft.virtual_score,
            )
        _ = context
        _ = parent_ids
        _ = plan
        return Proposal(
            proposal_id="proposal-placeholder",
            summary=summary,
            constraints=[self._fallback_policy],
            virtual_score=0.0,
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
            prompt = coding_prompt(
                proposal_summary=proposal.summary,
                constraints=proposal.constraints,
                experiment_node_id=experiment.node_id,
                workspace_ref=experiment.workspace_ref,
                scenario_name=scenario.scenario_name,
            )
            draft = self._llm_adapter.generate_structured(
                prompt,
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
            hypothesis_text = (
                experiment.hypothesis.get("text", "")
                if isinstance(experiment.hypothesis, dict)
                else str(experiment.hypothesis)
            )
            iteration = experiment.loop_index
            feedback_config = ModelSelectorConfig.from_dict(
                experiment.hypothesis.get("_feedback_model_config")
                if isinstance(experiment.hypothesis, dict)
                else None
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


def build_synthetic_research_bundle(
    config: Optional[SyntheticResearchConfig] = None,
    llm_adapter: Optional[LLMAdapter] = None,
    reasoning_pipeline: Optional["ReasoningPipeline"] = None,
    virtual_evaluator: Optional["VirtualEvaluator"] = None,
) -> PluginBundle:
    """Build the formal synthetic research plugin bundle."""

    plugin_config = config or SyntheticResearchConfig()
    adapter = llm_adapter or LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=2))
    return PluginBundle(
        scenario_name="synthetic_research",
        scenario_plugin=SyntheticResearchScenarioPlugin(),
        proposal_engine=SyntheticResearchProposalEngine(
            llm_adapter=adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        experiment_generator=SyntheticResearchExperimentGenerator(workspace_root=plugin_config.workspace_root),
        coder=SyntheticResearchCoder(llm_adapter=adapter),
        runner=SyntheticResearchRunner(),
        feedback_analyzer=SyntheticResearchFeedbackAnalyzer(llm_adapter=adapter),
        default_step_overrides=plugin_config.default_step_overrides,
    )
