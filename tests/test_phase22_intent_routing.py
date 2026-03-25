from rd_agent.contracts.preflight import (
    PreflightBlockerCategory,
    PreflightBlockersByCategory,
    PreflightReadiness,
    PreflightResult,
)
from rd_agent.entry import rd_agent as rd_agent_module


def _route_user_intent(*args, **kwargs):
    return rd_agent_module.route_user_intent(*args, **kwargs)


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


def _preflight_result(*, readiness: PreflightReadiness) -> PreflightResult:
    if readiness is PreflightReadiness.EXECUTABLE:
        return PreflightResult(
            run_id="run-001",
            branch_id="branch-001",
            stage_key="build",
            recommended_next_skill="rd-code",
            readiness=readiness,
            primary_blocker_category=None,
            primary_blocker_reason=None,
            repair_action="None - canonical preflight truth passed.",
            blockers_by_category=PreflightBlockersByCategory(),
        )
    return PreflightResult(
        run_id="run-001",
        branch_id="branch-001",
        stage_key="build",
        recommended_next_skill="rd-code",
        readiness=readiness,
        primary_blocker_category=PreflightBlockerCategory.DEPENDENCY,
        primary_blocker_reason="Required dependency pytest is missing.",
        repair_action="Run `uv sync --extra test` before continuing with rd-code.",
        blockers_by_category=PreflightBlockersByCategory(),
    )


def test_plain_language_intent_does_not_require_skill_name_first() -> None:
    result = _route_user_intent(
        "help me finish this task and tell me what to do next",
        persisted_state=None,
    )

    assert result["recommended_next_skill"] == "rd-agent"
    assert result["route_kind"] == "start_new_run"
    assert "new run" in result["current_state"].lower()
    assert "plain-language" in result["routing_reason"]
    assert "rd-agent" in result["exact_next_action"]


def test_paused_run_is_preferred_over_new_run() -> None:
    result = _route_user_intent(
        "what should i do next?",
        persisted_state=_paused_state(stage_key="build"),
        preflight_result_provider=lambda _context: _preflight_result(readiness=PreflightReadiness.EXECUTABLE),
    )

    assert result["route_kind"] == "continue_paused_run"
    assert result["recommended_next_skill"] == "rd-code"
    assert result["current_action_status"] == "executable"
    assert result["current_blocker_category"] is None
    assert result["current_blocker_reason"] is None
    assert result["repair_action"] == "None - canonical preflight truth passed."
    assert result["current_run_id"] == "run-001"
    assert result["current_branch_id"] == "branch-001"
    assert result["current_stage"] == "build"
    assert "paused run" in result["routing_reason"].lower()
    assert "new run" not in result["exact_next_action"].lower()
    assert "rd-code" in result["exact_next_action"]


def test_routing_response_includes_recommended_next_skill() -> None:
    result = _route_user_intent(
        "continue the current verify work",
        persisted_state=_paused_state(stage_key="verify"),
        preflight_result_provider=lambda _context: PreflightResult(
            run_id="run-001",
            branch_id="branch-001",
            stage_key="verify",
            recommended_next_skill="rd-execute",
            readiness=PreflightReadiness.EXECUTABLE,
            primary_blocker_category=None,
            primary_blocker_reason=None,
            repair_action="None - canonical preflight truth passed.",
            blockers_by_category=PreflightBlockersByCategory(),
        ),
    )

    assert result["recommended_next_skill"] == "rd-execute"
    assert result["current_action_status"] == "executable"
    assert result["current_blocker_category"] is None
    assert result["current_blocker_reason"] is None
    assert result["repair_action"] == "None - canonical preflight truth passed."
    assert result["current_state"]
    assert result["routing_reason"]
    assert result["exact_next_action"]
    assert result["current_state"].startswith("Current state:")
    assert result["routing_reason"].startswith("Reason:")
    assert result["exact_next_action"].startswith("Next action:")


def test_downshift_to_tool_catalog_happens_only_when_high_level_boundary_is_insufficient() -> None:
    default_route = _route_user_intent(
        "inspect the current state and help me continue",
        persisted_state=_paused_state(stage_key="build"),
    )
    downshift_route = _route_user_intent(
        "inspect the current state and help me continue",
        persisted_state=_paused_state(stage_key="build"),
        high_level_boundary_sufficient=False,
    )

    assert default_route["recommended_next_skill"] == "rd-code"
    assert downshift_route["recommended_next_skill"] == "rd-tool-catalog"
    assert "insufficient" in downshift_route["routing_reason"].lower()
    assert "rd-tool-catalog" in downshift_route["exact_next_action"]
