from __future__ import annotations

from data_models import BranchState, ExplorationGraph, NodeRecord
from exploration_manager.pruning import BranchPruner


def _make_graph(nodes, branch_scores=None):
    graph = ExplorationGraph(nodes=nodes)
    if branch_scores:
        graph.branch_scores = branch_scores
    return graph


def test_empty_graph_no_crash() -> None:
    graph = ExplorationGraph()
    pruned = BranchPruner().prune(graph)
    assert pruned is graph
    assert pruned.nodes == []


def test_single_active_node_never_pruned() -> None:
    graph = _make_graph([NodeRecord(node_id="n1", score=0.01)])
    BranchPruner(score_threshold=1.0, relative_threshold=1.0).prune(graph)
    assert graph.nodes[0].branch_state == BranchState.ACTIVE


def test_relative_pruning_removes_weak_branches() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.9),
            NodeRecord(node_id="n2", score=0.3),
            NodeRecord(node_id="n3", score=0.6),
        ]
    )
    BranchPruner(relative_threshold=0.5).prune(graph)
    assert graph.nodes[0].branch_state == BranchState.ACTIVE
    assert graph.nodes[1].branch_state == BranchState.PRUNED
    assert graph.nodes[2].branch_state == BranchState.ACTIVE


def test_best_node_always_preserved_even_with_high_absolute_threshold() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="best", score=0.9),
            NodeRecord(node_id="weak", score=0.2),
        ]
    )
    BranchPruner(score_threshold=1.2, relative_threshold=None).prune(graph)
    assert graph.nodes[0].branch_state == BranchState.ACTIVE
    assert graph.nodes[1].branch_state == BranchState.PRUNED


def test_absolute_threshold_pruning() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.8),
            NodeRecord(node_id="n2", score=0.4),
            NodeRecord(node_id="n3", score=0.5),
        ]
    )
    BranchPruner(score_threshold=0.5, relative_threshold=None).prune(graph)
    states = {node.node_id: node.branch_state for node in graph.nodes}
    assert states["n1"] == BranchState.ACTIVE
    assert states["n2"] == BranchState.PRUNED
    assert states["n3"] == BranchState.ACTIVE


def test_unscored_nodes_not_pruned() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=1.0),
            NodeRecord(node_id="n2", score=None),
            NodeRecord(node_id="n3", score=0.1),
        ]
    )
    BranchPruner(relative_threshold=0.5).prune(graph)
    states = {node.node_id: node.branch_state for node in graph.nodes}
    assert states["n2"] == BranchState.ACTIVE
    assert states["n3"] == BranchState.PRUNED


def test_already_pruned_nodes_untouched() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.9),
            NodeRecord(node_id="n2", score=0.2, branch_state=BranchState.PRUNED),
            NodeRecord(node_id="n3", score=0.1),
        ]
    )
    BranchPruner(relative_threshold=0.5).prune(graph)
    states = {node.node_id: node.branch_state for node in graph.nodes}
    assert states["n2"] == BranchState.PRUNED
    assert states["n3"] == BranchState.PRUNED


def test_at_least_one_remains_active() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.1),
            NodeRecord(node_id="n2", score=0.01),
            NodeRecord(node_id="n3", score=0.001),
        ]
    )
    BranchPruner(score_threshold=10.0, relative_threshold=None).prune(graph)
    active = [node for node in graph.nodes if node.branch_state == BranchState.ACTIVE]
    assert len(active) >= 1
    assert any(node.node_id == "n1" for node in active)


def test_should_prune_returns_true_for_weak_node() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="best", score=1.0),
            NodeRecord(node_id="weak", score=0.2),
        ]
    )
    pruner = BranchPruner(relative_threshold=0.5)
    assert pruner.should_prune(graph, "weak") is True


def test_should_prune_returns_false_for_strong_node() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="best", score=1.0),
            NodeRecord(node_id="strong", score=0.8),
        ]
    )
    pruner = BranchPruner(relative_threshold=0.5)
    assert pruner.should_prune(graph, "strong") is False


def test_should_prune_returns_false_for_only_active_node() -> None:
    graph = _make_graph([NodeRecord(node_id="solo", score=0.01)])
    assert BranchPruner(relative_threshold=0.5).should_prune(graph, "solo") is False


def test_negative_scores_handled_correctly() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="best", score=-0.1),
            NodeRecord(node_id="mid", score=-0.2),
            NodeRecord(node_id="worst", score=-1.0),
        ]
    )
    BranchPruner(score_threshold=None, relative_threshold=0.5).prune(graph)
    states = {node.node_id: node.branch_state for node in graph.nodes}
    assert states["best"] == BranchState.ACTIVE
    assert states["mid"] == BranchState.PRUNED
    assert states["worst"] == BranchState.PRUNED


def test_prune_updates_graph_level_branch_states() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.9),
            NodeRecord(node_id="n2", score=0.1),
        ]
    )
    graph.branch_states = {"n1": BranchState.ACTIVE, "n2": BranchState.ACTIVE}
    BranchPruner(relative_threshold=0.5).prune(graph)
    assert graph.branch_states["n1"] == BranchState.ACTIVE
    assert graph.branch_states["n2"] == BranchState.PRUNED
