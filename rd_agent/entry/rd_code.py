"""V3 build-stage skill entrypoint."""

from __future__ import annotations

from typing import Any

from rd_agent.contracts.preflight import PreflightReadiness
from rd_agent.contracts.recovery import RecoveryAssessment, RecoveryDisposition
from rd_agent.contracts.stage import StageKey, StageSnapshot
from rd_agent.contracts.tool_io import (
    ArtifactListRequest,
    BranchGetRequest,
    RecoveryAssessRequest,
    RunGetRequest,
    StageCompleteRequest,
    StageGetRequest,
    StageStartRequest,
)
from rd_agent.orchestration.operator_guidance import (
    _minimum_continuation_skeleton,
    build_stage_guidance_response,
)
from rd_agent.orchestration.preflight_service import PreflightService
from rd_agent.orchestration.recovery_service import RecoveryService
from rd_agent.orchestration.resume_planner import plan_resume_decision
from rd_agent.orchestration.run_board_service import RunBoardService
from rd_agent.orchestration.stage_transition_service import StageTransitionService
from rd_agent.ports.state_store import StateStorePort
from rd_agent.tools.artifact_tools import rd_artifact_list
from rd_agent.tools.branch_tools import rd_branch_get
from rd_agent.tools.recovery_tools import rd_recovery_assess
from rd_agent.tools.run_tools import rd_run_get
from rd_agent.tools.stage_tools import rd_stage_get
from rd_agent.tools.stage_write_tools import rd_stage_complete, rd_stage_replay

OWNED_STAGE_KEY = StageKey.BUILD
NEXT_STAGE_KEY = StageKey.VERIFY


def _tool_response(structured_content: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": text}],
    }


def rd_code(
    *,
    run_id: str,
    branch_id: str,
    summary: str,
    artifact_ids: list[str],
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
        recommended_next_skill="rd-code",
        require_branch_current_stage=False,
    )
    if preflight.readiness is PreflightReadiness.BLOCKED:
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="is blocked before execution",
            routing_reason=(
                f"Reason: canonical preflight found a {preflight.primary_blocker_category}"
                " blocker for the current build continuation."
            ),
            exact_next_action=(
                f"Next action: {preflight.repair_action} After repair, continue {run_id} / {branch_id} with rd-code."
            ),
            recommended_next_skill="rd-code",
            current_action_status="blocked",
            current_blocker_category=preflight.primary_blocker_category.value
            if preflight.primary_blocker_category
            else None,
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
        assessment=None
        if recovery_response is None
        else RecoveryAssessment.model_validate(recovery_response["structuredContent"]["assessment"]),
    )

    if decision.recovery_assessment is RecoveryDisposition.REUSE:
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="already has reusable published evidence",
            routing_reason="Reason: build evidence is reusable, so a fresh publish is unnecessary.",
            exact_next_action=f"Next action: continue {run_id} / {branch_id} with rd-execute.",
            recommended_next_skill="rd-execute",
            next_step_detail=next_step_detail,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "reused",
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
            state_descriptor="needs manual review before it can continue",
            routing_reason=(
                "Reason: build state or recovery evidence still needs review"
                " before the verify handoff is trustworthy."
            ),
            exact_next_action=f"Next action: review build blockers, then continue {run_id} / {branch_id} with rd-code.",
            recommended_next_skill="rd-code",
            next_step_detail=next_step_detail,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "review",
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
        guidance = build_stage_guidance_response(
            run_id=run_id,
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY.value,
            state_descriptor="needs replay before the verify handoff",
            routing_reason="Reason: build evidence must be replayed so the verify handoff is based on fresh output.",
            exact_next_action=f"Next action: replay build, then continue {run_id} / {branch_id} with rd-execute.",
            recommended_next_skill="rd-execute",
            next_step_detail=next_step_detail,
        )
        published = rd_stage_replay(
            StageStartRequest(
                branch_id=branch_id,
                stage_key=OWNED_STAGE_KEY,
                stage_iteration=decision.resume_stage_iteration,
                summary=summary,
                artifact_ids=decision.replay_artifact_ids or artifact_ids,
                next_stage_key=NEXT_STAGE_KEY,
            ),
            service=transition_service,
        )
        return _tool_response(
            {
                "owned_stage": OWNED_STAGE_KEY.value,
                "outcome": "replay",
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

    guidance = build_stage_guidance_response(
        run_id=run_id,
        branch_id=branch_id,
        stage_key=OWNED_STAGE_KEY.value,
        state_descriptor="completed successfully",
        routing_reason="Reason: build completed and prepared the verify handoff.",
        exact_next_action=f"Next action: continue {run_id} / {branch_id} with rd-execute.",
        recommended_next_skill="rd-execute",
        next_step_detail=next_step_detail,
    )
    published = rd_stage_complete(
        StageCompleteRequest(
            branch_id=branch_id,
            stage_key=OWNED_STAGE_KEY,
            stage_iteration=decision.resume_stage_iteration,
            summary=summary,
            artifact_ids=artifact_ids,
            next_stage_key=NEXT_STAGE_KEY,
        ),
        service=transition_service,
    )
    return _tool_response(
        {
            "owned_stage": OWNED_STAGE_KEY.value,
            "outcome": "completed",
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


__all__ = ["OWNED_STAGE_KEY", "rd_code"]
