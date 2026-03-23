from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import pytest

from v3.contracts.preflight import (
    PreflightBlockerCategory,
    PreflightBlockersByCategory,
    PreflightReadiness,
    PreflightResult,
)
from v3.contracts.recovery import RecoveryDisposition
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus

rd_code_module = importlib.import_module("v3.entry.rd_code")
rd_evaluate_module = importlib.import_module("v3.entry.rd_evaluate")
rd_execute_module = importlib.import_module("v3.entry.rd_execute")
rd_propose_module = importlib.import_module("v3.entry.rd_propose")


@dataclass(frozen=True)
class EntryCase:
    module: Any
    func_name: str
    stage_key: StageKey
    blocked_skill: str
    continue_skill: str
    kwargs: dict[str, Any]


class _FakeDecision:
    def __init__(self, outcome: RecoveryDisposition) -> None:
        self.disposition = outcome
        self.recovery_assessment = outcome
        self.resume_stage_iteration = 1
        self.replay_artifact_ids = ["artifact-replay-001"]

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        value = self.disposition.value
        return {
            "disposition": value,
            "recovery_assessment": value,
            "resume_stage_iteration": self.resume_stage_iteration,
            "replay_artifact_ids": list(self.replay_artifact_ids),
        }


class _FakeRecoveryAssessment:
    @staticmethod
    def model_validate(value: Any) -> Any:
        return value


class _FakePreflightService:
    def __init__(self, result: PreflightResult) -> None:
        self._result = result

    def assess(self, **_: Any) -> PreflightResult:
        return self._result


ENTRY_CASES = [
    EntryCase(
        module=rd_propose_module,
        func_name="rd_propose",
        stage_key=StageKey.FRAMING,
        blocked_skill="rd-propose",
        continue_skill="rd-code",
        kwargs={},
    ),
    EntryCase(
        module=rd_code_module,
        func_name="rd_code",
        stage_key=StageKey.BUILD,
        blocked_skill="rd-code",
        continue_skill="rd-execute",
        kwargs={},
    ),
    EntryCase(
        module=rd_execute_module,
        func_name="rd_execute",
        stage_key=StageKey.VERIFY,
        blocked_skill="rd-execute",
        continue_skill="rd-evaluate",
        kwargs={},
    ),
    EntryCase(
        module=rd_evaluate_module,
        func_name="rd_evaluate",
        stage_key=StageKey.SYNTHESIZE,
        blocked_skill="rd-evaluate",
        continue_skill="rd-propose",
        kwargs={"recommendation": "continue"},
    ),
]


def _next_stage_key(stage_key: StageKey) -> StageKey | None:
    return {
        StageKey.FRAMING: StageKey.BUILD,
        StageKey.BUILD: StageKey.VERIFY,
        StageKey.VERIFY: StageKey.SYNTHESIZE,
        StageKey.SYNTHESIZE: None,
    }[stage_key]


def _stage_payload(*, stage_key: StageKey, status: StageStatus) -> dict[str, Any]:
    return StageSnapshot(
        stage_key=stage_key,
        stage_iteration=1,
        status=status,
        summary=f"{stage_key.value} summary",
        artifact_ids=[f"{stage_key.value}-artifact-001"],
        next_stage_key=_next_stage_key(stage_key),
    ).model_dump(mode="json")


def _preflight_result(
    *,
    readiness: PreflightReadiness,
    stage_key: StageKey,
    recommended_next_skill: str,
) -> PreflightResult:
    if readiness is PreflightReadiness.EXECUTABLE:
        return PreflightResult(
            run_id="run-001",
            branch_id="branch-001",
            stage_key=stage_key,
            recommended_next_skill=recommended_next_skill,
            readiness=readiness,
            primary_blocker_category=None,
            primary_blocker_reason=None,
            repair_action="None - canonical preflight truth passed.",
            blockers_by_category=PreflightBlockersByCategory(),
        )
    return PreflightResult(
        run_id="run-001",
        branch_id="branch-001",
        stage_key=stage_key,
        recommended_next_skill=recommended_next_skill,
        readiness=readiness,
        primary_blocker_category=PreflightBlockerCategory.DEPENDENCY,
        primary_blocker_reason="Required dependency pytest is missing.",
        repair_action=f"Run `uv sync --extra test` before continuing with {recommended_next_skill}.",
        blockers_by_category=PreflightBlockersByCategory(),
    )


