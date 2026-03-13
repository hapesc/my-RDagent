from __future__ import annotations

from v2.graph.exploration import select_exploration_node


class _FakeScheduler:
    def select_node(self, graph: object) -> str:
        return "node-42"


class _FakeGraph:
    pass


def test_select_exploration_node_returns_node_id() -> None:
    result = select_exploration_node(_FakeScheduler(), _FakeGraph())
    assert result == "node-42"


def test_select_exploration_node_handles_none_scheduler() -> None:
    result = select_exploration_node(None, None)
    assert result is None


def test_select_exploration_node_handles_none_graph() -> None:
    result = select_exploration_node(_FakeScheduler(), None)
    assert result is None
