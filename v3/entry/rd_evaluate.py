"""V3 synthesize-stage skill entrypoint."""

from __future__ import annotations

from typing import Any, Literal

from v3.contracts.stage import StageKey
from v3.contracts.preflight import PreflightReadiness
from v3.contracts.tool_io import (
    ArtifactListRequest,
    BranchGetRequest,
    RecoveryAssessRequest,
    RunGetRequest,
    StageCompleteRequest,
    StageGetRequest,
    StageStartRequest,
)
from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from v3.contracts.stage import StageKey, StageSnapshot
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.preflight_service import PreflightService
from v3.orchestration.operator_guidance import (
    _minimum_continuation_skeleton,
    build_stage_guidance_response,
)
from v3.orchestration.resume_planner import plan_resume_decision
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.state_store import StateStorePort
from v3.tools.artifact_tools import rd_artifact_list
from v3.tools.branch_tools import rd_branch_get
from v3.tools.recovery_tools import rd_recovery_assess
from v3.tools.run_tools import rd_run_get
from v3.tools.stage_tools import rd_stage_get
from v3.tools.stage_write_tools import rd_stage_complete, rd_stage_replay

OWNED_STAGE_KEY = StageKey.SYNTHESIZE


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_evaluate(
    *,
    run_id: str,
    branch_id: str,
    summary: str,
    artifact_ids: list[str],
    recommendation: Literal["continue", "stop"],
    state_store: StateStorePort,
    run_service: RunBoardService,
    recovery_service: RecoveryService,
    transition_service: StageTransitionService,
    preflight_service: PreflightService | None = None,
) -> dict[str, Any]:
    run_response = rd_run_get(RunGetRequest(run_id=run_id), service=run_service)
    branch_response = rd_branch_get(BranchGetRequest(branch_id=branch_id), state_store=state_store)
    if branch_response["structuredContent"]["branch"]["run_id"] != run_id:
        raise ValueError(f"branch {branch_id} does not belong to run {run_id}")

    stage_response = rd_stage_get(
        StageGetRequest(branch_id=branch_id, stage_key=OWNED_STAGE_KEY),
        state_store=state_store,
    )
    artifact_response = rd_artifact_list(
        ArtifactListRequest(run_id=run_id, branch_id=branch_id, stage_key=OWNED_STAGE_KEY),
        state_store=state_store,
    )
    try:
        recovery_response = rd_recovery_assess(
            RecoveryAssessRequest(run_id=run_id, branch_id=branch_id, stage_key=OWNED_STAGE_KEY),
            service=recovery_service,
        )
    except KeyError:
        recovery_response = None

    stage_snapshot = stage_response["structuredContent"]["stage"]
    next_step_detail = _minimum_continuation_skeleton(run_id=run_id, branch_id=branch_id)
    preflight = (preflight_service or PreflightService(state_store)).assess(
        run_id=run_id,
        branch_id=branch_id,
        stage_key=OWNED_STAGE_KEY,
        recommended_next_skill="rd-evaluate",
        require_branch_current_stage=False,
    )
    if preflight.readiness is PreflightReadiness.BLOCKED:
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="is blocked before execution",
            routing_reason=(
                f"Reason: canonical preflight found a {preflight.primary_blocker_category} blocker for the current synthesize continuation."
            ),
            exact_next_action=(
                f"Next action: {preflight.repair_action} After repair, continue {run_id} / {branch_id} with rd-evaluate."
            ),
            recommended_next_skill="rd-evaluate",
            current_action_status="blocked",
            current_blocker_category=preflight.primary_blocker_category.value if preflight.primary_blocker_category else None,
            current_blocker_reason=preflight.primary_blocker_reason,
            repair_action=preflight.repair_action,
            next_step_detail=next_step_detail,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "preflight_blocked",
                "operator_guidance": guidance["payload"],
                "preflight": preflight.model_dump(mode="json"),
                "recommendation": recommendation,
                "run": run_response["structuredContent"]["run"],
                "branch_before": branch_response["structuredContent"]["branch"],
                "stage_before": stage_snapshot,
                "artifacts_before": artifact_response["structuredContent"]["items"],
                "recovery": None if recovery_response is None else recovery_response["structuredContent"]["assessment"],
                "branch_after": branch_response["structuredContent"]["branch"],
                "stage_after": stage_snapshot,
            },
            guidance["text"],
        )

    decision = plan_resume_decision(
        stage=StageSnapshot.model_validate(stage_snapshot),
        assessment=None if recovery_response is None else RecoveryAssessment.model_validate(recovery_response["structuredContent"]["assessment"]),
    )

    if decision.recovery_assessment is RecoveryDisposition.REUSE:
        next_skill = "rd-propose" if recommendation == "continue" else "stop"
        next_action = (
            f"Next action: continue {run_id} / {branch_id} with rd-propose."
            if recommendation == "continue"
            else "Next action: stop the loop; no next stage skill should be run."
        )
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="already has reusable published evidence",
            routing_reason="Reason: synthesize evidence is reusable, so a fresh publish is unnecessary.",
            exact_next_action=next_action,
            recommended_next_skill=next_skill,
            next_step_detail=next_step_detail,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "reused",
                "recommendation": recommendation,
                "operator_guidance": guidance["payload"],
                "decision": decision.model_dump(mode="json"),
                "run": run_response["structuredContent"]["run"],
                "branch_before": branch_response["structuredContent"]["branch"],
                "stage_before": stage_snapshot,
                "artifacts_before": artifact_response["structuredContent"]["items"],
                "recovery": None if recovery_response is None else recovery_response["structuredContent"]["assessment"],
                "branch_after": branch_response["structuredContent"]["branch"],
                "stage_after": stage_snapshot,
            },
            guidance["text"],
        )

    if decision.recovery_assessment is RecoveryDisposition.REVIEW:
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="needs manual review before the branch decision is trusted",
            routing_reason="Reason: synthesize state or recovery evidence still needs review before continue-or-stop can be finalized.",
            exact_next_action=f"Next action: review synthesize blockers, then continue {run_id} / {branch_id} with rd-evaluate.",
            recommended_next_skill="rd-evaluate",
            next_step_detail=next_step_detail,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "review",
                "recommendation": recommendation,
                "operator_guidance": guidance["payload"],
                "decision": decision.model_dump(mode="json"),
                "run": run_response["structuredContent"]["run"],
                "branch_before": branch_response["structuredContent"]["branch"],
                "stage_before": stage_snapshot,
                "artifacts_before": artifact_response["structuredContent"]["items"],
                "recovery": None if recovery_response is None else recovery_response["structuredContent"]["assessment"],
                "branch_after": branch_response["structuredContent"]["branch"],
                "stage_after": stage_snapshot,
            },
            guidance["text"],
        )

    if decision.recovery_assessment is RecoveryDisposition.REPLAY:
        next_skill = "rd-propose" if recommendation == "continue" else "stop"
        next_action = (
            f"Next action: replay synthesize, then continue {run_id} / {branch_id} with rd-propose."
            if recommendation == "continue"
            else "Next action: replay synthesize, then stop the loop with no next stage skill."
        )
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="needs replay before the branch decision is final",
            routing_reason="Reason: synthesize evidence must be replayed so the continue-or-stop recommendation is based on fresh output.",
            exact_next_action=next_action,
            recommended_next_skill=next_skill,
            next_step_detail=next_step_detail,
        )
        published = rd_stage_replay(
            StageStartRequest(
                branch_id=branch_id,
                stage_key=OWNED_STAGE_KEY,
                stage_iteration=decision.resume_stage_iteration,
                summary=summary,
                artifact_ids=decision.replay_artifact_ids or artifact_ids,
                next_stage_key=StageKey.FRAMING if recommendation == "continue" else None,
            ),
            service=transition_service,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "replay",
                "recommendation": recommendation,
                "operator_guidance": guidance["payload"],
                "decision": decision.model_dump(mode="json"),
                "run": run_response["structuredContent"]["run"],
                "branch_before": branch_response["structuredContent"]["branch"],
                "stage_before": stage_snapshot,
                "artifacts_before": artifact_response["structuredContent"]["items"],
                "recovery": None if recovery_response is None else recovery_response["structuredContent"]["assessment"],
                "branch_after": published["structuredContent"]["branch"],
                "stage_after": published["structuredContent"]["stage"],
            },
            guidance["text"],
        )

    next_skill = "rd-propose" if recommendation == "continue" else "stop"
    next_action = (
        f"Next action: continue {run_id} / {branch_id} with rd-propose."
        if recommendation == "continue"
        else "Next action: stop the loop; no next stage skill should be run."
    )
    guidance = build_stage_guidance_response(
        run_id=run_id,
        branch_id=branch_id,
        stage_key=OWNED_STAGE_KEY.value,
        state_descriptor="completed successfully",
        routing_reason=(
            "Reason: synthesize completed and the branch recommendation is finalized."
        ),
        exact_next_action=next_action,
        recommended_next_skill=next_skill,
        next_step_detail=next_step_detail,
    )
    next_stage_key = StageKey.FRAMING if recommendation == "continue" else None
    published = rd_stage_complete(
        StageCompleteRequest(
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY,
            stage_iteration=decision.resume_stage_iteration,
            summary=summary,
            artifact_ids=artifact_ids,
            next_stage_key=next_stage_key,
        ),
        service=transition_service,
    )
    return _tool_response(
        {
            "owned_stage": OWNED_STAGE_KEY.value,
            "outcome": "completed",
            "recommendation": recommendation,
            "operator_guidance": guidance["payload"],
            "decision": decision.model_dump(mode="json"),
            "run": run_response["structuredContent"]["run"],
            "branch_before": branch_response["structuredContent"]["branch"],
            "stage_before": stage_snapshot,
            "artifacts_before": artifact_response["structuredContent"]["items"],
            "recovery": None if recovery_response is None else recovery_response["structuredContent"]["assessment"],
            "branch_after": published["structuredContent"]["branch"],
            "stage_after": published["structuredContent"]["stage"],
        },
        guidance["text"],
    )


__all__ = ["OWNED_STAGE_KEY", "rd_evaluate"]
