"""Step executor for six-stage loop execution with step checkpoints."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from core.execution import WorkspaceManager
from core.storage import BranchTraceStore
from core.storage.interfaces import EventMetadataStore
from data_models import (
    Event,
    EventType,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    Score,
    StepState,
)
from evaluation_service import EvaluationService
from plugins.contracts import PluginBundle
from service_contracts import StepOverrideConfig, resolve_step_override_config


@dataclass
class StepExecutionResult:
    """Outputs of a single six-stage iteration."""

    proposal: Proposal
    experiment: ExperimentNode
    artifact_id: str
    score: Score
    feedback: FeedbackRecord
    checkpoint_ids: List[str] = field(default_factory=list)


class StepExecutor:
    """Executes propose->experiment->coding->running->feedback->record phases."""

    def __init__(
        self,
        plugin_bundle: PluginBundle,
        evaluation_service: EvaluationService,
        workspace_manager: WorkspaceManager,
        event_store: EventMetadataStore,
        branch_store: Optional[BranchTraceStore] = None,
    ) -> None:
        self._plugin_bundle = plugin_bundle
        self._evaluation_service = evaluation_service
        self._workspace_manager = workspace_manager
        self._event_store = event_store
        self._branch_store = branch_store

    def execute_iteration(
        self,
        run_session: RunSession,
        loop_state: LoopState,
        task_summary: str,
        plan: Plan,
        parent_ids: List[str],
        context_pack,
        source_workspace: Optional[str] = None,
    ) -> StepExecutionResult:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        resolved_parent_ids = list(parent_ids)
        if not resolved_parent_ids:
            fork_parent_node_id = run_session.entry_input.pop("fork_parent_node_id", None)
            if isinstance(fork_parent_node_id, str) and fork_parent_node_id:
                resolved_parent_ids = [fork_parent_node_id]
        effective_step_config = self._resolve_step_config(run_session)
        workspace_id = f"loop-{loop_state.iteration:04d}"
        workspace_path = self._workspace_manager.create_workspace(
            run_session.run_id,
            workspace_id,
            source_path=source_workspace,
        )
        checkpoint_ids: List[str] = []

        def checkpoint(step_name: str) -> None:
            checkpoint_id = f"loop-{loop_state.iteration:04d}-{step_name}"
            self._workspace_manager.create_checkpoint(run_session.run_id, workspace_path, checkpoint_id)
            checkpoint_ids.append(checkpoint_id)

        scenario_context = self._plugin_bundle.scenario_plugin.build_context(
            run_session=run_session,
            input_payload={
                **run_session.entry_input,
                "task_summary": task_summary,
                "loop_index": loop_state.iteration,
                "step_config": effective_step_config.to_dict(),
            },
        )

        proposal = self._plugin_bundle.proposal_engine.propose(
            task_summary=task_summary,
            context=context_pack,
            parent_ids=resolved_parent_ids,
            plan=plan,
            scenario=scenario_context,
        )
        self._workspace_manager.inject_files(
            workspace_path,
            {f"trace/proposal_{loop_state.iteration}.txt": proposal.summary},
        )
        checkpoint("propose")
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="proposing",
            event_type=EventType.HYPOTHESIS_GENERATED,
            payload={
                "proposal_id": proposal.proposal_id,
                "constraints": proposal.constraints,
                "model_config": effective_step_config.proposal.to_dict(),
            },
        )

        experiment = self._plugin_bundle.experiment_generator.generate(
            proposal=proposal,
            run_session=run_session,
            loop_state=loop_state,
            parent_ids=resolved_parent_ids,
        )
        experiment.branch_id = branch_id
        experiment.parent_node_id = resolved_parent_ids[0] if resolved_parent_ids else None
        experiment.workspace_ref = workspace_path
        self._workspace_manager.inject_files(
            workspace_path,
            {f"trace/experiment_{loop_state.iteration}.json": json.dumps(experiment.to_dict(), sort_keys=True)},
        )
        checkpoint("experiment")
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="experiment",
            event_type=EventType.EXPERIMENT_GENERATED,
            payload={"node_id": experiment.node_id, "workspace_ref": experiment.workspace_ref},
        )

        artifact = self._plugin_bundle.coder.develop(
            experiment=experiment,
            proposal=proposal,
            scenario=scenario_context,
        )
        self._workspace_manager.inject_files(
            workspace_path,
            {
                f"trace/coding_{loop_state.iteration}.json": json.dumps(
                    {"artifact_id": artifact.artifact_id, "location": artifact.location},
                    sort_keys=True,
                )
            },
        )
        checkpoint("coding")
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="coding",
            event_type=EventType.CODING_ROUND,
            payload={
                "artifact_id": artifact.artifact_id,
                "description": artifact.description,
                "model_config": effective_step_config.coding.to_dict(),
            },
        )

        execution_result = self._plugin_bundle.runner.run(artifact, scenario_context)
        self._workspace_manager.inject_files(
            workspace_path,
            {f"trace/execution_{loop_state.iteration}.txt": execution_result.logs_ref},
        )
        checkpoint("running")
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="running",
            event_type=EventType.EXECUTION_FINISHED,
            payload={
                "exit_code": execution_result.exit_code,
                "timeout_sec": effective_step_config.running.timeout_sec,
            },
        )

        eval_result = self._evaluation_service.evaluate_run(execution_result)
        if isinstance(experiment.hypothesis, dict):
            experiment.hypothesis["_feedback_model_config"] = effective_step_config.feedback.to_dict()
        feedback = self._plugin_bundle.feedback_analyzer.summarize(
            experiment=experiment,
            result=execution_result,
            score=eval_result.score,
        )
        self._workspace_manager.inject_files(
            workspace_path,
            {f"trace/feedback_{loop_state.iteration}.txt": feedback.reason},
        )
        checkpoint("feedback")
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="feedback",
            event_type=EventType.FEEDBACK_GENERATED,
            payload={
                "feedback_id": feedback.feedback_id,
                "acceptable": feedback.acceptable,
                "reason": feedback.reason,
                "model_config": effective_step_config.feedback.to_dict(),
            },
        )

        checkpoint("record")
        experiment.step_state = StepState.RECORDED
        experiment.result_ref = execution_result.artifacts_ref
        experiment.feedback_ref = feedback.feedback_id
        if self._branch_store is not None:
            self._branch_store.record_node(experiment)
        self._append_event(
            run_id=run_session.run_id,
            branch_id=branch_id,
            loop_index=loop_state.iteration,
            step_name="record",
            event_type=EventType.TRACE_RECORDED,
            payload={"proposal_id": proposal.proposal_id, "score_id": eval_result.score.score_id},
        )

        return StepExecutionResult(
            proposal=proposal,
            experiment=experiment,
            artifact_id=artifact.artifact_id,
            score=eval_result.score,
            feedback=feedback,
            checkpoint_ids=checkpoint_ids,
        )

    def _resolve_step_config(self, run_session: RunSession) -> StepOverrideConfig:
        config_snapshot = run_session.config_snapshot
        if "step_overrides" in config_snapshot:
            effective = resolve_step_override_config(
                self._plugin_bundle.default_step_overrides,
                StepOverrideConfig.from_dict(config_snapshot["step_overrides"]),
            )
            config_snapshot["step_overrides"] = effective.to_dict()
            return effective

        requested = StepOverrideConfig.from_dict(config_snapshot.get("requested_step_overrides"))
        effective = resolve_step_override_config(self._plugin_bundle.default_step_overrides, requested)
        config_snapshot["step_overrides"] = effective.to_dict()
        return effective

    def _append_event(
        self,
        run_id: str,
        branch_id: str,
        loop_index: int,
        step_name: str,
        event_type: EventType,
        payload: dict,
    ) -> None:
        self._event_store.append_event(
            Event(
                event_id=f"event-{uuid.uuid4().hex}",
                run_id=run_id,
                branch_id=branch_id,
                loop_index=loop_index,
                step_name=step_name,
                event_type=event_type,
                payload=payload,
            )
        )