def _configure_entry(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
    *,
    stage_status: StageStatus,
    preflight_readiness: PreflightReadiness,
    decision: RecoveryDisposition,
    recovery_present: bool = True,
) -> None:
    stage_payload = _stage_payload(stage_key=case.stage_key, status=stage_status)

    monkeypatch.setattr(
        case.module,
        "rd_run_get",
        lambda *args, **kwargs: {"structuredContent": {"run": {"run_id": "run-001"}}},
    )
    monkeypatch.setattr(
        case.module,
        "rd_branch_get",
        lambda *args, **kwargs: {"structuredContent": {"branch": {"branch_id": "branch-001", "run_id": "run-001"}}},
    )
    monkeypatch.setattr(
        case.module,
        "rd_stage_get",
        lambda *args, **kwargs: {"structuredContent": {"stage": dict(stage_payload)}},
    )
    monkeypatch.setattr(
        case.module,
        "rd_artifact_list",
        lambda *args, **kwargs: {"structuredContent": {"items": []}},
    )
    monkeypatch.setattr(case.module, "RecoveryAssessment", _FakeRecoveryAssessment)

    if recovery_present:
        monkeypatch.setattr(
            case.module,
            "rd_recovery_assess",
            lambda *args, **kwargs: {"structuredContent": {"assessment": {"ok": True}}},
        )
    else:

        def _missing_recovery(*args: Any, **kwargs: Any) -> dict[str, Any]:
            raise KeyError("missing recovery")

        monkeypatch.setattr(case.module, "rd_recovery_assess", _missing_recovery)

    monkeypatch.setattr(
        case.module,
        "plan_resume_decision",
        lambda *args, **kwargs: _FakeDecision(decision),
    )
    monkeypatch.setattr(
        case.module,
        "rd_stage_complete",
        lambda *args, **kwargs: {
            "structuredContent": {
                "branch": {"branch_id": "branch-001", "run_id": "run-001"},
                "stage": dict(stage_payload),
            }
        },
    )
    monkeypatch.setattr(
        case.module,
        "rd_stage_replay",
        lambda *args, **kwargs: {
            "structuredContent": {
                "branch": {"branch_id": "branch-001", "run_id": "run-001"},
                "stage": dict(stage_payload),
            }
        },
    )
    if hasattr(case.module, "rd_stage_block"):
        monkeypatch.setattr(
            case.module,
            "rd_stage_block",
            lambda *args, **kwargs: {
                "structuredContent": {
                    "branch": {"branch_id": "branch-001", "run_id": "run-001"},
                    "stage": dict(stage_payload),
                }
            },
        )

    monkeypatch.setattr(
        case.module,
        "PreflightService",
        lambda *args, **kwargs: _FakePreflightService(
            _preflight_result(
                readiness=preflight_readiness,
                stage_key=case.stage_key,
                recommended_next_skill=case.blocked_skill,
            )
        ),
    )


def _invoke(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
    *,
    stage_status: StageStatus,
    preflight_readiness: PreflightReadiness,
    decision: RecoveryDisposition,
    blocking_reasons: list[str] | None = None,
    recovery_present: bool = True,
) -> dict[str, Any]:
    _configure_entry(
        monkeypatch,
        case,
        stage_status=stage_status,
        preflight_readiness=preflight_readiness,
        decision=decision,
        recovery_present=recovery_present,
    )
    func = getattr(case.module, case.func_name)
    kwargs = {
        "run_id": "run-001",
        "branch_id": "branch-001",
        "summary": "Stage execution requested.",
        "artifact_ids": ["artifact-001"],
        "state_store": object(),
        "run_service": object(),
        "recovery_service": object(),
        "transition_service": object(),
        "preflight_service": None,
    }
    kwargs.update(case.kwargs)
    if blocking_reasons is not None:
        kwargs["blocking_reasons"] = list(blocking_reasons)
    return func(**kwargs)


@pytest.mark.parametrize("case", ENTRY_CASES, ids=lambda case: case.func_name)
def test_stage_entries_report_preflight_blocked_outcome(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
) -> None:
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.READY,
        preflight_readiness=PreflightReadiness.BLOCKED,
        decision=RecoveryDisposition.REBUILD,
    )

    assert result["structuredContent"]["outcome"] == "preflight_blocked"


@pytest.mark.parametrize("case", ENTRY_CASES, ids=lambda case: case.func_name)
def test_stage_entries_report_reused_outcome(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
) -> None:
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.COMPLETED,
        preflight_readiness=PreflightReadiness.EXECUTABLE,
        decision=RecoveryDisposition.REUSE,
    )

    assert result["structuredContent"]["outcome"] == "reused"


@pytest.mark.parametrize("case", ENTRY_CASES, ids=lambda case: case.func_name)
def test_stage_entries_report_review_outcome(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
) -> None:
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.BLOCKED,
        preflight_readiness=PreflightReadiness.EXECUTABLE,
        decision=RecoveryDisposition.REVIEW,
        recovery_present=False,
    )

    assert result["structuredContent"]["outcome"] == "review"


@pytest.mark.parametrize("case", ENTRY_CASES, ids=lambda case: case.func_name)
def test_stage_entries_report_replay_outcome(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
) -> None:
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.COMPLETED,
        preflight_readiness=PreflightReadiness.EXECUTABLE,
        decision=RecoveryDisposition.REPLAY,
    )

    assert result["structuredContent"]["outcome"] == "replay"


@pytest.mark.parametrize("case", ENTRY_CASES, ids=lambda case: case.func_name)
def test_stage_entries_report_completed_outcome(
    monkeypatch: pytest.MonkeyPatch,
    case: EntryCase,
) -> None:
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.READY,
        preflight_readiness=PreflightReadiness.EXECUTABLE,
        decision=RecoveryDisposition.REBUILD,
    )

    assert result["structuredContent"]["outcome"] == "completed"


def test_rd_execute_reports_blocked_outcome_when_verification_reasons_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = next(entry for entry in ENTRY_CASES if entry.func_name == "rd_execute")
    result = _invoke(
        monkeypatch,
        case,
        stage_status=StageStatus.READY,
        preflight_readiness=PreflightReadiness.EXECUTABLE,
        decision=RecoveryDisposition.REBUILD,
        blocking_reasons=["Tests failed."],
    )

    assert result["structuredContent"]["outcome"] == "blocked"
