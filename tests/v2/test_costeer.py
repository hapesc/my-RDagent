from __future__ import annotations

from v2.graph.costeer import build_costeer_subgraph


class _MockCoderPlugin:
    def __init__(self) -> None:
        self.calls = 0

    def develop(self, experiment: dict, proposal: dict) -> dict:
        _ = experiment
        _ = proposal
        self.calls += 1
        return {"code": f"print({self.calls})"}


class _MockRunnerPlugin:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, code: dict) -> dict:
        self.calls += 1
        return {"success": True, "output": "ok", "round": self.calls, "code": code.get("code")}


class _MockEvaluatorPlugin:
    def __init__(self, scores: list[float]) -> None:
        self._scores = scores
        self.calls = 0

    def evaluate(self, experiment: dict, result: dict) -> dict:
        _ = experiment
        _ = result
        score = self._scores[self.calls]
        self.calls += 1
        return {"score": score, "acceptable": False}


def _initial_state(max_rounds: int, round_number: int = 0) -> dict:
    return {
        "run_id": "costeer-test",
        "loop_iteration": 0,
        "max_loops": 1,
        "step_state": "CODING",
        "proposal": {"summary": "p"},
        "experiment": {"task": "t"},
        "code_result": None,
        "run_result": None,
        "feedback": None,
        "metrics": None,
        "error": None,
        "round_number": round_number,
        "max_rounds": max_rounds,
        "code_candidates": [],
        "best_candidate": None,
        "improvement_history": [],
    }


def test_costeer_single_round_records_history_and_best_candidate() -> None:
    coder = _MockCoderPlugin()
    runner = _MockRunnerPlugin()
    evaluator = _MockEvaluatorPlugin(scores=[0.6])

    graph = build_costeer_subgraph(
        coder_plugin=coder,
        runner_plugin=runner,
        evaluator_plugin=evaluator,
    )
    result = graph.invoke(_initial_state(max_rounds=1))

    assert result["round_number"] == 1
    assert len(result["improvement_history"]) == 1
    assert result["improvement_history"][0] == {
        "round": 1,
        "code": {"code": "print(1)"},
        "result": {"success": True, "output": "ok", "round": 1, "code": "print(1)"},
        "score": 0.6,
    }
    assert result["best_candidate"] is not None
    assert result["best_candidate"]["score"] == 0.6


def test_costeer_multi_round_appends_history_and_selects_highest_score() -> None:
    coder = _MockCoderPlugin()
    runner = _MockRunnerPlugin()
    evaluator = _MockEvaluatorPlugin(scores=[0.6, 0.9, 0.7])

    graph = build_costeer_subgraph(
        coder_plugin=coder,
        runner_plugin=runner,
        evaluator_plugin=evaluator,
    )
    result = graph.invoke(_initial_state(max_rounds=3))

    assert result["round_number"] == 3
    assert len(result["improvement_history"]) == 3
    assert [item["round"] for item in result["improvement_history"]] == [1, 2, 3]
    assert result["best_candidate"] is not None
    assert result["best_candidate"]["score"] == 0.9
    assert result["best_candidate"]["round"] == 2


def test_costeer_honors_round_number_boundary_condition() -> None:
    coder = _MockCoderPlugin()
    runner = _MockRunnerPlugin()
    evaluator = _MockEvaluatorPlugin(scores=[0.8])

    graph = build_costeer_subgraph(
        coder_plugin=coder,
        runner_plugin=runner,
        evaluator_plugin=evaluator,
    )
    result = graph.invoke(_initial_state(max_rounds=2, round_number=1))

    assert result["round_number"] == 2
    assert len(result["improvement_history"]) == 1
    assert coder.calls == 1
    assert runner.calls == 1
    assert evaluator.calls == 1


def test_costeer_max_rounds_zero_executes_zero_rounds() -> None:
    coder = _MockCoderPlugin()
    runner = _MockRunnerPlugin()
    evaluator = _MockEvaluatorPlugin(scores=[])

    graph = build_costeer_subgraph(
        coder_plugin=coder,
        runner_plugin=runner,
        evaluator_plugin=evaluator,
    )
    initial = _initial_state(max_rounds=0)
    result = graph.invoke(initial)

    assert result["round_number"] == 0
    assert result["improvement_history"] == []
    assert result["best_candidate"] is None
    assert coder.calls == 0
    assert runner.calls == 0
    assert evaluator.calls == 0
