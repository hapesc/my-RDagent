"""Shared operator-guidance formatting for Phase 24 public surfaces."""

from __future__ import annotations

from typing import Any

from v3.contracts.operator_guidance import OperatorGuidance

STAGE_TO_NEXT_SKILL = {
    "framing": "rd-propose",
    "build": "rd-code",
    "verify": "rd-execute",
    "synthesize": "rd-evaluate",
    "evaluate": "rd-evaluate",
}

_STAGE_LABELS = {
    "framing": "framing stage (`framing`)",
    "build": "implementation stage (`build`)",
    "verify": "verification stage (`verify`)",
    "synthesize": "synthesis stage (`synthesize`)",
    "evaluate": "synthesis stage (`synthesize`)",
}

_DETAIL_HINT = "If you want, I can expand the next step into the minimum command or skeleton."


def _normalize_stage_key(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _stage_label(stage_key: str | None) -> str:
    normalized = _normalize_stage_key(stage_key)
    if normalized is None:
        return "current stage"
    return _STAGE_LABELS.get(normalized, f"current stage (`{normalized}`)")


def _minimum_start_skeleton(user_intent: str) -> str:
    task_summary = user_intent or "Describe the task you want the standalone loop to drive."
    return (
        'title="Phase 24 task" '
        f'task_summary="{task_summary}" '
        'scenario_label="research" '
        'stage_inputs.framing.summary="Summarize the first framing step." '
        'stage_inputs.framing.artifact_ids=["artifact-plan-001"]'
    )


def _minimum_continuation_skeleton(*, run_id: str, branch_id: str) -> str:
    return (
        f'run_id="{run_id}" '
        f'branch_id="{branch_id}" '
        'summary="Summarize the current step." '
        'artifact_ids=["artifact-001"]'
    )


def build_stage_operator_guidance(
    *,
    run_id: str,
    branch_id: str,
    stage_key: str,
    recommended_next_skill: str,
    state_descriptor: str,
    routing_reason: str,
    exact_next_action: str,
    current_action_status: str | None = None,
    current_blocker_category: str | None = None,
    current_blocker_reason: str | None = None,
    repair_action: str | None = None,
    next_step_detail: str | None = None,
    detail_hint: str | None = None,
) -> OperatorGuidance:
    return OperatorGuidance(
        recommended_next_skill=recommended_next_skill,
        current_state=(
            f"Current state: {_stage_label(stage_key)} for run {run_id} on branch {branch_id} {state_descriptor}."
        ),
        routing_reason=routing_reason,
        exact_next_action=exact_next_action,
        current_action_status=current_action_status,
        current_blocker_category=current_blocker_category,
        current_blocker_reason=current_blocker_reason,
        repair_action=repair_action,
        next_step_detail=next_step_detail,
        detail_hint=detail_hint,
    )


def render_operator_guidance_text(guidance: OperatorGuidance | dict[str, Any]) -> str:
    if isinstance(guidance, OperatorGuidance):
        data = guidance.model_dump(mode="json")
    else:
        data = dict(guidance)

    lines = [
        str(data["current_state"]),
        str(data["routing_reason"]),
        str(data["exact_next_action"]),
    ]
    if data.get("detail_hint"):
        lines.append(str(data["detail_hint"]))
    if data.get("next_step_detail"):
        lines.append(f"Detail: {data['next_step_detail']}")
    return "\n".join(lines)


def project_operator_guidance(guidance: OperatorGuidance) -> dict[str, Any]:
    return guidance.model_dump(mode="json")


def build_start_new_run_guidance(*, user_intent: str) -> OperatorGuidance:
    intent_text = user_intent.strip()
    return OperatorGuidance(
        recommended_next_skill="rd-agent",
        current_state=(
            "Current state: no paused run is active in the current working context, "
            "so a new run can start (`start_new_run`)."
        ),
        routing_reason=(
            "Reason: plain-language intent did not name a skill, and no paused run "
            "dominates the current state."
        ),
        exact_next_action=(
            "Next action: stay on rd-agent and start a new run from the request"
            + (f' "{intent_text}".' if intent_text else ".")
        ),
        next_step_detail=_minimum_start_skeleton(intent_text),
    )


def build_paused_run_guidance(
    *,
    run_id: str,
    branch_id: str,
    stage_key: str,
    recommended_next_skill: str,
    selection_reason: str,
    current_action_status: str,
    current_blocker_category: str | None,
    current_blocker_reason: str | None,
    repair_action: str,
    exact_next_action: str,
) -> OperatorGuidance:
    guidance = build_stage_operator_guidance(
        run_id=run_id,
        branch_id=branch_id,
        stage_key=stage_key,
        recommended_next_skill=recommended_next_skill,
        state_descriptor="is paused and awaiting operator input",
        routing_reason=(
            "Reason: paused run continuation takes priority over a new run, and "
            f"{selection_reason}"
        ),
        exact_next_action=exact_next_action,
        current_action_status=current_action_status,
        current_blocker_category=current_blocker_category,
        current_blocker_reason=current_blocker_reason,
        repair_action=repair_action,
    )
    if current_action_status == "executable":
        return guidance.model_copy(update={"detail_hint": _DETAIL_HINT})
    return guidance.model_copy(
        update={
            "next_step_detail": _minimum_continuation_skeleton(run_id=run_id, branch_id=branch_id),
        }
    )


__all__ = [
    "STAGE_TO_NEXT_SKILL",
    "build_stage_operator_guidance",
    "build_paused_run_guidance",
    "build_start_new_run_guidance",
    "project_operator_guidance",
    "render_operator_guidance_text",
]
