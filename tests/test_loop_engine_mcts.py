from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from core.loop import LoopEngine, LoopEngineConfig
from data_models import ExplorationGraph, NodeRecord, Plan, RunSession, RunStatus, StopConditions


def _make_step_result(node_id: str, parent_node_id: str, score_value: float = 0.8, decision: bool = True):
    return SimpleNamespace(
        proposal=SimpleNamespace(proposal_id=f"prop-{node_id}"),
        experiment=SimpleNamespace(node_id=node_id, parent_node_id=parent_node_id),
        artifact_id=f"art-{node_id}",
        score=SimpleNamespace(score_id=f"score-{node_id}", value=score_value, metric_name="acc"),
        feedback=SimpleNamespace(
            feedback_id=f"fb-{node_id}",
            decision=decision,
            acceptable=True,
            reason="ok",
        ),
        checkpoint_ids=["cp-1"],
    )


def _build_run_session() -> RunSession:
    return RunSession(
        run_id="run-mcts",
        scenario="data_science",
        status=RunStatus.CREATED,
        stop_conditions=StopConditions(max_loops=10, max_duration_sec=120),
        entry_input={"task_summary": "mcts"},
    )


class _LegacyExplorationManager:
    def __init__(self) -> None:
        self.register_node = Mock(side_effect=lambda graph, node: graph)
        self.prune_branches = Mock(side_effect=lambda graph: graph)
        self.observe_feedback = Mock()


class _DiverseRootsExplorationManager(_LegacyExplorationManager):
    def __init__(self) -> None:
        super().__init__()
        self.generate_diverse_roots_mock = Mock(side_effect=self._generate_diverse_roots)

    def _generate_diverse_roots(self, graph, task_summary, scenario, n_candidates, k_forward):
        _ = task_summary
        _ = scenario
        _ = n_candidates
        _ = k_forward
        graph.nodes.append(NodeRecord(node_id="root-a"))
        graph.nodes.append(NodeRecord(node_id="root-b"))
        return graph

    def generate_diverse_roots(self, graph, task_summary, scenario, n_candidates, k_forward):
        return self.generate_diverse_roots_mock(graph, task_summary, scenario, n_candidates, k_forward)


