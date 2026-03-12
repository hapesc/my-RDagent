from __future__ import annotations


def propose_node(state: dict) -> dict:
    _ = state
    return {}


def experiment_setup_node(state: dict) -> dict:
    _ = state
    return {}


def coding_node(state: dict) -> dict:
    _ = state
    return {}


def running_node(state: dict) -> dict:
    _ = state
    return {}


def feedback_node(state: dict) -> dict:
    _ = state
    return {}


def record_node(state: dict) -> dict:
    loop_iteration = int(state.get("loop_iteration", 0)) + 1
    return {"loop_iteration": loop_iteration}


__all__ = [
    "propose_node",
    "experiment_setup_node",
    "coding_node",
    "running_node",
    "feedback_node",
    "record_node",
]
