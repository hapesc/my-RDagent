"""Shared operator-guidance formatting for Phase 24 public surfaces."""

from __future__ import annotations

from typing import Any

from rd_agent.contracts.exploration import FinalSubmissionSnapshot
from rd_agent.contracts.operator_guidance import OperatorGuidance

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

_REQUIRED_TEXT_FIELDS = ("current_state", "routing_reason", "exact_next_action")


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
        'title="Standalone V3 task" '
        f'task_summary="{task_summary}" '
        'scenario_label="research" '
        'stage_inputs.framing.summary="Summarize the first framing step." '
        'stage_inputs.framing.artifact_ids=["artifact-plan-001"]'
    )


def _generate_branch_hypotheses(intent: str) -> list[str]:
    summary = intent.strip()[:50]
    return [
        f"Approach A: primary method for {summary}",
        f"Approach B: alternative method for {summary}",
        f"Approach C: baseline comparison for {summary}",
    ]


def _minimum_continuation_skeleton(*, run_id: str, branch_id: str) -> str:
    return (
        f'run_id="{run_id}" branch_id="{branch_id}" summary="Summarize the current step." artifact_ids=["artifact-001"]'
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
    )


def _round_progress_text(current_round: int, max_rounds: int) -> str:
    """Format exploration round progress for operator display."""
    return f"exploring round {current_round}/{max_rounds}"



def build_exploration_progress_text(current_round: int, max_rounds: int) -> str:
    return _round_progress_text(current_round, max_rounds)



def build_finalization_guidance(
    *,
    submission: FinalSubmissionSnapshot,
    current_round: int | None = None,
    max_rounds: int | None = None,
) -> OperatorGuidance:
    ranking_lines = [
        (
            f"- rank={entry.rank} node_id={entry.node_id} branch_id={entry.branch_id} "
            f"holdout_mean={entry.holdout_mean:.4f} holdout_std={entry.holdout_std:.4f}"
        )
        for entry in submission.ranked_candidates
    ]
    ranking_detail = "\n".join(ranking_lines) if ranking_lines else "- no ranked candidates recorded"
    round_progress = (
        f"{_round_progress_text(current_round, max_rounds)}; "
        if current_round is not None and max_rounds is not None
        else ""
    )
    return OperatorGuidance(
        recommended_next_skill="rd-evaluate",
        current_state=(
            "Current state: "
            f"{round_progress}finalization complete for run {submission.run_id}; "
            f"winner {submission.winner_node_id} from branch {submission.winner_branch_id}."
        ),
        routing_reason=(
            "Reason: the run now has a holdout-backed final ranking, so the operator should review the "
            "winner and the supporting leaderboard instead of continuing open-ended exploration."
        ),
        exact_next_action=(
            "Next action: inspect the ranked final submission, confirm whether the winning node should become "
            "the accepted outcome, and continue with evaluation or reporting."
        ),
        next_step_detail=(
            f"winner_node_id={submission.winner_node_id} "
            f"holdout_mean={submission.holdout_mean:.4f} "
            f"holdout_std={submission.holdout_std:.4f}\n"
            "ranking:\n"
            f"{ranking_detail}"
        ),
    )


def render_operator_guidance_text(guidance: OperatorGuidance | dict[str, Any]) -> str:
    if isinstance(guidance, OperatorGuidance):
        data = guidance.model_dump(mode="json")
    else:
        data = dict(guidance)
        missing = [field_name for field_name in _REQUIRED_TEXT_FIELDS if field_name not in data]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"render_operator_guidance_text missing required fields: {joined}")

    lines = [
        str(data["current_state"]),
        str(data["routing_reason"]),
        str(data["exact_next_action"]),
    ]
    if data.get("next_step_detail"):
        lines.append(f"Detail: {data['next_step_detail']}")
    return "\n".join(lines)


def operator_guidance_to_dict(guidance: OperatorGuidance) -> dict[str, Any]:
    return guidance.model_dump(mode="json")


def build_stage_guidance_response(
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
) -> dict[str, Any]:
    guidance = build_stage_operator_guidance(
        run_id=run_id,
        branch_id=branch_id,
        stage_key=stage_key,
        recommended_next_skill=recommended_next_skill,
        state_descriptor=state_descriptor,
        routing_reason=routing_reason,
        exact_next_action=exact_next_action,
        current_action_status=current_action_status,
        current_blocker_category=current_blocker_category,
        current_blocker_reason=current_blocker_reason,
        repair_action=repair_action,
        next_step_detail=next_step_detail,
    )
    return {
        "payload": operator_guidance_to_dict(guidance),
        "text": render_operator_guidance_text(guidance),
    }


def build_start_new_run_guidance(*, user_intent: str) -> OperatorGuidance:
    intent_text = user_intent.strip()
    hypotheses = _generate_branch_hypotheses(intent_text)
    hypothesis_lines = "\n".join(f"  - {hypothesis}" for hypothesis in hypotheses)
    skeleton = _minimum_start_skeleton(intent_text)
    branch_skeleton = f'{skeleton} exploration_mode="exploration" branch_hypotheses={hypotheses!r}'
    return OperatorGuidance(
        recommended_next_skill="rd-agent",
        current_state=(
            "Current state: no paused run is active in the current working context, "
            "so a new run can start (`start_new_run`). "
            "Multi-branch exploration is recommended."
        ),
        routing_reason=(
            "Reason: plain-language intent suggests a research task. "
            "I suggest exploring these directions:\n"
            f"{hypothesis_lines}"
        ),
        exact_next_action=(
            "Next action: start a new run with rd-agent in exploration mode. "
            "Confirm or modify the suggested branch hypotheses, then start."
        ),
        next_step_detail=branch_skeleton,
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
        routing_reason=(f"Reason: paused run continuation takes priority over a new run, and {selection_reason}"),
        exact_next_action=exact_next_action,
        current_action_status=current_action_status,
        current_blocker_category=current_blocker_category,
        current_blocker_reason=current_blocker_reason,
        repair_action=repair_action,
    )
    return guidance.model_copy(
        update={
            "next_step_detail": _minimum_continuation_skeleton(run_id=run_id, branch_id=branch_id),
        }
    )


__all__ = [
    "STAGE_TO_NEXT_SKILL",
    "_generate_branch_hypotheses",
    "build_exploration_progress_text",
    "build_finalization_guidance",
    "build_stage_guidance_response",
    "build_stage_operator_guidance",
    "build_paused_run_guidance",
    "build_start_new_run_guidance",
    "operator_guidance_to_dict",
    "render_operator_guidance_text",
]
