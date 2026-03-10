"""Synthetic Research scenario plugin bundle."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, List

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
    default_step_overrides: StepOverrideConfig = field(default_factory=default_synthetic_research_step_overrides)


class SyntheticResearchScenarioPlugin(ScenarioPlugin):
    def build_context(self, run_session: RunSession, input_payload: dict[str, Any]) -> ScenarioContext:
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            config={"split_manifest": None},
            task_summary=str(input_payload.get("task_summary", "")),
            step_config=StepOverrideConfig.from_dict(input_payload.get("step_config")),
        )


class SyntheticResearchProposalEngine(ProposalEngine):
    def __init__(
        self,
        llm_adapter: LLMAdapter | None = None,
        reasoning_pipeline: ReasoningPipeline | None = None,
        virtual_evaluator: VirtualEvaluator | None = None,
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
        parent_ids: list[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        summary = task_summary or scenario.task_summary or "synthetic research task"
        highlights = list(getattr(context, "highlights", None) or [])
        scored_items = list(getattr(context, "scored_items", None) or [])
        context_lines: List[str] = [f"- {item}" for item in highlights if str(item).strip()]
        for item, score in scored_items[:3]:
            item_text = str(item).strip()
            if not item_text:
                continue
            try:
                score_text = f"{float(score):.3f}"
            except (TypeError, ValueError):
                score_text = "N/A"
            context_lines.append(f"- {item_text} (score={score_text})")
        if not context_lines:
            context_lines = ["- None"]

        guidance_items = list(getattr(plan, "guidance", None) or []) if plan is not None else []
        guidance_text = (
            "\n".join(f"- {str(item).strip()}" for item in guidance_items if str(item).strip())
            or "No specific guidance"
        )
        parent_text = ", ".join(parent_ids) if parent_ids else "None"
        context_text = "\n".join(context_lines)
        enriched_summary = (
            f"{summary}\n\n"
            f"Prior Context:\n{context_text}\n\n"
            f"Strategic Guidance:\n{guidance_text}\n\n"
            f"Parent Branch Continuity:\n{parent_text}"
        )
        iteration = int(scenario.input_payload.get("loop_index", 0))

        if self._virtual_evaluator is not None:
            from core.reasoning.virtual_eval import VirtualEvaluator

            evaluator = self._virtual_evaluator
            if isinstance(evaluator, VirtualEvaluator):
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                designs = evaluator.evaluate(
                    task_summary=enriched_summary,
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
                previous_results = [str(result) for result in scenario.input_payload.get("previous_results", [])]
                current_scores = [float(score) for score in scenario.input_payload.get("current_scores", [])]
                design = pipeline.reason(
                    task_summary=enriched_summary,
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
                task_summary=enriched_summary,
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
        return Proposal(
            proposal_id="proposal-placeholder",
            summary=enriched_summary,
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
            hypothesis={"text": proposal.summary, "component": "synthetic_research"},
            workspace_ref=str(workspace_ref),
            result_ref=str(workspace_ref / "research_summary.json"),
            feedback_ref="",
        )


class SyntheticResearchCoder(Coder):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm_adapter = llm_adapter

    def _enrich_proposal_with_feedback(self, proposal: Proposal, experiment: ExperimentNode) -> str:
        feedback_text = None
        if isinstance(experiment.hypothesis, dict):
            feedback_text = experiment.hypothesis.get("_costeer_feedback")

        if feedback_text and isinstance(feedback_text, str) and feedback_text.strip():
            return f"{proposal.summary}\n\nPrevious round feedback:\n{feedback_text}"
        return proposal.summary

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)
        brief_lines = [
            "# Synthetic Research Brief",
            "",
            f"Task: {proposal.summary}",
        ]
        topics = scenario.input_payload.get("reference_topics", [])
        if isinstance(topics, list) and topics:
            brief_lines.extend(["", "Reference Topics:"])
            brief_lines.extend([f"- {topic}" for topic in topics])
        brief_text = "\n".join(brief_lines) + "\n"
        artifact_description = proposal.summary

        proposal_summary_with_feedback = self._enrich_proposal_with_feedback(proposal, experiment)

        if self._llm_adapter is not None:
            prompt = coding_prompt(
                proposal_summary=proposal_summary_with_feedback,
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
        debug_config = scenario.config.get("debug_config")
        _ = debug_config
        workspace = Path(artifact.location)
        summary_path = workspace / "research_summary.json"
        topics = scenario.input_payload.get("reference_topics", [])
        if not isinstance(topics, list):
            topics = []
        normalized_task = str(scenario.task_summary or "synthetic research task").strip()
        primary_topic = str(topics[0]).strip() if topics else "core objective"
        secondary_topic = str(topics[1]).strip() if len(topics) > 1 else "baseline behavior"
        synthesized_findings = [
            (
                f"Compared to {secondary_topic}, {primary_topic} appears most relevant to {normalized_task} "
                "because it aligns with the requested scope and constraints."
            ),
            (
                f"A practical trade-off is to prioritize {primary_topic} evidence first, then expand to "
                f"{secondary_topic} to reduce coverage risk while keeping iteration cost bounded."
            ),
        ]
        payload = {
            "scenario": scenario.scenario_name,
            "task_summary": scenario.task_summary,
            "topic_count": len(topics),
            "topics": topics,
            "artifact_id": artifact.artifact_id,
            "synthesized_summary": synthesized_findings[0],
            "synthesized_findings": synthesized_findings,
        }
        summary_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref="synthetic research complete",
            artifacts_ref=json.dumps([str(summary_path)]),
        )


class SyntheticResearchFeedbackAnalyzer(FeedbackAnalyzer):
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self._llm_adapter = llm_adapter

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Score | None = None,
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


def _validate_synthetic_research_usefulness(gate_input: UsefulnessGateInput) -> str | None:
    payload = gate_input.structured_payload
    if not isinstance(payload, dict):
        return "missing structured payload"
    required_fields = ("task_summary", "artifact_id", "topic_count")
    for field_name in required_fields:
        if field_name not in payload:
            return f"missing key field: {field_name}"
    task_summary = str(payload.get("task_summary", "")).strip().lower()
    if task_summary in {"", "todo", "tbd", "placeholder"}:
        return "template-only task_summary"
    topic_count = payload.get("topic_count")
    if not isinstance(topic_count, int):
        return "topic_count must be integer"
    if topic_count < 0:
        return "topic_count cannot be negative"
    synthesized_summary = str(payload.get("synthesized_summary", "")).strip()
    if not synthesized_summary:
        return "missing synthesized summary"
    lowered_summary = synthesized_summary.lower()
    if _is_generic_synthetic_text(lowered_summary):
        return "generic synthesized summary"
    if _is_prompt_echo(lowered_summary, task_summary):
        return "prompt-echo synthesized summary"

    findings = payload.get("synthesized_findings")
    if not isinstance(findings, list):
        return "missing synthesized findings"
    normalized_findings = [str(item).strip().lower() for item in findings if str(item).strip()]
    if not normalized_findings:
        return "empty synthesized findings"
    if all(_is_generic_synthetic_text(item) for item in normalized_findings):
        return "template-only synthesized findings"
    if all(_is_prompt_echo(item, task_summary) for item in normalized_findings):
        return "prompt-echo synthesized findings"
    if not _has_task_specific_synthesis(task_summary, payload, normalized_findings):
        return "missing task-specific synthesis"
    return None


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
}

_GENERIC_SNIPPETS = {
    "no findings",
    "no meaningful findings",
    "placeholder",
    "template",
    "todo",
    "tbd",
    "n/a",
}

_SYNTHESIS_MARKERS = (
    "because",
    "therefore",
    "however",
    "trade-off",
    "tradeoff",
    "compared",
    "evidence",
    "risk",
    "impact",
    "suggests",
    "indicates",
)


def _is_generic_synthetic_text(text: str) -> bool:
    if not text.strip():
        return True
    compact = " ".join(text.split())
    if compact in {"summary", "synthesized summary", "findings", "research findings"}:
        return True
    return any(token in compact for token in _GENERIC_SNIPPETS)


def _is_prompt_echo(candidate: str, normalized_task_summary: str) -> bool:
    cleaned = " ".join(candidate.split())
    if not cleaned:
        return True
    if cleaned == normalized_task_summary:
        return True
    return bool(
        normalized_task_summary
        and cleaned
        in {
            f"task: {normalized_task_summary}",
            f"task summary: {normalized_task_summary}",
            f"research task: {normalized_task_summary}",
        }
    )


def _tokenize_significant(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return {token for token in tokens if len(token) >= 4 and token not in _STOPWORDS}


def _has_task_specific_synthesis(
    normalized_task_summary: str,
    payload: dict[str, Any],
    normalized_findings: list[str],
) -> bool:
    topic_tokens: set[str] = set()
    topics = payload.get("topics")
    if isinstance(topics, list):
        for topic in topics:
            topic_tokens.update(_tokenize_significant(str(topic)))
    task_tokens = _tokenize_significant(normalized_task_summary)
    target_tokens = task_tokens.union(topic_tokens)
    findings_text = " ".join(normalized_findings)
    finding_tokens = _tokenize_significant(findings_text)
    if target_tokens and not (target_tokens & finding_tokens):
        return False
    return any(marker in findings_text for marker in _SYNTHESIS_MARKERS)


def build_synthetic_research_bundle(
    config: SyntheticResearchConfig | None = None,
    llm_adapter: LLMAdapter | None = None,
    reasoning_pipeline: ReasoningPipeline | None = None,
    virtual_evaluator: VirtualEvaluator | None = None,
) -> PluginBundle:
    """Build the formal synthetic research plugin bundle."""

    plugin_config = config or SyntheticResearchConfig()
    if llm_adapter is None:
        raise RuntimeError(
            "llm_adapter is required for build_synthetic_research_bundle(). "
            "Configure a real LLM provider, e.g.: "
            "LLMAdapter(provider=LiteLLMProvider("
            "api_key=os.environ['OPENAI_API_KEY'], model='gpt-4o-mini'"
            "), config=LLMAdapterConfig(max_retries=2))"
        )
    adapter = llm_adapter
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
        scene_usefulness_validator=_validate_synthetic_research_usefulness,
        default_step_overrides=plugin_config.default_step_overrides,
    )
