from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from v2.state import CoSTEERState


class _DefaultMockCoderPlugin:
    def develop(self, experiment: dict, proposal: dict) -> dict:
        _ = experiment
        _ = proposal
        return {"code": "print('mock')"}


class _DefaultMockRunnerPlugin:
    def run(self, code: dict) -> dict:
        return {"success": True, "output": "ok", "code": code.get("code")}


class _DefaultMockEvaluatorPlugin:
    def evaluate(self, experiment: dict, result: dict) -> dict:
        _ = experiment
        _ = result
        return {"score": 0.0, "acceptable": False}


def code_generate_node(state: dict, *, coder_plugin: Any = None) -> dict:
    coder = coder_plugin or _DefaultMockCoderPlugin()
    experiment = state.get("experiment") or {}
    proposal = state.get("proposal") or {}
    code = coder.develop(experiment=experiment, proposal=proposal)

    return {
        "code_result": code,
        "code_candidates": [code],
    }


def run_code_node(state: dict, *, runner_plugin: Any = None) -> dict:
    runner = runner_plugin or _DefaultMockRunnerPlugin()
    code_result = state.get("code_result") or {}
    run_result = runner.run(code_result)
    return {"run_result": run_result}


def evaluate_node(state: dict, *, evaluator_plugin: Any = None) -> dict:
    run_result = state.get("run_result")
    code_result = state.get("code_result")
    if run_result is None or code_result is None:
        return {}

    evaluator: Any = evaluator_plugin or _DefaultMockEvaluatorPlugin()
    experiment = state.get("experiment") or {}

    evaluate_fn = evaluator.evaluate
    try:
        feedback = evaluate_fn(experiment=experiment, result=run_result)
    except TypeError:
        feedback = evaluate_fn(run_result)

    round_number = int(state.get("round_number", 0)) + 1
    score = feedback.get("score", 0.0)

    MAX_OUTPUT_CHARS = 1000
    truncated_result = dict(run_result)
    if "output" in truncated_result:
        truncated_result["output"] = str(truncated_result["output"])[:MAX_OUTPUT_CHARS]

    new_entry = {
        "round": round_number,
        "code": code_result,
        "result": truncated_result,
        "score": score,
    }

    current_best = state.get("best_candidate")
    best = new_entry if current_best is None or score >= current_best.get("score", float("-inf")) else current_best

    return {
        "feedback": feedback,
        "round_number": round_number,
        "improvement_history": [new_entry],
        "best_candidate": best,
    }


def _should_continue(state: dict) -> str:
    if state.get("round_number", 0) >= state.get("max_rounds", 1):
        return END
    return "code_generate_node"


def build_costeer_subgraph(
    *,
    coder_plugin: Any = None,
    runner_plugin: Any = None,
    evaluator_plugin: Any = None,
) -> Any:
    graph = StateGraph(CoSTEERState)

    graph.add_node("code_generate_node", partial(code_generate_node, coder_plugin=coder_plugin))
    graph.add_node("run_code_node", partial(run_code_node, runner_plugin=runner_plugin))
    graph.add_node("evaluate_node", partial(evaluate_node, evaluator_plugin=evaluator_plugin))

    graph.add_edge(START, "evaluate_node")
    graph.add_edge("code_generate_node", "run_code_node")
    graph.add_edge("run_code_node", "evaluate_node")
    graph.add_conditional_edges("evaluate_node", _should_continue)

    return graph.compile(checkpointer=None)


__all__ = ["build_costeer_subgraph", "code_generate_node", "run_code_node", "evaluate_node"]
