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


def test_main_graph_can_resume_from_specific_node() -> None:
    graph = build_main_graph()
    call_order: list[str] = []

    def _recording_node(name: str):
        def _node(_state: dict) -> dict:
            call_order.append(name)
            if name == "record":
                return {"loop_iteration": 1}
            return {}

        return _node

    for node_name in ["propose", "experiment_setup", "coding", "running", "feedback", "record"]:
        graph.nodes[node_name] = _recording_node(node_name)

    result = graph.invoke(_initial_state(max_loops=1), start_node="coding")

    assert result["loop_iteration"] == 1
    assert call_order == ["coding", "running", "feedback", "record"]


def test_main_graph_invokes_checkpoint_hook_after_each_successful_node() -> None:
    graph = build_main_graph()
    checkpoint_calls: list[tuple[str, str | None, dict]] = []

    def _recording_node(name: str, updates: dict):
        def _node(_state: dict) -> dict:
            return dict(updates)

        return _node

    graph.nodes["propose"] = _recording_node("propose", {"proposal": {"id": "p1"}})
    graph.nodes["experiment_setup"] = _recording_node("experiment_setup", {"experiment": {"id": "e1"}})
    graph.nodes["coding"] = _recording_node("coding", {"code_result": {"id": "c1"}})
    graph.nodes["running"] = _recording_node("running", {"run_result": {"id": "r1"}})
    graph.nodes["feedback"] = _recording_node("feedback", {"feedback": {"id": "f1"}})
    graph.nodes["record"] = _recording_node("record", {"loop_iteration": 1, "metrics": {"score": 1.0}})

    result = graph.invoke(
        _initial_state(max_loops=1),
        checkpoint_hook=lambda last_completed_node, next_node, state_snapshot: checkpoint_calls.append(
            (last_completed_node, next_node, state_snapshot)
        ),
    )

    assert result["loop_iteration"] == 1
    assert checkpoint_calls == [
        ("propose", "experiment_setup", {**_initial_state(max_loops=1), "proposal": {"id": "p1"}}),
        (
            "experiment_setup",
            "coding",
            {**_initial_state(max_loops=1), "proposal": {"id": "p1"}, "experiment": {"id": "e1"}},
        ),
        (
            "coding",
            "running",
            {
                **_initial_state(max_loops=1),
                "proposal": {"id": "p1"},
                "experiment": {"id": "e1"},
                "code_result": {"id": "c1"},
            },
        ),
        (
            "running",
            "feedback",
            {
                **_initial_state(max_loops=1),
                "proposal": {"id": "p1"},
                "experiment": {"id": "e1"},
                "code_result": {"id": "c1"},
                "run_result": {"id": "r1"},
            },
        ),
        (
            "feedback",
            "record",
            {
                **_initial_state(max_loops=1),
                "proposal": {"id": "p1"},
                "experiment": {"id": "e1"},
                "code_result": {"id": "c1"},
                "run_result": {"id": "r1"},
                "feedback": {"id": "f1"},
            },
        ),
        (
            "record",
            None,
            {
                **_initial_state(max_loops=1),
                "proposal": {"id": "p1"},
                "experiment": {"id": "e1"},
                "code_result": {"id": "c1"},
                "run_result": {"id": "r1"},
                "feedback": {"id": "f1"},
                "loop_iteration": 1,
                "metrics": {"score": 1.0},
            },
        ),
    ]
