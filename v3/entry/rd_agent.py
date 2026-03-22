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


_STAGE_TO_SKILL = {
    "framing": "rd-propose",
    "build": "rd-code",
    "verify": "rd-execute",
    "synthesize": "rd-evaluate",
    "evaluate": "rd-evaluate",
}


def _normalized_stage_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _summarize_state(
    *,
    route_kind: str,
    run_id: str | None = None,
    branch_id: str | None = None,
    stage_key: str | None = None,
) -> str:
    if route_kind == "continue_paused_run" and run_id and branch_id and stage_key:
        return (
            f"Current state: paused run {run_id} on branch {branch_id} is at {stage_key}."
        )
    return "Current state: no paused run dominates, so a new run can start."


def _extract_paused_run_context(persisted_state: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(persisted_state, dict):
        return None

    paused_runs = persisted_state.get("paused_runs")
    if isinstance(paused_runs, list) and paused_runs:
        preferred = next(
            (
                item
                for item in paused_runs
                if isinstance(item, dict)
                and (
                    item.get("is_current")
                    or item.get("is_selected")
                    or item.get("current_context")
                )
            ),
            None,
        )
        selection_reason = (
            "persisted state marked this paused run as the current continuation target."
            if preferred is not None
            else "persisted state did not mark a preferred paused run, so the first listed paused run is surfaced explicitly."
        )
        source = preferred if preferred is not None else paused_runs[0]
        if not isinstance(source, dict):
            return None
        run = source.get("run", source)
        branch = source.get("branch", source)
    else:
        run = persisted_state.get("run")
        branch = persisted_state.get("branch")
        selection_reason = "persisted state already exposes one paused run in the current working context."

    if not isinstance(run, dict) or not isinstance(branch, dict):
        return None

    branch_status = str(branch.get("status", "")).lower()
    run_status = str(run.get("status", "")).lower()
    stage_key = _normalized_stage_key(
        branch.get("current_stage_key") or branch.get("stage_key") or run.get("current_stage_key")
    )
    if "paused" not in branch_status and "awaiting_operator" not in run_status:
        return None
    if stage_key is None:
        return None

    run_id = run.get("run_id")
    branch_id = branch.get("branch_id")
    if not isinstance(run_id, str) or not isinstance(branch_id, str):
        return None

    recommended_skill = _STAGE_TO_SKILL.get(stage_key, "rd-agent")
    return {
        "run_id": run_id,
        "branch_id": branch_id,
        "stage_key": stage_key,
        "recommended_skill": recommended_skill,
        "selection_reason": selection_reason,
    }


def route_user_intent(
    user_intent: str,
    *,
    persisted_state: dict[str, Any] | None,
    high_level_boundary_sufficient: bool = True,
) -> dict[str, str]:
    """Route plain-language intent to the next high-level standalone V3 skill."""

    paused_context = _extract_paused_run_context(persisted_state)
    intent_text = user_intent.strip()

    if paused_context is not None:
        route_kind = "continue_paused_run"
        current_state = _summarize_state(
            route_kind=route_kind,
            run_id=paused_context["run_id"],
            branch_id=paused_context["branch_id"],
            stage_key=paused_context["stage_key"],
        )
        if not high_level_boundary_sufficient:
            return {
                "route_kind": "downshift_to_tool_catalog",
                "recommended_next_skill": "rd-tool-catalog",
                "current_state": current_state,
                "routing_reason": (
                    "Reason: paused run exists, but the high-level boundary is insufficient, "
                    "so routing downshifts after surfacing the continuation target."
                ),
                "exact_next_action": (
                    "Next action: inspect the paused run through rd-tool-catalog, then return "
                    f"to {paused_context['recommended_skill']} once the missing detail is resolved."
                ),
                "current_run_id": paused_context["run_id"],
                "current_branch_id": paused_context["branch_id"],
                "current_stage": paused_context["stage_key"],
            }

        return {
            "route_kind": route_kind,
            "recommended_next_skill": paused_context["recommended_skill"],
            "current_state": current_state,
            "routing_reason": (
                "Reason: paused run continuation takes priority over a new run, and "
                f"{paused_context['selection_reason']}"
            ),
            "exact_next_action": (
                "Next action: continue "
                f"{paused_context['run_id']} / {paused_context['branch_id']} with "
                f"{paused_context['recommended_skill']}."
            ),
            "current_run_id": paused_context["run_id"],
            "current_branch_id": paused_context["branch_id"],
            "current_stage": paused_context["stage_key"],
        }

    return {
        "route_kind": "start_new_run",
        "recommended_next_skill": "rd-agent",
        "current_state": _summarize_state(route_kind="start_new_run"),
        "routing_reason": (
            "Reason: plain-language intent did not name a skill, and no paused run "
            "dominates the current state."
        ),
        "exact_next_action": (
            "Next action: stay on rd-agent and start a new run from the request"
            + (f" \"{intent_text}\"." if intent_text else ".")
        ),
    }


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


__all__ = ["rd_agent", "route_user_intent"]
