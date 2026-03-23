"""Explicit Phase 14 execution policy for bounded single-branch orchestration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from v3.contracts.run import ExecutionMode, RunStatus, RunStopReason
from v3.contracts.stage import StageKey, StageStatus


class AgentExecutionPolicy(BaseModel):
    """Operator-facing control over bounded V3 execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: ExecutionMode = ExecutionMode.GATED
    max_stage_iterations: int = Field(default=1, ge=1)


class PolicyBoundaryDecision(BaseModel):
    """Public decision produced at a stage boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    should_stop: bool
    run_status: RunStatus
    stop_reason: RunStopReason | None = None
    current_stage_iteration: int = Field(ge=1)
    completed_stage_iterations: int = Field(ge=0)
    next_stage_iteration: int = Field(ge=1)
    message: str = Field(min_length=1)


def evaluate_stage_boundary(
    *,
    policy: AgentExecutionPolicy,
    current_iteration: int,
    stage_key: StageKey,
    stage_status: StageStatus,
    next_stage_key: StageKey | None,
    recommendation: Literal["continue", "stop"] | None = None,
) -> PolicyBoundaryDecision:
    """Determine whether `/rd-agent` should advance, pause, or stop in V3 terms."""

    if stage_status is StageStatus.BLOCKED:
        return PolicyBoundaryDecision(
            should_stop=True,
            run_status=RunStatus.NEEDS_ATTENTION,
            stop_reason=RunStopReason.STAGE_BLOCKED,
            current_stage_iteration=current_iteration,
            completed_stage_iterations=max(0, current_iteration - 1),
            next_stage_iteration=current_iteration,
            message=(
                f"Stopped at {stage_key.value} iteration {current_iteration} because the stage is blocked "
                "and needs manual review."
            ),
        )

    if policy.mode is ExecutionMode.GATED:
        target = next_stage_key.value if next_stage_key is not None else "completion"
        return PolicyBoundaryDecision(
            should_stop=True,
            run_status=RunStatus.PAUSED,
            stop_reason=RunStopReason.AWAITING_OPERATOR,
            current_stage_iteration=current_iteration,
            completed_stage_iterations=max(0, current_iteration - 1),
            next_stage_iteration=current_iteration,
            message=(
                f"Paused after {stage_key.value} iteration {current_iteration} for operator review before {target}."
            ),
        )

    if stage_key is not StageKey.SYNTHESIZE:
        if next_stage_key is None:
            raise ValueError(f"next stage key is required after {stage_key.value}")
        return PolicyBoundaryDecision(
            should_stop=False,
            run_status=RunStatus.ACTIVE,
            current_stage_iteration=current_iteration,
            completed_stage_iterations=max(0, current_iteration - 1),
            next_stage_iteration=current_iteration,
            message=f"Advanced to {next_stage_key.value}.",
        )

    if recommendation == "stop":
        return PolicyBoundaryDecision(
            should_stop=True,
            run_status=RunStatus.COMPLETED,
            stop_reason=RunStopReason.RUN_COMPLETED,
            current_stage_iteration=current_iteration,
            completed_stage_iterations=current_iteration,
            next_stage_iteration=current_iteration,
            message="Stopped because synthesize recommended stop.",
        )

    next_iteration = current_iteration + 1
    if current_iteration >= policy.max_stage_iterations:
        return PolicyBoundaryDecision(
            should_stop=True,
            run_status=RunStatus.PAUSED,
            stop_reason=RunStopReason.ITERATION_CEILING_REACHED,
            current_stage_iteration=next_iteration,
            completed_stage_iterations=current_iteration,
            next_stage_iteration=next_iteration,
            message=(
                f"Stopped because the hard iteration ceiling of {policy.max_stage_iterations} was reached "
                f"after synthesize iteration {current_iteration}."
            ),
        )

    return PolicyBoundaryDecision(
        should_stop=False,
        run_status=RunStatus.ACTIVE,
        current_stage_iteration=next_iteration,
        completed_stage_iterations=current_iteration,
        next_stage_iteration=next_iteration,
        message=f"Advanced to framing iteration {next_iteration}.",
    )


__all__ = ["AgentExecutionPolicy", "PolicyBoundaryDecision", "evaluate_stage_boundary"]
