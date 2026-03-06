"""Entry point for the R&D Agent scaffold."""

from __future__ import annotations

from artifact_registry import ArtifactRegistry, ArtifactRegistryConfig
from data_models import Event, EventType, ExplorationGraph, NodeRecord, PhaseResultMeta, PlanningContext
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from observability import Observability, ObservabilityConfig
from orchestrator_rd_loop_engine import OrchestratorConfig, OrchestratorRDLoopEngine
from planner import Planner, PlannerConfig
from plugins import build_default_registry
from task_intake_data_splitter import TaskIntakeConfig, TaskIntakeDataSplitter
from trace_store import TraceStore, TraceStoreConfig


def main() -> None:
    print("[Task Intake] start")
    task_intake = TaskIntakeDataSplitter(TaskIntakeConfig())
    task_artifacts = task_intake.prepare_task_artifacts(
        task_id="task-001",
        description="placeholder task description",
        data_source="data-source-placeholder",
        constraints={"time_budget": "short"},
    )
    print("[Task Intake] done")

    orchestrator = OrchestratorRDLoopEngine(OrchestratorConfig(time_budget_seconds=3600.0))
    loop_context = orchestrator.start_loop(task_artifacts.task_spec.task_id)

    planner = Planner(PlannerConfig())
    exploration_manager = ExplorationManager(ExplorationManagerConfig())
    memory_service = MemoryService(MemoryServiceConfig())
    evaluation_service = EvaluationService(EvaluationServiceConfig())
    artifact_registry = ArtifactRegistry(ArtifactRegistryConfig())
    observability = Observability(ObservabilityConfig())
    plugin_registry = build_default_registry()
    run_session = loop_context.run_session
    if run_session is None:
        raise RuntimeError("run_session must be initialized by orchestrator.start_loop")
    plugin_bundle = plugin_registry.create_bundle(run_session.scenario)
    trace_store = TraceStore(TraceStoreConfig())
    event_seq = 0
    branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"

    def record_event(event_type: EventType, step_name: str, payload: dict) -> None:
        nonlocal event_seq
        event_seq += 1
        trace_store.append_event(
            Event(
                event_id=f"{run_session.run_id}-event-{event_seq}",
                run_id=run_session.run_id,
                branch_id=branch_id,
                loop_index=loop_context.loop_state.iteration,
                step_name=step_name,
                event_type=event_type,
                payload=payload,
            )
        )

    scenario_context = plugin_bundle.scenario_plugin.build_context(
        run_session=run_session,
        input_payload={
            "task_id": task_artifacts.task_spec.task_id,
            "task_summary": task_artifacts.task_spec.description,
            "constraints": task_artifacts.task_spec.constraints,
        },
    )
    record_event(
        event_type=EventType.RUN_CREATED,
        step_name="run",
        payload={"scenario": run_session.scenario, "task_id": task_artifacts.task_spec.task_id},
    )

    graph = ExplorationGraph()

    print("[R&D Loop] planning")
    planning_context = PlanningContext(
        loop_state=loop_context.loop_state,
        budget=loop_context.budget,
        history_summary={},
    )
    plan = planner.generate_plan(planning_context)

    print("[R&D Loop] exploration")
    parent_ids = exploration_manager.select_parents(graph, plan)
    context_pack = memory_service.query_context({"task_id": task_artifacts.task_spec.task_id})

    print("[R&D Loop] reasoning")
    proposal = plugin_bundle.proposal_engine.propose(
        task_summary=task_artifacts.task_spec.description,
        context=context_pack,
        parent_ids=parent_ids,
        plan=plan,
        scenario=scenario_context,
    )
    record_event(
        event_type=EventType.HYPOTHESIS_GENERATED,
        step_name="reasoning",
        payload={"proposal_id": proposal.proposal_id},
    )
    experiment = plugin_bundle.experiment_generator.generate(
        proposal=proposal,
        run_session=run_session,
        loop_state=loop_context.loop_state,
        parent_ids=parent_ids,
    )
    record_event(
        event_type=EventType.EXPERIMENT_GENERATED,
        step_name="experiment",
        payload={"node_id": experiment.node_id, "branch_id": experiment.branch_id},
    )

    print("[R&D Loop] development")
    artifact = plugin_bundle.coder.develop(
        experiment=experiment,
        proposal=proposal,
        scenario=scenario_context,
    )
    record_event(
        event_type=EventType.CODING_ROUND,
        step_name="coding",
        payload={"artifact_id": artifact.artifact_id},
    )

    print("[R&D Loop] execution")
    execution_result = plugin_bundle.runner.run(artifact, scenario_context)
    record_event(
        event_type=EventType.EXECUTION_FINISHED,
        step_name="execution",
        payload={"exit_code": execution_result.exit_code},
    )

    print("[R&D Loop] evaluation")
    eval_result = evaluation_service.evaluate_run(execution_result)
    feedback = plugin_bundle.feedback_analyzer.summarize(
        experiment=experiment,
        result=execution_result,
        score=eval_result.score,
    )
    record_event(
        event_type=EventType.FEEDBACK_GENERATED,
        step_name="feedback",
        payload={"feedback_id": feedback.feedback_id, "acceptable": feedback.acceptable},
    )

    print("[R&D Loop] artifact registry")
    _ = artifact_registry.register_artifact(artifact)

    node = NodeRecord(
        node_id="node-1",
        parent_ids=parent_ids,
        proposal_id=proposal.proposal_id,
        artifact_id=artifact.artifact_id,
        score_id=eval_result.score.score_id,
    )
    graph = exploration_manager.register_node(graph, node)

    phase_result = PhaseResultMeta(
        proposal_id=proposal.proposal_id,
        artifact_id=artifact.artifact_id,
        score_id=eval_result.score.score_id,
        notes=feedback.reason,
    )
    record_event(
        event_type=EventType.TRACE_RECORDED,
        step_name="trace",
        payload={"proposal_id": proposal.proposal_id, "score_id": eval_result.score.score_id},
    )
    loop_context = orchestrator.tick_loop(loop_context, phase_result)

    observability.emit_log("loop_completed", {"loop_id": loop_context.loop_state.loop_id})

    loop_context = orchestrator.stop_loop(loop_context)
    print(f"[R&D Loop] stopped (status={loop_context.loop_state.status})")


if __name__ == "__main__":
    main()
