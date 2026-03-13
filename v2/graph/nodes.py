from __future__ import annotations

import json
from typing import Any


def _estimate_tokens(data: Any) -> int:
    """Estimate token count using ~4 chars per token heuristic."""
    if data is None:
        return 0
    if isinstance(data, str):
        return len(data) // 4
    try:
        text = json.dumps(data, default=str)
    except (TypeError, ValueError):
        text = str(data)
    return len(text) // 4


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


def propose_node(state: dict, *, proposer_plugin: Any = None) -> dict:
    plugin = proposer_plugin or _DefaultMockProposerPlugin()
    try:
        proposal = plugin.propose(state)
    except Exception as exc:
        return {"error": str(exc), "tokens_used": 0}

    estimated = _estimate_tokens(proposal)
    return {
        "proposal": proposal,
        "step_state": "EXPERIMENT_READY",
        "error": None,
        "tokens_used": estimated,
    }


def experiment_setup_node(state: dict) -> dict:
    try:
        proposal = state.get("proposal")
        experiment = {"proposal": proposal}
    except Exception as exc:
        return {"error": str(exc), "tokens_used": 0}

    return {
        "experiment": experiment,
        "step_state": "CODING",
        "error": None,
        "tokens_used": 0,
    }


def coding_node(
    state: dict,
    *,
    coder_plugin: Any = None,
    runner_plugin: Any = None,
    evaluator_plugin: Any = None,
) -> dict:
    try:
        from v2.graph.costeer import build_costeer_subgraph

        subgraph = build_costeer_subgraph(
            coder_plugin=coder_plugin,
            runner_plugin=runner_plugin,
            evaluator_plugin=evaluator_plugin,
        )
        result = subgraph.invoke(state)
        code_result = result.get("best_candidate", {})
        estimated = _estimate_tokens(code_result)
        return {
            "code_result": code_result,
            "step_state": "RUNNING",
            "error": None,
            "tokens_used": estimated,
        }
    except Exception as exc:
        return {"error": str(exc), "tokens_used": 0}


def running_node(state: dict, *, runner_plugin: Any = None) -> dict:
    plugin = runner_plugin or _DefaultMockRunnerPlugin()
    try:
        run_result = plugin.run(state.get("code_result", {}))
        estimated = _estimate_tokens(run_result)
        return {
            "run_result": run_result,
            "step_state": "FEEDBACK",
            "error": None,
            "tokens_used": estimated,
        }
    except Exception as exc:
        return {
            "run_result": {"success": False, "error": str(exc)},
            "step_state": "FEEDBACK",
            "tokens_used": 0,
        }


def feedback_node(state: dict, *, evaluator_plugin: Any = None) -> dict:
    plugin: Any = evaluator_plugin or _DefaultMockEvaluatorPlugin()
    experiment = state.get("experiment", {})
    run_result = state.get("run_result", {})

    try:
        try:
            feedback = plugin.evaluate(experiment, run_result)
        except TypeError:
            feedback = plugin.evaluate(run_result)
        estimated = _estimate_tokens(feedback)
        return {
            "feedback": feedback,
            "step_state": "RECORD",
            "error": None,
            "tokens_used": estimated,
        }
    except Exception as exc:
        return {
            "feedback": {"score": 0.0, "decision": "retry"},
            "error": str(exc),
            "tokens_used": 0,
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
        "tokens_used": 0,
    }


__all__ = [
    "propose_node",
    "experiment_setup_node",
    "coding_node",
    "running_node",
    "feedback_node",
    "record_node",
    "_estimate_tokens",
]
