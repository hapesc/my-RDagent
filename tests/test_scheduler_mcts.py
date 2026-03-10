import math

from data_models import BranchState, ExplorationGraph, NodeRecord
from exploration_manager.reward import RewardCalculator
from exploration_manager.scheduler import MCTSScheduler


def _node(
    node_id: str,
    *,
    score: float | None = None,
    branch_state: BranchState = BranchState.ACTIVE,
    visits: int = 0,
    total_value: float = 0.0,
    avg_value: float = 0.0,
    parent_ids: list[str] | None = None,
) -> NodeRecord:
    return NodeRecord(
        node_id=node_id,
        score=score,
        branch_state=branch_state,
        visits=visits,
        total_value=total_value,
        avg_value=avg_value,
        parent_ids=parent_ids or [],
    )


def _graph(nodes: list[NodeRecord], visit_counts: dict[str, int] | None = None) -> ExplorationGraph:
    graph = ExplorationGraph(nodes=nodes)
    if visit_counts is not None:
        graph.visit_counts = visit_counts
    return graph


def test_empty_graph_returns_none() -> None:
    assert MCTSScheduler().select_node(ExplorationGraph()) is None


def test_single_active_node_returns_that_node() -> None:
    graph = _graph([_node("n1")])
    assert MCTSScheduler().select_node(graph) == "n1"


