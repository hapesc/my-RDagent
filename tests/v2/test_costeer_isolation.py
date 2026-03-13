from __future__ import annotations


def test_coding_node_does_not_leak_internal_state() -> None:
    from v2.graph.nodes import coding_node

    state = {
        "run_id": "test",
        "loop_iteration": 0,
        "max_loops": 1,
        "proposal": {"summary": "test"},
        "code_result": None,
        "step_state": "CODING",
        "experiment": {"component": "test"},
        "tokens_used": 0,
        "token_budget": 0,
        "iteration_history": [],
    }
    result = coding_node(state)

    # Internal CoSTEER keys must NOT leak into the parent graph
    assert "improvement_history" not in result
    assert "code_candidates" not in result
    assert "round_number" not in result
    assert "max_rounds" not in result
    assert "best_candidate" not in result

    # Only expected keys should be present
    assert "code_result" in result
    assert "step_state" in result
    assert "error" in result
    assert "tokens_used" in result


def test_coding_node_returns_exactly_four_keys() -> None:
    from v2.graph.nodes import coding_node

    state = {
        "run_id": "test",
        "loop_iteration": 0,
        "max_loops": 1,
        "proposal": {"summary": "test"},
        "code_result": None,
        "step_state": "CODING",
        "experiment": {"component": "test"},
        "tokens_used": 0,
        "token_budget": 0,
        "iteration_history": [],
    }
    result = coding_node(state)

    expected_keys = {"code_result", "step_state", "error", "tokens_used"}
    assert set(result.keys()) == expected_keys


def test_costeer_subgraph_compiled_without_checkpointer() -> None:
    from v2.graph.costeer import build_costeer_subgraph

    graph = build_costeer_subgraph()
    # A subgraph compiled with checkpointer=None should not have
    # a checkpointer attribute (or it should be None)
    checkpointer = getattr(graph, "checkpointer", None)
    assert checkpointer is None
