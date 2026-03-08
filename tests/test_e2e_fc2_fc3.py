from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from app.runtime import build_run_service, build_runtime
from core.reasoning.virtual_eval import VirtualEvaluator
from data_models import BranchState, EventType, ExplorationGraph, NodeRecord, StopConditions
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from exploration_manager.merging import TraceMerger
from exploration_manager.pruning import BranchPruner
from exploration_manager.scheduler import MCTSScheduler
from llm.adapter import LLMAdapter, MockLLMProvider
from llm.schemas import ExperimentDesign


class TestFC2FC3Integration(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._env_patch = patch.dict(
            os.environ,
            {
                "AGENTRD_ARTIFACT_ROOT": self._tmpdir.name,
                "AGENTRD_WORKSPACE_ROOT": self._tmpdir.name,
                "AGENTRD_TRACE_STORAGE_PATH": os.path.join(self._tmpdir.name, "trace", "events.jsonl"),
                "AGENTRD_SQLITE_PATH": os.path.join(self._tmpdir.name, "meta.db"),
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                "RD_AGENT_LLM_PROVIDER": "mock",
            },
            clear=False,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_full_loop_with_reasoning_and_branches(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="classify iris dataset",
            stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
        )

        context = run_service.start_run(
            run.run_id,
            task_summary="classify iris dataset",
            loops_per_call=2,
        )

        self.assertIsNotNone(context)
        run_session = context.run_session
        self.assertIsNotNone(run_session)
        assert run_session is not None
        self.assertEqual(run_session.status.name, "COMPLETED")

        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        self.assertGreaterEqual(len(events), 6)
        event_types = {event.event_type for event in events}
        self.assertTrue(
            {
                EventType.HYPOTHESIS_GENERATED,
                EventType.EXPERIMENT_GENERATED,
                EventType.CODING_ROUND,
                EventType.EXECUTION_FINISHED,
                EventType.FEEDBACK_GENERATED,
                EventType.TRACE_RECORDED,
            }.issubset(event_types)
        )

    def test_virtual_eval_produces_multiple_candidates(self) -> None:
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        evaluator = VirtualEvaluator(adapter, n_candidates=3, k_forward=2)

        designs = evaluator.evaluate("classify images", "data_science", 0, [], [])

        self.assertEqual(len(designs), 2)
        for design in designs:
            self.assertIsInstance(design, ExperimentDesign)
            self.assertTrue(design.summary.strip())
            self.assertGreaterEqual(design.virtual_score, 0.0)

    def test_mcts_selection_and_feedback_with_multiple_nodes(self) -> None:
        nodes = [
            NodeRecord(node_id="n1", score=0.9, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.7, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n3", score=0.6, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n4", score=0.5, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n5", score=0.4, branch_state=BranchState.ACTIVE),
        ]
        graph = ExplorationGraph(nodes=nodes)
        graph.branch_scores = {
            "n1": 0.9,
            "n2": 0.7,
            "n3": 0.6,
            "n4": 0.5,
            "n5": 0.4,
        }
        graph.visit_counts = {"n1": 0, "n2": 0, "n3": 0, "n4": 0, "n5": 0}

        scheduler = MCTSScheduler(exploration_weight=1.41)
        selected_ids = []
        for _ in range(10):
            selected = scheduler.select_node(graph)
            self.assertIsNotNone(selected)
            assert selected is not None
            selected_ids.append(selected)
            scheduler.observe_feedback(graph, selected, score=0.8, decision=True)

        self.assertGreaterEqual(len(set(selected_ids)), 2)
        all_node_ids = {node.node_id for node in graph.nodes}
        self.assertTrue(set(selected_ids).issubset(all_node_ids))

    def test_observe_feedback_updates_mcts_stats(self) -> None:
        parent = NodeRecord(node_id="parent", score=0.6, branch_state=BranchState.ACTIVE)
        child = NodeRecord(
            node_id="child",
            parent_ids=["parent"],
            score=0.8,
            branch_state=BranchState.ACTIVE,
        )
        graph = ExplorationGraph(nodes=[parent, child])

        scheduler = MCTSScheduler(c_puct=1.41)
        scheduler.observe_feedback(graph, "child", score=0.8, decision=True)

        self.assertEqual(child.visits, 1)
        self.assertGreater(child.total_value, 0.0)
        self.assertEqual(parent.visits, 1)
        self.assertGreater(parent.total_value, 0.0)
        self.assertAlmostEqual(parent.total_value, child.total_value)

    def test_layer0_diverse_roots_integration(self) -> None:
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        evaluator = VirtualEvaluator(adapter, n_candidates=4, k_forward=3)
        manager = ExplorationManager(
            ExplorationManagerConfig(),
            scheduler=MCTSScheduler(c_puct=1.41),
            virtual_evaluator=evaluator,
        )
        graph = ExplorationGraph()

        graph = manager.generate_diverse_roots(
            graph,
            task_summary="classify iris dataset",
            scenario_name="data_science",
            n_candidates=4,
            k_forward=3,
        )

        self.assertGreater(len(graph.nodes), 1)
        node_ids = [node.node_id for node in graph.nodes]
        self.assertEqual(len(node_ids), len(set(node_ids)))
        for node in graph.nodes:
            self.assertIsNotNone(node.score)

    def test_full_loop_with_backprop_integration(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="classify iris dataset",
            stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
        )

        captured_graphs = []
        original_observe_feedback = runtime.exploration_manager.observe_feedback

        def _capture_feedback(graph, node_id, score, decision):
            original_observe_feedback(graph, node_id, score, decision)
            captured_graphs.append(graph)

        runtime.exploration_manager.observe_feedback = _capture_feedback
        try:
            context = run_service.start_run(
                run.run_id,
                task_summary="classify iris dataset",
                loops_per_call=2,
            )
        finally:
            runtime.exploration_manager.observe_feedback = original_observe_feedback

        self.assertIsNotNone(context)
        run_session = context.run_session
        self.assertIsNotNone(run_session)
        assert run_session is not None
        self.assertEqual(run_session.status.name, "COMPLETED")
        self.assertGreaterEqual(len(captured_graphs), 1)

        final_graph = captured_graphs[-1]
        updated_nodes = [
            node for node in final_graph.nodes if node.visits > 0 and node.total_value > 0.0
        ]
        self.assertGreaterEqual(len(updated_nodes), 1)

    def test_prune_then_merge_pipeline(self) -> None:
        graph = ExplorationGraph(
            nodes=[
                NodeRecord(node_id="n1", proposal_id="p1", score=0.9, branch_state=BranchState.ACTIVE),
                NodeRecord(node_id="n2", proposal_id="p2", score=0.8, branch_state=BranchState.ACTIVE),
                NodeRecord(node_id="n3", proposal_id="p3", score=0.1, branch_state=BranchState.ACTIVE),
                NodeRecord(node_id="n4", proposal_id="p4", score=0.2, branch_state=BranchState.ACTIVE),
            ]
        )
        graph.branch_scores = {"n1": 0.9, "n2": 0.8, "n3": 0.1, "n4": 0.2}

        pruner = BranchPruner(relative_threshold=0.5)
        pruner.prune(graph)

        states = {node.node_id: node.branch_state for node in graph.nodes}
        self.assertEqual(states["n1"], BranchState.ACTIVE)
        self.assertEqual(states["n2"], BranchState.ACTIVE)
        self.assertEqual(states["n3"], BranchState.PRUNED)
        self.assertEqual(states["n4"], BranchState.PRUNED)

        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        merger = TraceMerger(adapter)

        active_nodes = [node for node in graph.nodes if node.branch_state == BranchState.ACTIVE]
        trace_dicts = [
            {"node_id": n.node_id, "score": n.score, "proposal_id": n.proposal_id}
            for n in active_nodes
        ]
        result = merger.merge(trace_dicts, "classify iris", "data_science")

        self.assertIsInstance(result, ExperimentDesign)
        self.assertTrue(result.summary.strip())


if __name__ == "__main__":
    unittest.main()
