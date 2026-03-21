"""Single-branch V3 skill chaining for the Phase 14 `/rd-agent` surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from v3.contracts.run import RunBoardSnapshot, RunStatus, RunStopReason
from v3.contracts.stage import StageKey, StageSnapshot, StageStatus
from v3.entry.rd_code import rd_code
from v3.entry.rd_evaluate import rd_evaluate
from v3.entry.rd_execute import rd_execute
from v3.entry.rd_propose import rd_propose
from v3.orchestration.execution_policy import AgentExecutionPolicy, evaluate_stage_boundary
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.state_store import StateStorePort
from v3.contracts.tool_io import StageTransitionRequest
from v3.tools.stage_write_tools import rd_stage_transition


StagePayload = dict[str, Any]


@dataclass(frozen=True)
class SkillLoopResult:
    run: RunBoardSnapshot
    branch_id: str
    history: list[dict[str, Any]]
    stop_reason: RunStopReason
    message: str


class SkillLoopService:
    """Chains the public stage skills for one V3 branch."""

    _ORDER: tuple[StageKey, ...] = (
        StageKey.FRAMING,
        StageKey.BUILD,
        StageKey.VERIFY,
        StageKey.SYNTHESIZE,
    )

    def __init__(
        self,
        *,
        state_store: StateStorePort,
        run_service: RunBoardService,
        recovery_service: RecoveryService,
        transition_service: StageTransitionService,
    ) -> None:
        self._state_store = state_store
        self._run_service = run_service
        self._recovery_service = recovery_service
        self._transition_service = transition_service

    def run_single_branch(
        self,
        *,
        run_id: str,
        branch_id: str,
        policy: AgentExecutionPolicy,
        stage_inputs: dict[StageKey, StagePayload],
    ) -> SkillLoopResult:
        history: list[dict[str, Any]] = []
        messages: list[str] = []
        current_iteration = 1

        while True:
            for stage_key in self._ORDER:
                payload = stage_inputs.get(stage_key)
                if payload is None:
                    raise KeyError(f"missing stage input for {stage_key.value}")

                self._ensure_stage_exists(
                    branch_id=branch_id,
                    stage_key=stage_key,
                    stage_iteration=current_iteration,
                )
                response = self._run_stage(
                    stage_key=stage_key,
                    run_id=run_id,
                    branch_id=branch_id,
                    payload=payload,
                )
                text = response["content"][0]["text"]
                stage_after = StageSnapshot.model_validate(response["structuredContent"]["stage_after"])
                recommendation = response["structuredContent"].get("recommendation")
                decision = evaluate_stage_boundary(
                    policy=policy,
                    current_iteration=current_iteration,
                    stage_key=stage_key,
                    stage_status=stage_after.status,
                    next_stage_key=stage_after.next_stage_key,
                    recommendation=recommendation,
                )
                history.append(
                    {
                        "stage_key": stage_key.value,
                        "disposition": response["structuredContent"]["decision"]["disposition"],
                        "message": text,
                    }
                )
                messages.append(f"{text} {decision.message}")
                if decision.should_stop:
                    if (
                        decision.stop_reason is RunStopReason.AWAITING_OPERATOR
                        and stage_after.next_stage_key is not None
                    ):
                        self._ensure_stage_exists(
                            branch_id=branch_id,
                            stage_key=stage_after.next_stage_key,
                            stage_iteration=decision.next_stage_iteration,
                        )
                    run = self._persist_run_stop(
                        run_id=run_id,
                        status=decision.run_status,
                        stop_reason=decision.stop_reason,
                        completed_stage_iterations=decision.completed_stage_iterations,
                        current_stage_iteration=decision.current_stage_iteration,
                        summary=decision.message,
                    )
                    return SkillLoopResult(
                        run=run,
                        branch_id=branch_id,
                        history=history,
                        stop_reason=decision.stop_reason or RunStopReason.AWAITING_OPERATOR,
                        message=" ".join(messages),
                    )
                if stage_after.next_stage_key is not None:
                    self._ensure_stage_exists(
                        branch_id=branch_id,
                        stage_key=stage_after.next_stage_key,
                        stage_iteration=decision.next_stage_iteration,
                    )
                if stage_key is StageKey.SYNTHESIZE:
                    current_iteration = decision.next_stage_iteration
                    break

        raise RuntimeError("single-branch loop exhausted without synthesize outcome")

    def _ensure_stage_exists(
        self,
        *,
        branch_id: str,
        stage_key: StageKey,
        stage_iteration: int,
    ) -> None:
        if self._state_store.load_stage_snapshot(branch_id, stage_key, stage_iteration=stage_iteration) is not None:
            return

        next_stage_key = {
            StageKey.FRAMING: StageKey.BUILD,
            StageKey.BUILD: StageKey.VERIFY,
            StageKey.VERIFY: StageKey.SYNTHESIZE,
            StageKey.SYNTHESIZE: None,
        }[stage_key]
        rd_stage_transition(
            StageTransitionRequest(
                branch_id=branch_id,
                stage_key=stage_key,
                stage_iteration=stage_iteration,
                status=StageStatus.READY,
                summary=(
                    f"{stage_key.value.capitalize()} iteration {stage_iteration} is ready for `/rd-agent`."
                ),
                artifact_ids=[],
                next_stage_key=next_stage_key,
            ),
            service=self._transition_service,
        )

    def _run_stage(
        self,
        *,
        stage_key: StageKey,
        run_id: str,
        branch_id: str,
        payload: StagePayload,
    ) -> dict[str, Any]:
        summary = str(payload["summary"])
        artifact_ids = list(payload.get("artifact_ids", []))

        if stage_key is StageKey.FRAMING:
            return rd_propose(
                run_id=run_id,
                branch_id=branch_id,
                summary=summary,
                artifact_ids=artifact_ids,
                state_store=self._state_store,
                run_service=self._run_service,
                recovery_service=self._recovery_service,
                transition_service=self._transition_service,
            )
        if stage_key is StageKey.BUILD:
            return rd_code(
                run_id=run_id,
                branch_id=branch_id,
                summary=summary,
                artifact_ids=artifact_ids,
                state_store=self._state_store,
                run_service=self._run_service,
                recovery_service=self._recovery_service,
                transition_service=self._transition_service,
            )
        if stage_key is StageKey.VERIFY:
            return rd_execute(
                run_id=run_id,
                branch_id=branch_id,
                summary=summary,
                artifact_ids=artifact_ids,
                state_store=self._state_store,
                run_service=self._run_service,
                recovery_service=self._recovery_service,
                transition_service=self._transition_service,
                blocking_reasons=list(payload.get("blocking_reasons", [])),
            )
        if stage_key is StageKey.SYNTHESIZE:
            recommendation = payload.get("recommendation", "stop")
            if recommendation not in {"continue", "stop"}:
                raise ValueError(f"unsupported synthesize recommendation: {recommendation}")
            return rd_evaluate(
                run_id=run_id,
                branch_id=branch_id,
                summary=summary,
                artifact_ids=artifact_ids,
                recommendation=recommendation,
                state_store=self._state_store,
                run_service=self._run_service,
                recovery_service=self._recovery_service,
                transition_service=self._transition_service,
            )
        raise ValueError(f"unsupported stage key: {stage_key.value}")

    def _persist_run_stop(
        self,
        *,
        run_id: str,
        status: RunStatus,
        stop_reason: RunStopReason | None,
        completed_stage_iterations: int,
        current_stage_iteration: int,
        summary: str,
    ) -> RunBoardSnapshot:
        run = self._run_service.get_run(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        updated = run.model_copy(
            update={
                "status": status,
                "stop_reason": stop_reason,
                "completed_stage_iterations": completed_stage_iterations,
                "current_stage_iteration": current_stage_iteration,
                "summary": summary,
            }
        )
        self._state_store.write_run_snapshot(updated)
        return updated


__all__ = ["SkillLoopResult", "SkillLoopService", "StagePayload"]
