from __future__ import annotations

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
    nodes = list(graph.nodes.keys()) if hasattr(graph, "nodes") else []

    assert len(nodes) >= 6
    for expected in ["propose", "experiment_setup", "coding", "running", "feedback", "record"]:
        assert expected in nodes


def test_main_graph_invoke_completes_for_pass_through_nodes() -> None:
    graph = build_main_graph()
    result = graph.invoke(_initial_state(max_loops=1))

    assert result is not None
    assert result["loop_iteration"] >= 1


def test_main_graph_conditional_edge_loops_for_max_loops_two() -> None:
    graph = build_main_graph()
    result = graph.invoke(_initial_state(max_loops=2))

    assert result["loop_iteration"] >= 2
