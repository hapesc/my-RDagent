from __future__ import annotations

import importlib

from v3.contracts.preflight import (
    PreflightBlockerCategory,
    PreflightBlockersByCategory,
    PreflightReadiness,
    PreflightResult,
)
from v3.entry.rd_agent import route_user_intent


def _paused_state(*, stage_key: str, branch_id: str = "branch-001") -> dict[str, object]:
    return {
        "run": {
            "run_id": "run-001",
            "title": "Pipeline hardening",
            "status": "awaiting_operator",
        },
        "branch": {
            "branch_id": branch_id,
            "label": "primary",
            "status": "paused",
            "current_stage_key": stage_key,
        },
    }


def _preflight_result(*, readiness: PreflightReadiness, stage_key: str = "build") -> PreflightResult:
    if readiness is PreflightReadiness.EXECUTABLE:
        return PreflightResult(
            run_id="run-001",
            branch_id="branch-001",
            stage_key=stage_key,
            recommended_next_skill="rd-code" if stage_key == "build" else "rd-execute",
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
        recommended_next_skill="rd-code" if stage_key == "build" else "rd-execute",
        readiness=readiness,
        primary_blocker_category=PreflightBlockerCategory.DEPENDENCY,
        primary_blocker_reason="Required dependency pytest is missing.",
        repair_action="Run `uv sync --extra test` before continuing with rd-code.",
        blockers_by_category=PreflightBlockersByCategory(),
    )


def _operator_guidance_module():
    return importlib.import_module("v3.orchestration.operator_guidance")


def test_paused_build_route_uses_human_first_state_summary_and_preserves_ids() -> None:
    result = route_user_intent(
        "what should i do next?",
        persisted_state=_paused_state(stage_key="build"),
        preflight_result_provider=lambda _context: _preflight_result(readiness=PreflightReadiness.EXECUTABLE),
    )

    assert "implementation stage (`build`)" in result["current_state"]
    assert "run-001" in result["current_state"]
    assert "branch-001" in result["current_state"]


def test_blocked_route_prioritizes_repair_before_continue_target() -> None:
    result = route_user_intent(
        "what should i do next?",
        persisted_state=_paused_state(stage_key="build"),
        preflight_result_provider=lambda _context: _preflight_result(readiness=PreflightReadiness.BLOCKED),
    )

    assert result["recommended_next_skill"] == "rd-code"
    assert "uv sync --extra test" in result["exact_next_action"]
    assert "continue" in result["exact_next_action"]
    assert result["exact_next_action"].index("uv sync --extra test") < result["exact_next_action"].index("continue")


def test_new_run_route_includes_minimum_start_skeleton() -> None:
    result = route_user_intent(
        "help me start a new run",
        persisted_state=None,
    )

    detail = result["next_step_detail"]
    assert "title" in detail
    assert "task_summary" in detail
    assert "scenario_label" in detail
    assert "stage_inputs.framing.summary" in detail
    assert "stage_inputs.framing.artifact_ids" in detail


def test_executable_paused_route_uses_detail_hint_without_auto_skeleton() -> None:
    result = route_user_intent(
        "continue the current build work",
        persisted_state=_paused_state(stage_key="build"),
        preflight_result_provider=lambda _context: _preflight_result(readiness=PreflightReadiness.EXECUTABLE),
    )

    assert result["detail_hint"]
    assert result.get("next_step_detail") in (None, "")


def test_stage_to_next_skill_mapping_comes_from_one_shared_source() -> None:
    module = _operator_guidance_module()

    assert module.STAGE_TO_NEXT_SKILL["framing"] == "rd-propose"
    assert module.STAGE_TO_NEXT_SKILL["build"] == "rd-code"
    assert module.STAGE_TO_NEXT_SKILL["verify"] == "rd-execute"
    assert module.STAGE_TO_NEXT_SKILL["synthesize"] == "rd-evaluate"


def test_guidance_text_renderer_emits_current_state_reason_next_action_shape() -> None:
    module = _operator_guidance_module()

    text = module.render_operator_guidance_text(
        {
            "current_state": "Current state: implementation stage (`build`) for run-001 / branch-001.",
            "routing_reason": "Reason: paused run continuation takes priority.",
            "exact_next_action": "Next action: continue run-001 / branch-001 with rd-code.",
        }
    )

    assert "Current state:" in text
    assert "Reason:" in text
    assert "Next action:" in text
