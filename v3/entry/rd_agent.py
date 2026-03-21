"""Primary V3 skill entrypoint for single-branch and multi-branch runs."""

from __future__ import annotations

from typing import Any

from v3.contracts.run import ExecutionMode
from v3.contracts.tool_io import RunStartRequest
from v3.entry.tool_catalog import call_cli_tool
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.execution_policy import AgentExecutionPolicy
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.selection_service import SelectionService
from v3.orchestration.skill_loop_service import SkillLoopService, StagePayload
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.state_store import StateStorePort


def rd_agent(
    *,
    title: str,
    task_summary: str,
    scenario_label: str,
    state_store: StateStorePort,
    run_service: RunBoardService,
    recovery_service: RecoveryService,
    transition_service: StageTransitionService,
    stage_inputs: dict[Any, StagePayload],
    initial_branch_label: str | None = None,
    execution_mode: ExecutionMode = ExecutionMode.GATED,
    max_stage_iterations: int = 1,
    branch_hypotheses: list[str] | None = None,
    dispatcher=None,
) -> dict[str, Any]:
    start_response = call_cli_tool(
        "rd_run_start",
        {
            "title": title,
            "task_summary": task_summary,
            "scenario_label": scenario_label,
            "initial_branch_label": initial_branch_label,
            "execution_mode": execution_mode,
            "max_stage_iterations": max_stage_iterations,
        },
        service=run_service,
    )
    run_snapshot = run_service.get_run(start_response["structuredContent"]["run"]["run_id"])
    if run_snapshot is None:
        raise KeyError("run start did not persist a run snapshot")
    run_snapshot = run_snapshot.model_copy(
        update={
            "execution_mode": execution_mode,
            "max_stage_iterations": max_stage_iterations,
        }
    )
    state_store.write_run_snapshot(run_snapshot)
    branch_snapshot = start_response["structuredContent"]["branch"]

    if branch_hypotheses and len(branch_hypotheses) > 1:
        workspace_manager = BranchWorkspaceManager(getattr(state_store, "_root", ".state"))
        board_service = BranchBoardService(state_store)
        convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
        multi_branch_service = MultiBranchService(
            state_store=state_store,
            workspace_manager=workspace_manager,
            branch_lifecycle_service=BranchLifecycleService(
                state_store=state_store,
                workspace_manager=workspace_manager,
                run_board_service=run_service,
            ),
            branch_board_service=board_service,
            selection_service=SelectionService(state_store=state_store),
            branch_merge_service=BranchMergeService(
                state_store=state_store,
                convergence_service=convergence_service,
                board_service=board_service,
            ),
            dispatcher=dispatcher,
        )
        explore_round = multi_branch_service.run_exploration_round(
            __import__("v3.contracts.tool_io", fromlist=["ExploreRoundRequest"]).ExploreRoundRequest(
                run_id=run_snapshot.run_id,
                hypotheses=branch_hypotheses,
            )
        )
        converge_round = multi_branch_service.run_convergence_round(
            __import__("v3.contracts.tool_io", fromlist=["ConvergeRoundRequest"]).ConvergeRoundRequest(
                run_id=run_snapshot.run_id,
            )
        )
        return {
            "structuredContent": {
                "run": run_snapshot.model_dump(mode="json"),
                "board": converge_round.board.model_dump(mode="json"),
                "mode": converge_round.board.mode.value,
                "recommended_next_step": converge_round.recommended_next_step,
                "selected_branch_id": converge_round.selected_branch_id,
                "dispatches": explore_round.dispatched_branch_ids,
                "merge_summary": converge_round.merge_summary,
            },
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Multi-branch round explored {len(explore_round.dispatched_branch_ids)} branch(es) "
                        f"and selected {converge_round.selected_branch_id}."
                    ),
                }
            ],
        }

    loop_service = SkillLoopService(
        state_store=state_store,
        run_service=run_service,
        recovery_service=recovery_service,
        transition_service=transition_service,
    )
    loop_result = loop_service.run_single_branch(
        run_id=run_snapshot.run_id,
        branch_id=branch_snapshot["branch_id"],
        policy=AgentExecutionPolicy(
            mode=execution_mode,
            max_stage_iterations=max_stage_iterations,
        ),
        stage_inputs=stage_inputs,
    )
    branch_after = state_store.load_branch_snapshot(loop_result.branch_id)

    return {
        "structuredContent": {
            "run": loop_result.run.model_dump(mode="json"),
            "branch": branch_snapshot if branch_after is None else branch_after.model_dump(mode="json"),
            "policy": {
                "mode": execution_mode.value,
                "max_stage_iterations": max_stage_iterations,
            },
            "history": loop_result.history,
            "stop_reason": loop_result.stop_reason.value,
        },
        "content": [{"type": "text", "text": loop_result.message}],
    }


__all__ = ["rd_agent"]
