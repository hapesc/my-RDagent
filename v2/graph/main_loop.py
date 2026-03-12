from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from v2.graph.nodes import (
    coding_node,
    experiment_setup_node,
    feedback_node,
    propose_node,
    record_node,
    running_node,
)
from v2.state import MainState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph as CompiledGraph

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:
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

        def invoke(self, initial_state: dict) -> dict:
            state = dict(initial_state)
            current = self._edges.get(START, END)

            while current != END:
                node_fn = self.nodes[current]
                updates = node_fn(state)
                if updates:
                    state.update(updates)

                if current in self._conditional_edges:
                    current = self._conditional_edges[current](state)
                else:
                    current = self._edges.get(current, END)

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

    CompiledGraph = _CompiledGraph


def _next_after_record(state: dict) -> str:
    if state.get("loop_iteration", 0) < state.get("max_loops", 1):
        return "propose"
    return END


def build_main_graph(checkpointer: Any = None) -> "CompiledGraph":
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
