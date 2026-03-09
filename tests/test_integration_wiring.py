from __future__ import annotations

from unittest.mock import Mock

from core.loop import LoopEngine, LoopEngineConfig, StepExecutionResult
from data_models import (
    BranchState,
    ExperimentNode,
    ExplorationGraph,
    FeedbackRecord,
    NodeRecord,
    Plan,
    Proposal,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from exploration_manager import ExplorationManager, ExplorationManagerConfig


def _make_step_result(node_id: str, parent_node_id: str | None = None) -> StepExecutionResult:
    return StepExecutionResult(
        proposal=Proposal(proposal_id=f"proposal-{node_id}", summary="summary"),
        experiment=ExperimentNode(
            node_id=node_id,
            run_id="run-wiring",
            branch_id="main",
            parent_node_id=parent_node_id,
        ),
        artifact_id=f"artifact-{node_id}",
        score=Score(score_id=f"score-{node_id}", value=1.0, metric_name="acc"),
        feedback=FeedbackRecord(
            feedback_id=f"feedback-{node_id}",
            decision=True,
            acceptable=True,
            reason="ok",
        ),
    )


def _make_run(max_loops: int = 1) -> RunSession:
    return RunSession(
        run_id="run-wiring",
        scenario="data_science",
        status=RunStatus.CREATED,
        stop_conditions=StopConditions(max_loops=max_loops, max_duration_sec=120),
    )


def test_select_parents_delegates_to_scheduler() -> None:
    scheduler = Mock()
    scheduler.select_node.return_value = "node-1"
    manager = ExplorationManager(ExplorationManagerConfig(), scheduler=scheduler)

    selected = manager.select_parents(ExplorationGraph(), Plan(plan_id="p1"))

    assert selected == ["node-1"]
    scheduler.select_node.assert_called_once()


def test_select_parents_without_scheduler_returns_empty() -> None:
    manager = ExplorationManager(ExplorationManagerConfig())

    selected = manager.select_parents(ExplorationGraph(), Plan(plan_id="p1"))

    assert selected == []


def test_get_frontier_returns_active_nodes() -> None:
    manager = ExplorationManager(ExplorationManagerConfig())
    graph = ExplorationGraph(
        nodes=[
            NodeRecord(node_id="active-1", branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="pruned-1", branch_state=BranchState.PRUNED),
            NodeRecord(node_id="active-2", branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="merged-1", branch_state=BranchState.MERGED),
        ]
    )

    frontier = manager.get_frontier(graph, criteria={"any": "value"})

    assert frontier == ["active-1", "active-2"]


def test_get_frontier_without_nodes_returns_empty() -> None:
    manager = ExplorationManager(ExplorationManagerConfig())

    frontier = manager.get_frontier(ExplorationGraph(), criteria={})

    assert frontier == []


def test_prune_branches_delegates_to_pruner() -> None:
    pruner = Mock()
    graph = ExplorationGraph(nodes=[NodeRecord(node_id="n1")])
    pruned_graph = ExplorationGraph(nodes=[NodeRecord(node_id="n1", branch_state=BranchState.PRUNED)])
    pruner.prune.return_value = pruned_graph
    manager = ExplorationManager(ExplorationManagerConfig(), pruner=pruner)

    result = manager.prune_branches(graph)

    assert result is pruned_graph
    pruner.prune.assert_called_once_with(graph)


def test_prune_branches_without_pruner_is_noop() -> None:
    graph = ExplorationGraph(nodes=[NodeRecord(node_id="n1")])
    manager = ExplorationManager(ExplorationManagerConfig())

    result = manager.prune_branches(graph)

    assert result is graph


def test_merge_traces_delegates_to_merger() -> None:
    merger = Mock()
    merged_design = object()
    merger.merge.return_value = merged_design
    manager = ExplorationManager(ExplorationManagerConfig(), merger=merger)
    graph = ExplorationGraph(
        nodes=[
            NodeRecord(node_id="n1", proposal_id="p1", score=0.5, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", proposal_id="p2", score=0.8, branch_state=BranchState.ACTIVE),
        ]
    )

    result = manager.merge_traces(graph, task_summary="task", scenario_name="data_science")

    assert result is merged_design
    merger.merge.assert_called_once()
    traces_arg, task_arg, scenario_arg = merger.merge.call_args[0]
    assert len(traces_arg) == 2
    assert traces_arg[0]["node_id"] == "n1"
    assert traces_arg[1]["node_id"] == "n2"
    assert task_arg == "task"
    assert scenario_arg == "data_science"


def test_merge_traces_without_merger_returns_none() -> None:
    manager = ExplorationManager(ExplorationManagerConfig())
    graph = ExplorationGraph(nodes=[NodeRecord(node_id="n1", branch_state=BranchState.ACTIVE)])

    result = manager.merge_traces(graph, task_summary="task", scenario_name="data_science")

    assert result is None


def test_engine_calls_prune_after_register_no_scheduler_path() -> None:
    planner = Mock()
    planner.generate_plan.return_value = Plan(plan_id="plan-1")
    exploration_manager = Mock()
    exploration_manager.select_parents.return_value = []
    exploration_manager.register_node.side_effect = lambda graph, node: graph
    exploration_manager.prune_branches.side_effect = lambda graph: graph

    memory_service = Mock()
    memory_service.query_context.return_value = Mock(items=[])

    step_executor = Mock()
    step_executor.execute_iteration.return_value = _make_step_result("n1")

    engine = LoopEngine(
        config=LoopEngineConfig(),
        planner=planner,
        exploration_manager=exploration_manager,
        memory_service=memory_service,
        step_executor=step_executor,
        run_store=Mock(),
        event_store=Mock(),
        scheduler=None,
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="wiring", max_loops=1)

    register_index = next(i for i, call in enumerate(exploration_manager.mock_calls) if call[0] == "register_node")
    prune_index = next(i for i, call in enumerate(exploration_manager.mock_calls) if call[0] == "prune_branches")
    assert register_index < prune_index


def test_engine_calls_prune_after_register_scheduler_path() -> None:
    planner = Mock()
    planner.generate_plan.return_value = Plan(plan_id="plan-1")
    exploration_manager = Mock()
    exploration_manager.register_node.side_effect = lambda graph, node: graph
    exploration_manager.prune_branches.side_effect = lambda graph: graph

    scheduler = Mock()
    scheduler.select_node.return_value = "root-a"

    memory_service = Mock()
    memory_service.query_context.return_value = Mock(items=[])

    step_executor = Mock()
    step_executor.execute_iteration.return_value = _make_step_result("n1")

    engine = LoopEngine(
        config=LoopEngineConfig(branches_per_iteration=1),
        planner=planner,
        exploration_manager=exploration_manager,
        memory_service=memory_service,
        step_executor=step_executor,
        run_store=Mock(),
        event_store=Mock(),
        scheduler=scheduler,
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="wiring", max_loops=1)

    register_index = next(i for i, call in enumerate(exploration_manager.mock_calls) if call[0] == "register_node")
    prune_index = next(i for i, call in enumerate(exploration_manager.mock_calls) if call[0] == "prune_branches")
    assert register_index < prune_index


def test_backward_compat_none_components() -> None:
    manager = ExplorationManager(ExplorationManagerConfig())
    graph = ExplorationGraph()

    selected = manager.select_parents(graph, Plan(plan_id="plan-1"))
    registered = manager.register_node(graph, NodeRecord(node_id="n1"))
    frontier = manager.get_frontier(registered, criteria={})
    pruned = manager.prune_branches(registered)
    merged = manager.merge_traces(pruned, task_summary="task", scenario_name="data_science")

    assert selected == []
    assert frontier == ["n1"]
    assert registered is graph
    assert pruned is graph
    assert merged is None
