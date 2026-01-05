"""Entry point for the R&D Agent scaffold."""

from __future__ import annotations

from artifact_registry import ArtifactRegistry, ArtifactRegistryConfig
from data_models import ExplorationGraph, NodeRecord, PhaseResultMeta, PlanningContext
from development_service import DevelopmentService, DevelopmentServiceConfig
from evaluation_service import EvaluationService, EvaluationServiceConfig
from execution_service import ExecutionService, ExecutionServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from observability import Observability, ObservabilityConfig
from orchestrator_rd_loop_engine import OrchestratorConfig, OrchestratorRDLoopEngine
from planner import Planner, PlannerConfig
from reasoning_service import ReasoningService, ReasoningServiceConfig
from task_intake_data_splitter import TaskIntakeConfig, TaskIntakeDataSplitter


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
    reasoning_service = ReasoningService(ReasoningServiceConfig())
    development_service = DevelopmentService(DevelopmentServiceConfig())
    execution_service = ExecutionService(ExecutionServiceConfig())
    evaluation_service = EvaluationService(EvaluationServiceConfig())
    artifact_registry = ArtifactRegistry(ArtifactRegistryConfig())
    observability = Observability(ObservabilityConfig())

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
    proposal = reasoning_service.generate_proposal(
        task_summary=task_artifacts.task_spec.description,
        context=context_pack,
        parent_ids=parent_ids,
        plan=plan,
    )

    print("[R&D Loop] development")
    artifact = development_service.build_solution(proposal)

    print("[R&D Loop] execution")
    execution_result = execution_service.execute_artifact(artifact)

    print("[R&D Loop] evaluation")
    eval_result = evaluation_service.evaluate_run(execution_result)

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
        notes="placeholder",
    )
    loop_context = orchestrator.tick_loop(loop_context, phase_result)

    observability.emit_log("loop_completed", {"loop_id": loop_context.loop_state.loop_id})

    loop_context = orchestrator.stop_loop(loop_context)
    print(f"[R&D Loop] stopped (status={loop_context.loop_state.status})")


if __name__ == "__main__":
    main()
