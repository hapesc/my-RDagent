from __future__ import annotations


class _DefaultMockProposerPlugin:
    def propose(self, state: dict) -> dict:
        run_id = state.get("run_id", "mock-run")
        loop_iteration = state.get("loop_iteration", 0)
        return {
            "hypothesis": f"mock proposal for {run_id}",
            "loop_iteration": loop_iteration,
        }


def propose_node(state: dict) -> dict:
    if state.get("_force_llm_error"):
        return {"error": "forced error"}

    plugin = state.get("_proposer_plugin") or _DefaultMockProposerPlugin()
    try:
        proposal = plugin.propose(state)
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "proposal": proposal,
        "step_state": "EXPERIMENT_READY",
        "error": None,
    }


def experiment_setup_node(state: dict) -> dict:
    try:
        proposal = state.get("proposal")
        experiment = {"proposal": proposal}
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "experiment": experiment,
        "step_state": "CODING",
        "error": None,
    }


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
