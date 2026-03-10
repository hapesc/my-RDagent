from __future__ import annotations

import logging
from unittest.mock import Mock

from core.loop import LoopEngine, LoopEngineConfig, StepExecutionResult
from data_models import (
    ArtifactVerificationStatus,
    ExecutionOutcomeContract,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    Plan,
    ProcessExecutionStatus,
    Proposal,
    RunSession,
    RunStatus,
    Score,
    StepState,
    StopConditions,
    UsefulnessEligibilityStatus,
)


def _make_step_result(node_id: str, parent_node_id: str | None = None) -> StepExecutionResult:
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


def _make_fatal_step_result(node_id: str) -> StepExecutionResult:
    return StepExecutionResult(
        proposal=Proposal(proposal_id=f"proposal-{node_id}", summary="summary"),
        experiment=ExperimentNode(
            node_id=node_id,
            run_id="run-multi",
            branch_id="main",
        ),
        artifact_id=f"artifact-{node_id}",
        score=Score(score_id=f"score-{node_id}", value=0.0, metric_name="acc"),
        feedback=FeedbackRecord(
            feedback_id=f"feedback-{node_id}",
            decision=False,
            acceptable=False,
            reason="fatal",
        ),
        outcome=ExecutionOutcomeContract(
            process_status=ProcessExecutionStatus.FAILED,
            artifact_status=ArtifactVerificationStatus.MISSING_REQUIRED,
            usefulness_status=UsefulnessEligibilityStatus.INELIGIBLE,
        ),
        step_state=StepState.FAILED,
        failed_stage="running",
        error_message="fatal process failure",
    )


def _build_engine(
    *,
    branches_per_iteration: int = 1,
    scheduler: Mock | None = None,
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


def _make_real_provider_run(max_loops: int = 1) -> RunSession:
    run = _make_run(max_loops=max_loops)
    run.config_snapshot = {
        "runtime": {
            "uses_real_llm_provider": True,
            "guardrail_warnings": [],
            "real_provider_safe_profile": {
                "layer0_n_candidates": 1,
                "layer0_k_forward": 1,
            },
        }
    }
    return run


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


def test_scheduler_marks_run_failed_when_all_branches_fatal() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["root-a", "root-b"]

    engine, _planner, exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
        scheduler=scheduler,
        step_side_effect=[_make_fatal_step_result("n1"), _make_fatal_step_result("n2")],
    )

    context = engine.run(run_session=_make_run(max_loops=1), task_summary="all-fatal", max_loops=1)

    assert context.loop_state.status == RunStatus.FAILED
    assert step_executor.execute_iteration.call_count == 2
    assert exploration_manager.register_node.call_count == 0


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


def test_real_provider_run_clamps_scheduler_branches_to_one() -> None:
    scheduler = Mock()
    scheduler.select_node.side_effect = ["root-a", "root-b", "root-c"]

    engine, _planner, _exploration_manager, step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=3,
        scheduler=scheduler,
        step_side_effect=[_make_step_result("n1")],
    )

    engine.run(run_session=_make_real_provider_run(max_loops=1), task_summary="real-provider", max_loops=1)

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


def test_select_best_branch_prefers_real_execution_result() -> None:
    engine, _planner, _exploration_manager, _step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
    )
    selector = Mock()
    engine._validation_selector = selector

    real_first = ExecutionResult(run_id="real-run-1", exit_code=1, logs_ref="log-1", artifacts_ref="artifact-1")
    real_second = ExecutionResult(run_id="real-run-2", exit_code=0, logs_ref="log-2", artifacts_ref='["artifact-2"]')
    first = _make_step_result("node-1")
    first.execution_result = real_first
    second = _make_step_result("node-2")
    second.execution_result = real_second
    selector.select_best.return_value = (real_second, Score(score_id="best", value=0.9, metric_name="acc"))

    best_node_id = engine._select_best_branch(
        [first, second],
        [("node-1", first, True), ("node-2", second, True)],
    )

    assert best_node_id == "node-2"
    selector.select_best.assert_called_once_with([real_first, real_second])


def test_select_best_branch_warns_when_fabricating_execution_result(caplog) -> None:
    engine, _planner, _exploration_manager, _step_executor, _run_store, _event_store = _build_engine(
        branches_per_iteration=2,
    )
    selector = Mock()
    engine._validation_selector = selector

    real_result = ExecutionResult(run_id="real-run", exit_code=0, logs_ref="log", artifacts_ref='["artifact"]')
    fallback_step = _make_step_result("node-fallback")
    real_step = _make_step_result("node-real")
    real_step.execution_result = real_result

    def _capture_candidates(candidates):
        assert candidates[1] is real_result
        assert candidates[0].run_id == "node-fallback"
        return real_result, Score(score_id="best", value=0.8, metric_name="acc")

    selector.select_best.side_effect = _capture_candidates

    with caplog.at_level(logging.WARNING):
        best_node_id = engine._select_best_branch(
            [fallback_step, real_step],
            [("node-fallback", fallback_step, True), ("node-real", real_step, True)],
        )

    assert best_node_id == "node-real"
    assert "using fabricated fallback" in caplog.text
