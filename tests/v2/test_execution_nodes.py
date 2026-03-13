from __future__ import annotations

from v2.graph.nodes import coding_node, feedback_node, record_node, running_node


class _MockRunnerPlugin:
    def __init__(self) -> None:
        self.seen_code: dict | None = None

    def run(self, code: dict) -> dict:
        self.seen_code = code
        return {"success": True, "output": "runner output", "code": code}


class _FailingRunnerPlugin:
    def run(self, code: dict) -> dict:
        raise RuntimeError("forced error")


class _MockEvaluatorPlugin:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, dict]] = []

    def evaluate(self, experiment: dict, result: dict) -> dict:
        self.calls.append((experiment, result))
        return {"score": 0.9, "decision": "accept", "reason": "looks good"}


class _SingleArgEvaluatorPlugin:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def evaluate(self, result: dict) -> dict:
        self.calls.append(result)
        return {"score": 0.4, "decision": "continue", "reason": "single arg"}


def test_coding_node_invokes_costeer_and_sets_step_state_to_running() -> None:
    result = coding_node(
        {
            "run_id": "test-run",
            "loop_iteration": 0,
            "max_loops": 1,
            "step_state": "CODING",
            "proposal": {"summary": "test proposal"},
            "experiment": {"task": "test task"},
            "code_result": None,
            "run_result": None,
            "feedback": None,
            "metrics": [],
            "error": None,
            "iteration_history": [],
        }
    )

    assert result["step_state"] == "RUNNING"
    assert result["error"] is None
    assert "code_result" in result
    assert result["code_result"] is not None


def test_running_node_calls_runner_plugin_and_stores_run_result() -> None:
    runner = _MockRunnerPlugin()

    result = running_node(
        {
            "step_state": "RUNNING",
            "code_result": {"code": "print('hello')"},
        },
        runner_plugin=runner,
    )

    assert runner.seen_code == {"code": "print('hello')"}
    assert result == {
        "run_result": {"success": True, "output": "runner output", "code": {"code": "print('hello')"}},
        "step_state": "FEEDBACK",
        "error": None,
    }


def test_running_node_handles_plugin_error_gracefully() -> None:
    result = running_node(
        {
            "step_state": "RUNNING",
            "code_result": {"code": "print('hello')"},
        },
        runner_plugin=_FailingRunnerPlugin(),
    )

    assert result["run_result"]["success"] is False
    assert "forced error" in result["run_result"]["error"]
    assert result["step_state"] == "FEEDBACK"


def test_feedback_node_calls_evaluator_plugin_and_stores_feedback() -> None:
    evaluator = _MockEvaluatorPlugin()

    result = feedback_node(
        {
            "step_state": "FEEDBACK",
            "experiment": {"task": "benchmark"},
            "run_result": {"success": True, "output": "ok"},
        },
        evaluator_plugin=evaluator,
    )

    assert evaluator.calls == [({"task": "benchmark"}, {"success": True, "output": "ok"})]
    assert result == {
        "feedback": {"score": 0.9, "decision": "accept", "reason": "looks good"},
        "step_state": "RECORD",
        "error": None,
    }


def test_feedback_node_falls_back_to_single_argument_evaluate() -> None:
    evaluator = _SingleArgEvaluatorPlugin()

    result = feedback_node(
        {
            "step_state": "FEEDBACK",
            "experiment": {"task": "benchmark"},
            "run_result": {"success": True, "output": "ok"},
        },
        evaluator_plugin=evaluator,
    )

    assert evaluator.calls == [{"success": True, "output": "ok"}]
    assert result == {
        "feedback": {"score": 0.4, "decision": "continue", "reason": "single arg"},
        "step_state": "RECORD",
        "error": None,
    }


def test_record_node_increments_iteration_and_appends_metrics() -> None:
    result = record_node(
        {
            "loop_iteration": 2,
            "step_state": "RECORD",
            "feedback": {"score": 0.75, "decision": "accept"},
            "metrics": [],
            "proposal": {"hypothesis": "test hypothesis"},
        }
    )

    assert result == {
        "loop_iteration": 3,
        "metrics": [{"iteration": 2, "score": 0.75}],
        "step_state": "COMPLETED",
        "iteration_history": [
            {
                "iteration": 3,
                "hypothesis": "test hypothesis",
                "score": 0.75,
                "outcome": "accept",
            }
        ],
    }
