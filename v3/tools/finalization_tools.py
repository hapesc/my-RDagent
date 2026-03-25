"""CLI-oriented finalization inspection and mutation tools."""

from __future__ import annotations

from typing import Any

from v3.contracts.tool_io import (
    FinalizeEarlyRequest,
    FinalizeEarlyResult,
    ShouldFinalizeRequest,
    ShouldFinalizeResult,
)
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.ports.state_store import StateStorePort


def rd_should_finalize(
    request: ShouldFinalizeRequest,
    *,
    multi_branch_service: MultiBranchService,
    state_store: StateStorePort,
) -> dict[str, Any]:
    """Query whether a run is ready for holdout finalization."""
    run = state_store.load_run_snapshot(request.run_id)
    if run is None:
        raise KeyError(f"run not found: {request.run_id}")
    should_finalize = multi_branch_service.should_finalize(request.run_id)
    result = ShouldFinalizeResult(
        should_finalize=should_finalize,
        current_round=run.current_round,
        max_rounds=run.max_rounds,
        holdout_available=should_finalize,
    )
    return {
        "structuredContent": result.model_dump(mode="json"),
        "content": [
            {
                "type": "text",
                "text": f"should_finalize={should_finalize} (round {run.current_round}/{run.max_rounds})",
            }
        ],
    }



def rd_finalize_early(
    request: FinalizeEarlyRequest,
    *,
    multi_branch_service: MultiBranchService,
) -> dict[str, Any]:
    """Trigger early holdout finalization for a run."""
    submission = multi_branch_service.finalize_early(run_id=request.run_id)
    result = FinalizeEarlyResult(
        finalized=True,
        run_id=request.run_id,
        exploration_mode="finalized",
    )
    return {
        "structuredContent": {
            **result.model_dump(mode="json"),
            "submission": submission.model_dump(mode="json"),
        },
        "content": [
            {
                "type": "text",
                "text": f"Run {request.run_id} finalized early. Winner: {submission.winner_node_id}",
            }
        ],
    }


__all__ = ["rd_finalize_early", "rd_should_finalize"]
