from __future__ import annotations

from types import SimpleNamespace

from data_models import EventType
from scripts.e2e_gemini_test import evaluate_smoke_success


def _event(event_type: EventType, step_name: str, payload: dict) -> SimpleNamespace:
    return SimpleNamespace(event_type=event_type, step_name=step_name, payload=payload)


def test_evaluate_smoke_success_requires_usefulness_gate_pass() -> None:
    ok, reason = evaluate_smoke_success(
        [
            _event(
                EventType.EXECUTION_FINISHED,
                "running",
                {
                    "usefulness_status": "INELIGIBLE",
                    "usefulness_gate_reason": "scene validator rejected: generic synthesized summary",
                },
            ),
            _event(
                EventType.FEEDBACK_GENERATED,
                "feedback",
                {"acceptable": True, "reason": "looks good"},
            ),
        ],
    )

    assert not ok
    assert reason == "usefulness validator rejected output: scene validator rejected: generic synthesized summary"


def test_evaluate_smoke_success_requires_feedback_acceptance() -> None:
    ok, reason = evaluate_smoke_success(
        [
            _event(
                EventType.EXECUTION_FINISHED,
                "running",
                {
                    "usefulness_status": "ELIGIBLE",
                    "usefulness_gate_reason": "eligible",
                },
            ),
            _event(
                EventType.FEEDBACK_GENERATED,
                "feedback",
                {"acceptable": False, "reason": "feedback unacceptable"},
            ),
        ],
    )

    assert not ok
    assert reason == "feedback rejected smoke result: feedback unacceptable"


def test_evaluate_smoke_success_accepts_completed_useful_run() -> None:
    ok, reason = evaluate_smoke_success(
        [
            _event(
                EventType.EXECUTION_FINISHED,
                "running",
                {
                    "usefulness_status": "ELIGIBLE",
                    "usefulness_gate_reason": "eligible",
                },
            ),
            _event(
                EventType.FEEDBACK_GENERATED,
                "feedback",
                {"acceptable": True, "reason": "acceptable"},
            ),
        ],
    )

    assert ok
    assert reason == "usefulness validators passed"


def test_evaluate_smoke_success_accepts_running_status_with_valid_gates() -> None:
    """Smoke success should depend on usefulness/feedback gates, not run status.
    
    In single-loop smoke execution, the run may still be RUNNING after the loop
    completes (max_loops affects loop iteration count, not run state transition).
    Success must be based on validator gates, not completion status.
    """
    ok, reason = evaluate_smoke_success(
        [
            _event(
                EventType.EXECUTION_FINISHED,
                "running",
                {
                    "usefulness_status": "ELIGIBLE",
                    "usefulness_gate_reason": "eligible",
                },
            ),
            _event(
                EventType.FEEDBACK_GENERATED,
                "feedback",
                {"acceptable": True, "reason": "acceptable"},
            ),
        ],
    )

    assert ok
    assert reason == "usefulness validators passed"