def test_unvisited_nodes_prioritized_over_visited() -> None:
    graph = _graph(
        [
            _node("visited", score=1.0, visits=5, avg_value=0.9),
            _node("unvisited", score=-1.0, visits=0),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "unvisited"


def test_unvisited_node_with_no_score_preferred_first() -> None:
    graph = _graph(
        [
            _node("with_score", score=0.5, visits=0),
            _node("no_score", score=None, visits=0),
            _node("visited", score=0.9, visits=1, avg_value=0.9),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "no_score"


def test_pruned_nodes_skipped() -> None:
    graph = _graph(
        [
            _node("p", branch_state=BranchState.PRUNED),
            _node("a", branch_state=BranchState.ACTIVE),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "a"


def test_merged_nodes_skipped() -> None:
    graph = _graph(
        [
            _node("m", branch_state=BranchState.MERGED),
            _node("a", branch_state=BranchState.ACTIVE),
        ]
    )
    assert MCTSScheduler().select_node(graph) == "a"


def test_all_pruned_returns_none() -> None:
    graph = _graph(
        [
            _node("p1", branch_state=BranchState.PRUNED),
            _node("p2", branch_state=BranchState.PRUNED),
        ]
    )
    assert MCTSScheduler().select_node(graph) is None


def test_puct_balances_exploration_and_exploitation_high_cpuct_prefers_less_visited() -> None:
    scheduler = MCTSScheduler(c_puct=3.0)
    graph = _graph(
        [
            _node("high_q_many_visits", score=0.1, visits=100, avg_value=1.0),
            _node("low_q_few_visits", score=0.1, visits=1, avg_value=0.2),
        ]
    )
    assert scheduler.select_node(graph) == "low_q_few_visits"


def test_pure_exploitation_cpuct_zero_picks_highest_avg_value() -> None:
    scheduler = MCTSScheduler(c_puct=0.0)
    graph = _graph(
        [
            _node("best_q", score=0.0, visits=8, avg_value=0.9),
            _node("worse_q", score=10.0, visits=8, avg_value=0.1),
        ]
    )
    assert scheduler.select_node(graph) == "best_q"


def test_backpropagation_updates_leaf_parent_and_grandparent() -> None:
    root = _node("root")
    parent = _node("parent", parent_ids=["root"])
    leaf = _node("leaf", parent_ids=["parent"])
    graph = _graph([root, parent, leaf])

    MCTSScheduler().backpropagate(graph, "leaf", reward=0.6)

    assert leaf.visits == 1 and math.isclose(leaf.avg_value, 0.6)
    assert parent.visits == 1 and math.isclose(parent.avg_value, 0.6)
    assert root.visits == 1 and math.isclose(root.avg_value, 0.6)


def test_backpropagation_with_single_root_node() -> None:
    root = _node("root")
    graph = _graph([root])

    MCTSScheduler().backpropagate(graph, "root", reward=1.0)

    assert root.visits == 1
    assert math.isclose(root.total_value, 1.0)
    assert math.isclose(root.avg_value, 1.0)


def test_observe_feedback_uses_reward_calculator_and_triggers_backpropagation() -> None:
    class SpyRewardCalculator:
        def __init__(self) -> None:
            self.calls: list[tuple[float | None, bool | None]] = []

        def calculate(self, score: float | None, decision: bool | None) -> float:
            self.calls.append((score, decision))
            return 0.75

    reward_calc = SpyRewardCalculator()
    scheduler = MCTSScheduler(reward_calculator=reward_calc)  # type: ignore[arg-type]

    root = _node("root")
    leaf = _node("leaf", parent_ids=["root"])
    graph = _graph([root, leaf])

    scheduler.observe_feedback(graph, "leaf", score=0.3, decision=False)

    assert reward_calc.calls == [(0.3, False)]
    assert leaf.visits == 1 and math.isclose(leaf.avg_value, 0.75)
    assert root.visits == 1 and math.isclose(root.avg_value, 0.75)


def test_observe_feedback_with_decision_based_reward_mode() -> None:
    scheduler = MCTSScheduler(reward_calculator=RewardCalculator(mode="decision_based"))
    node = _node("n")
    graph = _graph([node])

    scheduler.observe_feedback(graph, "n", score=None, decision=True)

    assert node.visits == 1
    assert math.isclose(node.total_value, 1.0)
    assert math.isclose(node.avg_value, 1.0)


def test_observe_feedback_with_score_based_tanh_reward() -> None:
    scheduler = MCTSScheduler(reward_calculator=RewardCalculator(mode="score_based"))
    node = _node("n")
    graph = _graph([node])

    scheduler.observe_feedback(graph, "n", score=1.0, decision=None)

    expected = math.tanh(1.0)
    assert node.visits == 1
    assert math.isclose(node.total_value, expected)
    assert math.isclose(node.avg_value, expected)


def test_get_all_scores_returns_puct_scores_for_active_nodes() -> None:
    scheduler = MCTSScheduler(c_puct=1.41)
    graph = _graph(
        [
            _node("n1", score=2.0, visits=4, avg_value=0.4),
            _node("n2", score=0.5, visits=2, avg_value=0.2),
            _node("p", score=100.0, visits=99, avg_value=99.0, branch_state=BranchState.PRUNED),
        ]
    )

    scores = scheduler.get_all_scores(graph)

    assert set(scores.keys()) == {"n1", "n2"}
    assert all(math.isfinite(v) for v in scores.values())


def test_get_all_scores_unvisited_active_nodes_are_inf() -> None:
    scheduler = MCTSScheduler()
    graph = _graph([_node("u", visits=0), _node("v", visits=3, avg_value=0.1)])

    scores = scheduler.get_all_scores(graph)

    assert math.isinf(scores["u"])
    assert scores["u"] > 0
    assert math.isfinite(scores["v"])


def test_prior_probability_affects_selection_with_same_q_and_visits() -> None:
    scheduler = MCTSScheduler(c_puct=2.0)
    graph = _graph(
        [
            _node("high_prior", score=3.0, visits=5, avg_value=0.4),
            _node("low_prior", score=-1.0, visits=5, avg_value=0.4),
        ]
    )

    assert scheduler.select_node(graph) == "high_prior"


def test_softmax_numerical_stability_with_large_potentials() -> None:
    scheduler = MCTSScheduler(c_puct=1.2)
    graph = _graph(
        [
            _node("a", score=10000.0, visits=10, avg_value=0.1),
            _node("b", score=9999.0, visits=10, avg_value=0.1),
        ]
    )

    selected = scheduler.select_node(graph)
    scores = scheduler.get_all_scores(graph)

    assert selected in {"a", "b"}
    assert all(math.isfinite(v) for v in scores.values())


def test_select_node_uses_node_visits_not_graph_visit_counts() -> None:
    scheduler = MCTSScheduler()
    graph = _graph(
        [
            _node("n1", score=0.1, visits=1, avg_value=0.1),
            _node("n2", score=0.2, visits=0),
        ],
        visit_counts={"n1": 0, "n2": 100},
    )

    assert scheduler.select_node(graph) == "n2"
