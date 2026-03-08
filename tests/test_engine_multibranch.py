from __future__ import annotations

from typing import Optional
from unittest.mock import Mock

from core.loop import LoopEngine, LoopEngineConfig, StepExecutionResult
from data_models import (
    ExperimentNode,
    FeedbackRecord,
    Plan,
    Proposal,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)


def _make_step_result(node_id: str, parent_node_id: Optional[str] = None) -> StepExecutionResult:
    return StepExecutionResult(
        proposal=Proposal(proposal_id=f"proposal-{node_id}", summary="summary"),
        experiment=ExperimentNode(
            node_id=node_id,
            run_id="run-multi",
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


def _build_engine(
    *,
    branches_per_iteration: int = 1,
    scheduler: Optional[Mock] = None,
    step_side_effect=None,
    exploration_manager_override=None,
):
    planner = Mock()
    planner.generate_plan.return_value = Plan(plan_id="plan-1")

    if exploration_manager_override is None:
        exploration_manager = Mock()
        exploration_manager.select_parents.return_value = ["default-parent"]

        def _register_node(graph, node):
            graph.nodes.append(node)
            return graph

        exploration_manager.register_node.side_effect = _register_node
    else:
        exploration_manager = exploration_manager_override

    memory_service = Mock()
    memory_service.query_context.return_value = Mock(items=[])

    step_executor = Mock()
    if step_side_effect is None:
        step_executor.execute_iteration.return_value = _make_step_result("node-default")
    else:
        step_executor.execute_iteration.side_effect = step_side_effect

    run_store = Mock()
    event_store = Mock()

    engine = LoopEngine(
        config=LoopEngineConfig(branches_per_iteration=branches_per_iteration),
        planner=planner,
        exploration_manager=exploration_manager,
        memory_service=memory_service,
        step_executor=step_executor,
        run_store=run_store,
        event_store=event_store,
        scheduler=scheduler,
    )
    return engine, planner, exploration_manager, step_executor, run_store, event_store


class _NoMergeExplorationManager:
    def __init__(self) -> None:
        self.select_parents = Mock(return_value=["default-parent"])
        self.observe_feedback = Mock()

    def register_node(self, graph, node):
        graph.nodes.append(node)
        return graph

    def prune_branches(self, graph):
        return graph


class _MergeExplorationManager(_NoMergeExplorationManager):
    def __init__(self) -> None:
        super().__init__()
        self.merge_calls = []

    def merge_traces(self, graph, task_summary, scenario_name):
        self.merge_calls.append((graph, task_summary, scenario_name))
        return {"status": "merged", "active_nodes": len(graph.nodes)}


def _make_run(max_loops: int = 1) -> RunSession:
    return RunSession(
        run_id="run-multi",
        scenario="data_science",
        status=RunStatus.CREATED,
        stop_conditions=StopConditions(max_loops=max_loops, max_duration_sec=120),
    )


def test_config_default_branches_per_iteration_is_one() -> None:
    assert LoopEngineConfig().branches_per_iteration == 1


def test_no_scheduler_keeps_single_branch_behavior() -> None:
    engine, _planner, exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=3,
        scheduler=None,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
    )

    context = engine.run(run_session=_make_run(max_loops=2), task_summary="compat", max_loops=2)

    assert context.loop_state.iteration == 2
    assert step_executor.execute_iteration.call_count == 2
    assert exploration_manager.select_parents.call_count == 2


def test_scheduler_multi_branch_creates_multiple_nodes_per_outer_iteration() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["root-a", "root-b"]

    engine, _planner, exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
    )

    context = engine.run(run_session=_make_run(max_loops=1), task_summary="multi", max_loops=1)

    assert context.loop_state.iteration == 1
    assert step_executor.execute_iteration.call_count == 2
    assert exploration_manager.register_node.call_count == 2
    assert exploration_manager.select_parents.call_count == 0


def test_scheduler_none_selection_exhausts_branches_gracefully() -> None:
    scheduler = Mock()
    scheduler.select_node.return_value = None

    engine, _planner, _exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=3,
        scheduler=scheduler,
    )

    context = engine.run(run_session=_make_run(max_loops=1), task_summary="none", max_loops=1)

    assert context.loop_state.iteration == 1
    assert context.loop_state.status == RunStatus.COMPLETED
    assert step_executor.execute_iteration.call_count == 0


def test_branch_error_does_not_stop_other_branches_when_scheduler_enabled() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["root-a", "root-b"]

    engine, _planner, exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
        scheduler=scheduler,
        step_side_effect=[RuntimeError("branch failed"), _make_step_result("n2")],
    )

    context = engine.run(run_session=_make_run(max_loops=1), task_summary="resilient", max_loops=1)

    assert context.loop_state.status == RunStatus.COMPLETED
    assert step_executor.execute_iteration.call_count == 2
    assert exploration_manager.register_node.call_count == 1


def test_scheduler_with_single_branch_per_iteration_executes_once() -> None:
    scheduler = Mock()
    scheduler.select_node.return_value = "root-a"

    engine, _planner, _exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=1,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1")],
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="single", max_loops=1)

    assert step_executor.execute_iteration.call_count == 1
    assert scheduler.select_node.call_count == 1


def test_observe_feedback_called_after_each_successful_branch_execution() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["root-a", "root-b"]

    engine, _planner, exploration_manager, _step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="visits", max_loops=1)

    assert exploration_manager.observe_feedback.call_count == 2
    first_call = exploration_manager.observe_feedback.call_args_list[0]
    second_call = exploration_manager.observe_feedback.call_args_list[1]
    assert first_call[0][1] == "n1"  # node_id
    assert second_call[0][1] == "n2"  # node_id


def test_scheduler_selected_node_is_used_as_parent_id() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["p1", "p2"]

    engine, _planner, _exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="parents", max_loops=1)

    first_parent_ids = step_executor.execute_iteration.call_args_list[0][1]["parent_ids"]
    second_parent_ids = step_executor.execute_iteration.call_args_list[1][1]["parent_ids"]
    assert first_parent_ids == ["p1"]
    assert second_parent_ids == ["p2"]


def test_scheduler_none_mid_iteration_stops_remaining_branches() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["p1", None]

    engine, _planner, _exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=3,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1")],
    )

    engine.run(run_session=_make_run(max_loops=1), task_summary="partial", max_loops=1)

    assert step_executor.execute_iteration.call_count == 1
    assert scheduler.select_node.call_count == 2


def test_merge_capability_supported_merges_after_multiple_active_nodes() -> None:
    manager = _MergeExplorationManager()
    engine, _planner, _exploration_manager, _step_executor, _run_store, _event_store = _build_engine(
        scheduler=None,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
        exploration_manager_override=manager,
    )

    context = engine.run(run_session=_make_run(max_loops=2), task_summary="merge", max_loops=2)

    assert context.loop_state.iteration == 2
    assert context.merged_result == {"status": "merged", "active_nodes": 2}
    assert len(manager.merge_calls) == 1


def test_merge_capability_missing_skips_merge_without_failure() -> None:
    manager = _NoMergeExplorationManager()
    engine, _planner, _exploration_manager, _step_executor, _run_store, _event_store = _build_engine(
        scheduler=None,
        step_side_effect=[_make_step_result("n1"), _make_step_result("n2")],
        exploration_manager_override=manager,
    )

    context = engine.run(run_session=_make_run(max_loops=2), task_summary="no-merge", max_loops=2)

    assert context.loop_state.iteration == 2
    assert context.merged_result is None
