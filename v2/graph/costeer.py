from __future__ import annotations

from typing import Any

from v2.graph.main_loop import END, START, CompiledGraph, StateGraph
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


def code_generate_node(state: dict) -> dict:
    coder = state.get("_coder_plugin") or _DefaultMockCoderPlugin()
    experiment = state.get("experiment") or {}
    proposal = state.get("proposal") or {}
    code = coder.develop(experiment=experiment, proposal=proposal)

    code_candidates = list(state.get("code_candidates") or [])
    code_candidates.append(code)

    return {
        "code_result": code,
        "code_candidates": code_candidates,
    }


def run_code_node(state: dict) -> dict:
    runner = state.get("_runner_plugin") or _DefaultMockRunnerPlugin()
    code_result = state.get("code_result") or {}
    run_result = runner.run(code_result)
    return {"run_result": run_result}


def evaluate_node(state: dict) -> dict:
    run_result = state.get("run_result")
    code_result = state.get("code_result")
    if run_result is None or code_result is None:
        return {}

    evaluator: Any = state.get("_evaluator_plugin") or _DefaultMockEvaluatorPlugin()
    experiment = state.get("experiment") or {}

    evaluate_fn = evaluator.evaluate
    try:
        feedback = evaluate_fn(experiment=experiment, result=run_result)
    except TypeError:
        feedback = evaluate_fn(run_result)

    round_number = int(state.get("round_number", 0)) + 1
    score = feedback.get("score", 0.0)

    history = list(state.get("improvement_history") or [])
    history.append(
        {
            "round": round_number,
            "code": code_result,
            "result": run_result,
            "score": score,
        }
    )

    best_candidate = max(history, key=lambda item: item.get("score", float("-inf"))) if history else None

    return {
        "feedback": feedback,
        "round_number": round_number,
        "improvement_history": history,
        "best_candidate": best_candidate,
    }


def _should_continue(state: dict) -> str:
    if state.get("round_number", 0) >= state.get("max_rounds", 1):
        return END
    return "code_generate_node"


def build_costeer_subgraph(checkpointer: Any = None) -> CompiledGraph:
    graph = StateGraph(CoSTEERState)

    graph.add_node("code_generate_node", code_generate_node)
    graph.add_node("run_code_node", run_code_node)
    graph.add_node("evaluate_node", evaluate_node)

    graph.add_edge(START, "evaluate_node")
    graph.add_edge("code_generate_node", "run_code_node")
    graph.add_edge("run_code_node", "evaluate_node")
    graph.add_conditional_edges("evaluate_node", _should_continue)

    return graph.compile(checkpointer=checkpointer)


__all__ = ["build_costeer_subgraph", "code_generate_node", "run_code_node", "evaluate_node"]
