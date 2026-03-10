"""Tests for ExplorationManager tree structure and scheduler integration (T9)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from core.reasoning.virtual_eval import VirtualEvaluator
from data_models import ExplorationGraph, NodeRecord
from exploration_manager.scheduler import MCTSScheduler
from exploration_manager.service import ExplorationManager, ExplorationManagerConfig


class TestRegisterNodeEdgeMaintenance(unittest.TestCase):
    """register_node() should automatically maintain graph.edges."""

    def setUp(self) -> None:
        self.config = ExplorationManagerConfig()
        self.manager = ExplorationManager(self.config, scheduler=MCTSScheduler())

    def test_register_root_no_edges(self) -> None:
        graph = ExplorationGraph()
        root = NodeRecord(node_id="root")
        graph = self.manager.register_node(graph, root)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(len(graph.edges), 0)

    def test_register_child_creates_edge(self) -> None:
        graph = ExplorationGraph()
        root = NodeRecord(node_id="root")
        graph = self.manager.register_node(graph, root)
        child = NodeRecord(node_id="child-1", parent_ids=["root"])
        graph = self.manager.register_node(graph, child)
        self.assertEqual(len(graph.edges), 1)
        edge = graph.edges[0]
        self.assertEqual(edge.parent_id, "root")
        self.assertEqual(edge.child_id, "child-1")

    def test_register_node_with_multiple_parents(self) -> None:
        graph = ExplorationGraph()
        graph = self.manager.register_node(graph, NodeRecord(node_id="p1"))
        graph = self.manager.register_node(graph, NodeRecord(node_id="p2"))
        child = NodeRecord(node_id="c1", parent_ids=["p1", "p2"])
        graph = self.manager.register_node(graph, child)
        self.assertEqual(len(graph.edges), 2)
        edge_pairs = {(e.parent_id, e.child_id) for e in graph.edges}
        self.assertIn(("p1", "c1"), edge_pairs)
        self.assertIn(("p2", "c1"), edge_pairs)

    def test_register_preserves_existing_edges(self) -> None:
        graph = ExplorationGraph()
        graph = self.manager.register_node(graph, NodeRecord(node_id="root"))
        graph = self.manager.register_node(graph, NodeRecord(node_id="a", parent_ids=["root"]))
        self.assertEqual(len(graph.edges), 1)
        graph = self.manager.register_node(graph, NodeRecord(node_id="b", parent_ids=["root"]))
        self.assertEqual(len(graph.edges), 2)


class TestGetNodeDepth(unittest.TestCase):
    """get_node_depth() should compute depth via parent chain."""

    def setUp(self) -> None:
        self.config = ExplorationManagerConfig()
        self.manager = ExplorationManager(self.config, scheduler=MCTSScheduler())
        self.graph = ExplorationGraph()
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="root"))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="a", parent_ids=["root"]))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="b", parent_ids=["a"]))

    def test_root_depth_is_zero(self) -> None:
        self.assertEqual(self.manager.get_node_depth(self.graph, "root"), 0)

    def test_child_depth_is_one(self) -> None:
        self.assertEqual(self.manager.get_node_depth(self.graph, "a"), 1)

    def test_grandchild_depth_is_two(self) -> None:
        self.assertEqual(self.manager.get_node_depth(self.graph, "b"), 2)

    def test_unknown_node_returns_minus_one(self) -> None:
        self.assertEqual(self.manager.get_node_depth(self.graph, "nonexistent"), -1)


class TestGetChildren(unittest.TestCase):
    """get_children() should return direct children from graph.edges."""

    def setUp(self) -> None:
        self.config = ExplorationManagerConfig()
        self.manager = ExplorationManager(self.config, scheduler=MCTSScheduler())
        self.graph = ExplorationGraph()
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="root"))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="c1", parent_ids=["root"]))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="c2", parent_ids=["root"]))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="gc1", parent_ids=["c1"]))

    def test_root_has_two_children(self) -> None:
        children = self.manager.get_children(self.graph, "root")
        self.assertEqual(sorted(children), ["c1", "c2"])

    def test_leaf_has_no_children(self) -> None:
        children = self.manager.get_children(self.graph, "gc1")
        self.assertEqual(children, [])

    def test_c1_has_one_child(self) -> None:
        children = self.manager.get_children(self.graph, "c1")
        self.assertEqual(children, ["gc1"])


class TestGetPathToRoot(unittest.TestCase):
    """get_path_to_root() should return leaf→root path."""

    def setUp(self) -> None:
        self.config = ExplorationManagerConfig()
        self.manager = ExplorationManager(self.config, scheduler=MCTSScheduler())
        self.graph = ExplorationGraph()
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="root"))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="A", parent_ids=["root"]))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="B", parent_ids=["A"]))

    def test_leaf_path_to_root(self) -> None:
        path = self.manager.get_path_to_root(self.graph, "B")
        self.assertEqual(path, ["B", "A", "root"])

    def test_root_path_is_just_root(self) -> None:
        path = self.manager.get_path_to_root(self.graph, "root")
        self.assertEqual(path, ["root"])

    def test_unknown_node_returns_empty(self) -> None:
        path = self.manager.get_path_to_root(self.graph, "nonexistent")
        self.assertEqual(path, [])


class TestObserveFeedback(unittest.TestCase):
    """observe_feedback() should delegate to scheduler and trigger backprop."""

    def setUp(self) -> None:
        self.config = ExplorationManagerConfig()
        self.scheduler = MCTSScheduler()
        self.manager = ExplorationManager(self.config, scheduler=self.scheduler)
        self.graph = ExplorationGraph()
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="root"))
        self.graph = self.manager.register_node(self.graph, NodeRecord(node_id="child", parent_ids=["root"]))

    def test_observe_feedback_updates_visits(self) -> None:
        self.manager.observe_feedback(self.graph, "child", score=0.7, decision=True)
        child = next(n for n in self.graph.nodes if n.node_id == "child")
        self.assertGreaterEqual(child.visits, 1)

    def test_observe_feedback_backpropagates_to_parent(self) -> None:
        self.manager.observe_feedback(self.graph, "child", score=0.7, decision=True)
        root = next(n for n in self.graph.nodes if n.node_id == "root")
        self.assertGreaterEqual(root.visits, 1)

    def test_observe_feedback_without_scheduler_is_noop(self) -> None:
        manager_no_sched = ExplorationManager(self.config, scheduler=None)
        graph = ExplorationGraph()
        graph = manager_no_sched.register_node(graph, NodeRecord(node_id="root"))
        # Should not raise
        manager_no_sched.observe_feedback(graph, "root", score=0.5, decision=True)
        root = next(n for n in graph.nodes if n.node_id == "root")
        self.assertEqual(root.visits, 0)


class TestGenerateDiverseRoots(unittest.TestCase):
    """generate_diverse_roots() Layer-0 diversity via VirtualEvaluator."""

    def test_diverse_roots_with_evaluator(self) -> None:
        from llm.schemas import ExperimentDesign

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = [
            ExperimentDesign(summary="approach A", virtual_score=0.8),
            ExperimentDesign(summary="approach B", virtual_score=0.6),
        ]
        config = ExplorationManagerConfig()
        manager = ExplorationManager(config, scheduler=MCTSScheduler(), virtual_evaluator=mock_evaluator)
        graph = ExplorationGraph()
        graph = manager.generate_diverse_roots(graph, "classify images", "data_science", n_candidates=3, k_forward=2)
        self.assertEqual(len(graph.nodes), 2)
        eval_call = mock_evaluator.evaluate.call_args
        self.assertEqual(eval_call.kwargs["n_candidates"], 3)
        self.assertEqual(eval_call.kwargs["k_forward"], 2)
        for node in graph.nodes:
            self.assertEqual(node.parent_ids, [])
            self.assertTrue(node.node_id.startswith("root-"))
            assert node.proposal_id is not None
            self.assertTrue(node.proposal_id.startswith("layer0-"))

    def test_diverse_roots_uses_call_time_n_k_configuration(self) -> None:
        from llm.adapter import LLMAdapter, MockLLMProvider

        adapter = LLMAdapter(MockLLMProvider())
        evaluator = VirtualEvaluator(adapter, n_candidates=2, k_forward=1)
        manager = ExplorationManager(
            ExplorationManagerConfig(),
            scheduler=MCTSScheduler(),
            virtual_evaluator=evaluator,
        )
        graph = manager.generate_diverse_roots(
            ExplorationGraph(),
            "classify images",
            "data_science",
            n_candidates=4,
            k_forward=3,
        )
        self.assertEqual(len(graph.nodes), 3)

    def test_fallback_single_root_when_no_evaluator(self) -> None:
        config = ExplorationManagerConfig()
        manager = ExplorationManager(config, scheduler=MCTSScheduler(), virtual_evaluator=None)
        graph = ExplorationGraph()
        graph = manager.generate_diverse_roots(graph, "classify images", "data_science")
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].node_id, "root")

    def test_fallback_when_evaluator_returns_empty(self) -> None:
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = []
        config = ExplorationManagerConfig()
        manager = ExplorationManager(config, scheduler=MCTSScheduler(), virtual_evaluator=mock_evaluator)
        graph = ExplorationGraph()
        graph = manager.generate_diverse_roots(graph, "task", "scenario")
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].node_id, "root")

    def test_diverse_roots_have_unique_ids(self) -> None:
        from llm.schemas import ExperimentDesign

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = [
            ExperimentDesign(summary="A", virtual_score=0.9),
            ExperimentDesign(summary="B", virtual_score=0.7),
            ExperimentDesign(summary="C", virtual_score=0.5),
        ]
        config = ExplorationManagerConfig()
        manager = ExplorationManager(config, scheduler=MCTSScheduler(), virtual_evaluator=mock_evaluator)
        graph = ExplorationGraph()
        graph = manager.generate_diverse_roots(graph, "task", "scenario", n_candidates=3, k_forward=3)
        node_ids = [n.node_id for n in graph.nodes]
        self.assertEqual(len(node_ids), len(set(node_ids)))

    def test_diverse_roots_score_mapping(self) -> None:
        from llm.schemas import ExperimentDesign

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = [
            ExperimentDesign(summary="high", virtual_score=0.9),
            ExperimentDesign(summary="zero", virtual_score=0.0),
        ]
        config = ExplorationManagerConfig()
        manager = ExplorationManager(config, scheduler=MCTSScheduler(), virtual_evaluator=mock_evaluator)
        graph = ExplorationGraph()
        graph = manager.generate_diverse_roots(graph, "task", "scenario")
        high_node = graph.nodes[0]
        zero_node = graph.nodes[1]
        self.assertEqual(high_node.score, 0.9)
        self.assertIsNone(zero_node.score)


if __name__ == "__main__":
    unittest.main()