class LoopEngineMCTSTests(unittest.TestCase):
    def _build_engine(
        self,
        *,
        branches_per_iteration: int = 1,
        layer0_n_candidates: int = 5,
        layer0_k_forward: int = 2,
        scheduler: Mock,
        exploration_manager,
        step_executor: Mock,
    ) -> LoopEngine:
        planner = Mock()
        planner.generate_plan.return_value = Plan(plan_id="plan-1")

        memory_service = Mock()
        memory_service.query_context.return_value = SimpleNamespace(items=[], highlights=[], scored_items=[])

        run_store = Mock()
        event_store = Mock()

        return LoopEngine(
            config=LoopEngineConfig(
                branches_per_iteration=branches_per_iteration,
                layer0_n_candidates=layer0_n_candidates,
                layer0_k_forward=layer0_k_forward,
            ),
            planner=planner,
            exploration_manager=exploration_manager,
            memory_service=memory_service,
            step_executor=step_executor,
            run_store=run_store,
            event_store=event_store,
            scheduler=scheduler,
        )

    def test_scheduler_branch_runs_select_expand_backprop_and_observes_feedback(self) -> None:
        scheduler = Mock()
        scheduler.select_node.return_value = "root"

        exploration_manager = Mock()
        exploration_manager.register_node.side_effect = lambda graph, node: graph
        exploration_manager.prune_branches.side_effect = lambda graph: graph
        exploration_manager.observe_feedback = Mock()

        step_executor = Mock()
        step_executor.execute_iteration.return_value = _make_step_result("node-1", "root")

        engine = self._build_engine(
            scheduler=scheduler,
            exploration_manager=exploration_manager,
            step_executor=step_executor,
        )

        context = engine.run(_build_run_session(), "task", max_loops=1)

        self.assertEqual(context.loop_state.iteration, 1)
        scheduler.select_node.assert_called_once()
        self.assertEqual(step_executor.execute_iteration.call_count, 1)
        self.assertEqual(exploration_manager.register_node.call_count, 1)
        self.assertEqual(exploration_manager.prune_branches.call_count, 1)
        registered_node = exploration_manager.register_node.call_args.args[1]
        self.assertEqual(registered_node.score, 0.8)
        exploration_manager.observe_feedback.assert_called_once()
        observe_call = exploration_manager.observe_feedback.call_args
        self.assertEqual(observe_call.args[1], "node-1")
        self.assertEqual(observe_call.kwargs["score"], 0.8)
        self.assertTrue(observe_call.kwargs["decision"])

    def test_scheduler_branch_no_longer_calls_update_visit_count(self) -> None:
        scheduler = Mock()
        scheduler.select_node.return_value = "root"
        scheduler.update_visit_count = Mock()

        exploration_manager = Mock()
        exploration_manager.register_node.side_effect = lambda graph, node: graph
        exploration_manager.prune_branches.side_effect = lambda graph: graph
        exploration_manager.observe_feedback = Mock()

        step_executor = Mock()
        step_executor.execute_iteration.return_value = _make_step_result("node-2", "root")

        engine = self._build_engine(
            scheduler=scheduler,
            exploration_manager=exploration_manager,
            step_executor=step_executor,
        )

        engine.run(_build_run_session(), "task", max_loops=1)

        scheduler.update_visit_count.assert_not_called()

    def test_layer0_initialization_uses_configured_params_when_available(self) -> None:
        scheduler = Mock()

        def select_node(graph: ExplorationGraph) -> str:
            return graph.nodes[0].node_id

        scheduler.select_node.side_effect = select_node

        exploration_manager = _DiverseRootsExplorationManager()

        step_executor = Mock()
        step_executor.execute_iteration.return_value = _make_step_result("node-3", "root-a")

        engine = self._build_engine(
            layer0_n_candidates=9,
            layer0_k_forward=4,
            scheduler=scheduler,
            exploration_manager=exploration_manager,
            step_executor=step_executor,
        )

        run_session = _build_run_session()
        engine.run(run_session, "task", max_loops=1)

        exploration_manager.generate_diverse_roots_mock.assert_called_once()
        call = exploration_manager.generate_diverse_roots_mock.call_args
        self.assertEqual(call.args[1], "task")
        self.assertEqual(call.args[2], run_session.scenario)
        self.assertEqual(call.args[3], 9)
        self.assertEqual(call.args[4], 4)

    def test_layer0_falls_back_to_single_root_without_generate_diverse_roots(self) -> None:
        scheduler = Mock()
        selected_graphs = []

        def select_node(graph: ExplorationGraph) -> str:
            selected_graphs.append(graph)
            return "root"

        scheduler.select_node.side_effect = select_node

        exploration_manager = _LegacyExplorationManager()

        step_executor = Mock()
        step_executor.execute_iteration.return_value = _make_step_result("node-4", "root")

        engine = self._build_engine(
            scheduler=scheduler,
            exploration_manager=exploration_manager,
            step_executor=step_executor,
        )

        engine.run(_build_run_session(), "task", max_loops=1)

        self.assertGreaterEqual(len(selected_graphs), 1)
        self.assertEqual([n.node_id for n in selected_graphs[0].nodes], ["root"])

    def test_multiple_iterations_and_branches_observe_feedback_each_expansion(self) -> None:
        scheduler = Mock()
        scheduler.select_node.return_value = "root"

        exploration_manager = Mock()
        exploration_manager.register_node.side_effect = lambda graph, node: graph
        exploration_manager.prune_branches.side_effect = lambda graph: graph
        exploration_manager.observe_feedback = Mock()

        step_executor = Mock()
        step_executor.execute_iteration.side_effect = [
            _make_step_result("node-1", "root", score_value=0.8, decision=True),
            _make_step_result("node-2", "root", score_value=0.7, decision=False),
            _make_step_result("node-3", "root", score_value=0.6, decision=True),
            _make_step_result("node-4", "root", score_value=0.5, decision=True),
        ]

        engine = self._build_engine(
            branches_per_iteration=2,
            scheduler=scheduler,
            exploration_manager=exploration_manager,
            step_executor=step_executor,
        )

        engine.run(_build_run_session(), "task", max_loops=2)

        self.assertEqual(step_executor.execute_iteration.call_count, 4)
        self.assertEqual(exploration_manager.observe_feedback.call_count, 4)
        registered_scores = [call.args[1].score for call in exploration_manager.register_node.call_args_list]
        self.assertEqual(registered_scores, [0.8, 0.7, 0.6, 0.5])
        observed_node_ids = [call.args[1] for call in exploration_manager.observe_feedback.call_args_list]
        self.assertEqual(observed_node_ids, ["node-1", "node-2", "node-3", "node-4"])


if __name__ == "__main__":
    unittest.main()
