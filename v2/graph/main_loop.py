from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from v2.graph.budget_guard import budget_check
from v2.graph.nodes import (
    coding_node,
    experiment_setup_node,
    feedback_node,
    propose_node,
    record_node,
    running_node,
)
from v2.state import MainState


def _next_after_record(state: dict) -> str:
    if state.get("loop_iteration", 0) < state.get("max_loops", 1):
        return "propose"
    return END


def build_main_graph(
    *,
    checkpointer: Any = None,
    proposer_plugin: Any = None,
    coder_plugin: Any = None,
    runner_plugin: Any = None,
    evaluator_plugin: Any = None,
    memory_write_fn: Any = None,
) -> Any:
    graph = StateGraph(MainState)

    graph.add_node("propose", partial(propose_node, proposer_plugin=proposer_plugin))
    graph.add_node("experiment_setup", experiment_setup_node)
    graph.add_node(
        "coding",
        partial(coding_node, coder_plugin=coder_plugin, runner_plugin=runner_plugin, evaluator_plugin=evaluator_plugin),
    )
    graph.add_node("running", partial(running_node, runner_plugin=runner_plugin))
    graph.add_node(
        "feedback",
        partial(feedback_node, evaluator_plugin=evaluator_plugin, memory_write_fn=memory_write_fn),
    )
    graph.add_node("record", record_node)

    graph.add_edge(START, "propose")
    graph.add_conditional_edges("propose", budget_check, {"continue": "experiment_setup", "over_budget": END})
    graph.add_edge("experiment_setup", "coding")
    graph.add_conditional_edges("coding", budget_check, {"continue": "running", "over_budget": END})
    graph.add_edge("running", "feedback")
    graph.add_conditional_edges("feedback", budget_check, {"continue": "record", "over_budget": END})
    graph.add_conditional_edges("record", _next_after_record)

    return graph.compile(checkpointer=checkpointer)


__all__ = ["build_main_graph"]
