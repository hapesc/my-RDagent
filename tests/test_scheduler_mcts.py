import math

from data_models import BranchState, ExplorationGraph, NodeRecord
from exploration_manager.scheduler import MCTSScheduler


def _make_graph(nodes, visit_counts=None):
    graph = ExplorationGraph(nodes=nodes)
    if visit_counts:
        graph.visit_counts = visit_counts
    return graph


def test_empty_graph_returns_none() -> None:
    scheduler = MCTSScheduler()
    assert scheduler.select_node(ExplorationGraph()) is None


def test_single_active_node_returns_that_node() -> None:
    graph = _make_graph([NodeRecord(node_id="n1", branch_state=BranchState.ACTIVE)])
    assert MCTSScheduler().select_node(graph) == "n1"


def test_unvisited_nodes_prioritized_over_visited() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.9, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.1, branch_state=BranchState.ACTIVE),
        ],
        visit_counts={"n1": 5},
    )
    assert MCTSScheduler().select_node(graph) == "n2"


def test_unvisited_node_with_no_score_preferred() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.2, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=None, branch_state=BranchState.ACTIVE),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "n2"


def test_pruned_nodes_skipped() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", branch_state=BranchState.PRUNED),
            NodeRecord(node_id="n2", branch_state=BranchState.ACTIVE),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "n2"


def test_merged_nodes_skipped() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", branch_state=BranchState.MERGED),
            NodeRecord(node_id="n2", branch_state=BranchState.ACTIVE),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "n2"


def test_all_pruned_returns_none() -> None:
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", branch_state=BranchState.PRUNED),
            NodeRecord(node_id="n2", branch_state=BranchState.PRUNED),
        ]
    )
    assert MCTSScheduler().select_node(graph) is None


def test_puct_balances_exploration_and_exploitation() -> None:
    scheduler = MCTSScheduler(exploration_weight=4.0)
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.95, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.10, branch_state=BranchState.ACTIVE),
        ],
        visit_counts={"n1": 40, "n2": 1},
    )
    assert scheduler.select_node(graph) == "n2"


def test_update_visit_count_increments() -> None:
    scheduler = MCTSScheduler()
    graph = _make_graph([NodeRecord(node_id="n1", branch_state=BranchState.ACTIVE)])

    updated = scheduler.update_visit_count(graph, "n1")
    assert updated.visit_counts["n1"] == 1

    updated.visit_counts["n1"] = 3
    updated = scheduler.update_visit_count(updated, "n1")
    assert updated.visit_counts["n1"] == 4


def test_get_all_scores_returns_active_node_scores() -> None:
    scheduler = MCTSScheduler(exploration_weight=1.0)
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.6, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.2, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n3", score=0.9, branch_state=BranchState.PRUNED),
        ],
        visit_counts={"n1": 4, "n2": 2, "n3": 99},
    )

    scores = scheduler.get_all_scores(graph)
    assert set(scores.keys()) == {"n1", "n2"}
    assert math.isfinite(scores["n1"])
    assert math.isfinite(scores["n2"])


def test_custom_exploration_weight_zero_is_pure_exploitation() -> None:
    scheduler = MCTSScheduler(exploration_weight=0.0)
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.9, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.1, branch_state=BranchState.ACTIVE),
        ],
        visit_counts={"n1": 10, "n2": 1},
    )
    assert scheduler.select_node(graph) == "n1"


def test_custom_exploration_weight_high_prefers_lower_visits() -> None:
    scheduler = MCTSScheduler(exploration_weight=100.0)
    graph = _make_graph(
        [
            NodeRecord(node_id="n1", score=0.95, branch_state=BranchState.ACTIVE),
            NodeRecord(node_id="n2", score=0.05, branch_state=BranchState.ACTIVE),
        ],
        visit_counts={"n1": 100, "n2": 1},
    )
    assert scheduler.select_node(graph) == "n2"
