from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from v2.graph.main_loop import build_main_graph


def _initial_state(max_loops: int = 1) -> dict:
    return {
        "run_id": "test-run",
        "loop_iteration": 0,
        "max_loops": max_loops,
        "step_state": "CREATED",
        "proposal": None,
        "experiment": None,
        "code_result": None,
        "run_result": None,
        "feedback": None,
        "metrics": None,
        "error": None,
    }


def test_main_graph_compiles_and_contains_six_nodes() -> None:
    graph = build_main_graph()
    node_names = {n for n in graph.get_graph().nodes if not n.startswith("__")}

    assert len(node_names) >= 6
    for expected in ["propose", "experiment_setup", "coding", "running", "feedback", "record"]:
        assert expected in node_names


def test_main_graph_invoke_completes_for_pass_through_nodes() -> None:
    graph = build_main_graph()
    result = graph.invoke(_initial_state(max_loops=1))

    assert result is not None
    assert result["loop_iteration"] >= 1


def test_main_graph_conditional_edge_loops_for_max_loops_two() -> None:
    graph = build_main_graph()
    result = graph.invoke(_initial_state(max_loops=2))

    assert result["loop_iteration"] >= 2


def test_main_graph_can_resume_from_specific_node() -> None:
    checkpointer = MemorySaver()
    graph = build_main_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "resume-test"}}

    state = _initial_state(max_loops=1)
    state["proposal"] = {"id": "p1"}
    state["experiment"] = {"id": "e1"}

    graph.update_state(config, state, as_node="experiment_setup")
    snapshot = graph.get_state(config)
    assert "coding" in snapshot.next

    events = list(graph.stream(None, config, stream_mode="updates"))
    executed_nodes = [list(e.keys())[0] for e in events if not list(e.keys())[0].startswith("__")]
    assert "propose" not in executed_nodes
    assert "experiment_setup" not in executed_nodes
    assert "coding" in executed_nodes
    assert "running" in executed_nodes
    assert "feedback" in executed_nodes
    assert "record" in executed_nodes


def test_main_graph_stream_emits_event_per_node() -> None:
    checkpointer = MemorySaver()
    graph = build_main_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "stream-test"}}

    events = list(graph.stream(_initial_state(max_loops=1), config, stream_mode="updates"))
    executed_nodes = [list(e.keys())[0] for e in events if not list(e.keys())[0].startswith("__")]

    assert executed_nodes == ["propose", "experiment_setup", "coding", "running", "feedback", "record"]
