from __future__ import annotations

from typing import Any


class _DefaultMockProposerPlugin:
    def propose(self, state: dict) -> dict:
        run_id = state.get("run_id", "mock-run")
        loop_iteration = state.get("loop_iteration", 0)
        return {
            "hypothesis": f"mock proposal for {run_id}",
            "loop_iteration": loop_iteration,
        }


class _DefaultMockRunnerPlugin:
    def run(self, code: dict) -> dict:
        _ = code
        return {"success": True, "output": "mock output"}


class _DefaultMockEvaluatorPlugin:
    def evaluate(self, experiment: dict, result: dict) -> dict:
        _ = experiment
        _ = result
        return {"score": 0.5, "decision": "continue", "reason": "mock"}


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
    try:
        from v2.graph.costeer import build_costeer_subgraph

        subgraph = build_costeer_subgraph()
        result = subgraph.invoke(state)
        return {
            "code_result": result.get("best_candidate", {}),
            "step_state": "RUNNING",
            "error": None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def running_node(state: dict) -> dict:
    if state.get("_force_runner_error"):
        return {
            "run_result": {"success": False, "error": "forced error"},
            "step_state": "FEEDBACK",
        }

    plugin = state.get("_runner_plugin") or _DefaultMockRunnerPlugin()
    try:
        run_result = plugin.run(state.get("code_result", {}))
        return {
            "run_result": run_result,
            "step_state": "FEEDBACK",
            "error": None,
        }
    except Exception as exc:
        return {
            "run_result": {"success": False, "error": str(exc)},
            "step_state": "FEEDBACK",
        }


def feedback_node(state: dict) -> dict:
    plugin: Any = state.get("_evaluator_plugin") or _DefaultMockEvaluatorPlugin()
    experiment = state.get("experiment", {})
    run_result = state.get("run_result", {})

    try:
        try:
            feedback = plugin.evaluate(experiment, run_result)
        except TypeError:
            feedback = plugin.evaluate(run_result)
        return {
            "feedback": feedback,
            "step_state": "RECORD",
            "error": None,
        }
    except Exception as exc:
        return {
            "feedback": {"score": 0.0, "decision": "retry"},
            "error": str(exc),
        }


def record_node(state: dict) -> dict:
    previous_iteration = int(state.get("loop_iteration", 0))
    loop_iteration = previous_iteration + 1
    metrics = list(state.get("metrics") or [])
    metrics.append(
        {
            "iteration": previous_iteration,
            "score": (state.get("feedback") or {}).get("score", 0.0),
        }
    )
    return {
        "loop_iteration": loop_iteration,
        "metrics": metrics,
        "step_state": "COMPLETED",
    }


__all__ = [
    "propose_node",
    "experiment_setup_node",
    "coding_node",
    "running_node",
    "feedback_node",
    "record_node",
]
