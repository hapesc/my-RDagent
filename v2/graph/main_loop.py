from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, Protocol

from v2.graph.nodes import (
    coding_node,
    experiment_setup_node,
    feedback_node,
    propose_node,
    record_node,
    running_node,
)
from v2.state import MainState


class CompiledGraph(Protocol):
    nodes: dict[str, Any]

    def invoke(
        self,
        initial_state: dict,
        start_node: str | None = None,
        checkpoint_hook: Callable[[str, str | None, dict], None] | None = None,
    ) -> dict: ...


# LangGraph-compatible constants.  Custom execution engine provides features
# not available in real LangGraph: start_node, checkpoint_hook, flexible state.
START = "__start__"
END = "__end__"


class _CompiledGraph:
    def __init__(
        self,
        nodes: dict[str, Callable[[dict], dict]],
        edges: dict[str, str],
        conditional_edges: dict[str, Callable[[dict], str]],
    ) -> None:
        self.nodes = nodes
        self._edges = edges
        self._conditional_edges = conditional_edges

    def _resolve_next_node(self, current: str, state: dict) -> str:
        if current in self._conditional_edges:
            return self._conditional_edges[current](state)
        return self._edges.get(current, END)

    def invoke(
        self,
        initial_state: dict,
        start_node: str | None = None,
        checkpoint_hook: Callable[[str, str | None, dict], None] | None = None,
    ) -> dict:
        state = dict(initial_state)
        current = start_node or self._edges.get(START, END)

        while current != END:
            node_fn = self.nodes[current]
            updates = node_fn(state)
            if updates:
                state.update(updates)

            next_node = self._resolve_next_node(current, state)
            if checkpoint_hook is not None:
                checkpoint_hook(current, None if next_node == END else next_node, copy.deepcopy(state))
            current = next_node

        return state


class StateGraph:
    def __init__(self, _state_type: type[dict] | type[MainState]) -> None:
        self._nodes: dict[str, Callable[[dict], dict]] = {}
        self._edges: dict[str, str] = {}
        self._conditional_edges: dict[str, Callable[[dict], str]] = {}

    def add_node(self, name: str, fn: Callable[[dict], dict]) -> None:
        self._nodes[name] = fn

    def add_edge(self, source: str, target: str) -> None:
        self._edges[source] = target

    def add_conditional_edges(self, source: str, route_fn: Callable[[dict], str]) -> None:
        self._conditional_edges[source] = route_fn

    def compile(self, checkpointer: Any = None) -> _CompiledGraph:
        _ = checkpointer
        return _CompiledGraph(self._nodes, self._edges, self._conditional_edges)


def _next_after_record(state: dict) -> str:
    if state.get("loop_iteration", 0) < state.get("max_loops", 1):
        return "propose"
    return END


def build_main_graph(checkpointer: Any = None) -> CompiledGraph:
    graph = StateGraph(MainState)

    graph.add_node("propose", propose_node)
    graph.add_node("experiment_setup", experiment_setup_node)
    graph.add_node("coding", coding_node)
    graph.add_node("running", running_node)
    graph.add_node("feedback", feedback_node)
    graph.add_node("record", record_node)

    graph.add_edge(START, "propose")
    graph.add_edge("propose", "experiment_setup")
    graph.add_edge("experiment_setup", "coding")
    graph.add_edge("coding", "running")
    graph.add_edge("running", "feedback")
    graph.add_edge("feedback", "record")
    graph.add_conditional_edges("record", _next_after_record)

    return graph.compile(checkpointer=checkpointer)


__all__ = ["build_main_graph"]
