"""Primary V3 skill entrypoint for single-branch and multi-branch runs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from v3.contracts.exploration import ExplorationMode, HypothesisSpec
from v3.contracts.preflight import PreflightReadiness
from v3.contracts.run import ExecutionMode
from v3.contracts.tool_io import ConvergeRoundRequest, ExploreRoundRequest
from v3.entry.tool_catalog import call_cli_tool
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_prune_service import BranchPruneService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.execution_policy import AgentExecutionPolicy
from v3.orchestration.multi_branch_service import MultiBranchService
from v3.orchestration.branch_share_service import BranchShareService
from v3.orchestration.holdout_validation_service import HoldoutValidationService
from v3.orchestration.memory_service import MemoryService
from v3.orchestration.memory_state_store import MemoryStateStore
from v3.orchestration.operator_guidance import (
    STAGE_TO_NEXT_SKILL,
    build_finalization_guidance,
    build_paused_run_guidance,
    build_start_new_run_guidance,
    operator_guidance_to_dict,
)
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.select_parents_service import SelectParentsService
from v3.orchestration.selection_service import SelectionService
from v3.orchestration.skill_loop_service import SkillLoopService, StagePayload
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.holdout_port import EvaluationPort, HoldoutSplitPort, StratifiedKFoldSplitter
from v3.ports.memory_store import MemoryStorePort
from v3.ports.state_store import StateStorePort


def _normalized_stage_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


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
                and (item.get("is_current") or item.get("is_selected") or item.get("current_context"))
            ),
            None,
        )
        selection_reason = (
            "persisted state marked this paused run as the current continuation target."
            if preferred is not None
            else (
                "persisted state did not mark a preferred paused run, "
                "so the first listed paused run is surfaced explicitly."
            )
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

    recommended_skill = STAGE_TO_NEXT_SKILL.get(stage_key, "rd-agent")
    return {
        "run_id": run_id,
        "branch_id": branch_id,
        "stage_key": stage_key,
        "recommended_skill": recommended_skill,
        "selection_reason": selection_reason,
    }


def _normalize_preflight_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, dict):
        return result
    raise TypeError("preflight_result_provider must return a dict or PreflightResult")


def _paused_route_preflight_fields(
    paused_context: dict[str, str],
    *,
    preflight_result_provider: Callable[[dict[str, str]], Any] | None,
) -> dict[str, Any]:
    if preflight_result_provider is None:
        return {
            "current_action_status": "unknown_not_ready",
            "current_blocker_category": None,
            "current_blocker_reason": "Canonical preflight truth has not been evaluated for this paused stage yet.",
            "repair_action": (
                f"Run canonical preflight for {paused_context['run_id']} / {paused_context['branch_id']} "
                f"before continuing with {paused_context['recommended_skill']}."
            ),
            "exact_next_action": (
                "Next action: run canonical preflight for "
                f"{paused_context['run_id']} / {paused_context['branch_id']} before continuing with "
                f"{paused_context['recommended_skill']}."
            ),
        }

    preflight = _normalize_preflight_result(preflight_result_provider(paused_context))
    if preflight["readiness"] == PreflightReadiness.BLOCKED.value:
        repair_action = str(preflight["repair_action"])
        return {
            "current_action_status": "blocked",
            "current_blocker_category": preflight.get("primary_blocker_category"),
            "current_blocker_reason": preflight.get("primary_blocker_reason"),
            "repair_action": repair_action,
            "exact_next_action": (
                f"Next action: {repair_action} After repair, continue "
                f"{paused_context['run_id']} / {paused_context['branch_id']} with "
                f"{paused_context['recommended_skill']}."
            ),
        }

    return {
        "current_action_status": "executable",
        "current_blocker_category": None,
        "current_blocker_reason": None,
        "repair_action": str(preflight["repair_action"]),
        "exact_next_action": (
            "Next action: continue "
            f"{paused_context['run_id']} / {paused_context['branch_id']} with "
            f"{paused_context['recommended_skill']}."
        ),
    }


def route_user_intent(
    user_intent: str,
    *,
    persisted_state: dict[str, Any] | None,
    high_level_boundary_sufficient: bool = True,
    preflight_result_provider: Callable[[dict[str, str]], Any] | None = None,
) -> dict[str, Any]:
    """Route plain-language intent to the next high-level standalone V3 skill."""

    paused_context = _extract_paused_run_context(persisted_state)
    intent_text = user_intent.strip()

    if paused_context is not None:
        route_kind = "continue_paused_run"
        if not high_level_boundary_sufficient:
            return {
                "route_kind": "downshift_to_tool_catalog",
                "recommended_next_skill": "rd-tool-catalog",
                "current_state": (
                    "Current state: paused "
                    f"{paused_context['stage_key']} work for run {paused_context['run_id']} "
                    f"on branch {paused_context['branch_id']}."
                ),
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

        preflight_fields = _paused_route_preflight_fields(
            paused_context,
            preflight_result_provider=preflight_result_provider,
        )
        guidance = build_paused_run_guidance(
            run_id=paused_context["run_id"],
            branch_id=paused_context["branch_id"],
            stage_key=paused_context["stage_key"],
            recommended_next_skill=paused_context["recommended_skill"],
            selection_reason=paused_context["selection_reason"],
            current_action_status=preflight_fields["current_action_status"],
            current_blocker_category=preflight_fields["current_blocker_category"],
            current_blocker_reason=preflight_fields["current_blocker_reason"],
            repair_action=preflight_fields["repair_action"],
            exact_next_action=preflight_fields["exact_next_action"],
        )
        route_payload = {
            "route_kind": route_kind,
            "current_run_id": paused_context["run_id"],
            "current_branch_id": paused_context["branch_id"],
            "current_stage": paused_context["stage_key"],
        }
        route_payload.update(operator_guidance_to_dict(guidance))
        return route_payload

    guidance = build_start_new_run_guidance(user_intent=intent_text)
    route_payload = {
        "route_kind": "start_new_run",
    }
    route_payload.update(operator_guidance_to_dict(guidance))
    return route_payload


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
    exploration_mode: ExplorationMode = ExplorationMode.EXPLORATION,
    max_stage_iterations: int = 1,
    branch_hypotheses: list[str] | None = None,
    hypothesis_specs: list[HypothesisSpec] | None = None,
    auto_prune: bool = True,
    dispatcher=None,
    memory_store: MemoryStorePort | None = None,
    holdout_split_port: HoldoutSplitPort | None = None,
    holdout_evaluation_port: EvaluationPort | None = None,
) -> dict[str, Any]:
    if branch_hypotheses and hypothesis_specs:
        raise ValueError("Provide either branch_hypotheses or hypothesis_specs, not both")

    derived_hypotheses = branch_hypotheses
    if hypothesis_specs and not derived_hypotheses:
        derived_hypotheses = [spec.label for spec in hypothesis_specs]

    start_response = call_cli_tool(
        "rd_run_start",
        {
            "title": title,
            "task_summary": task_summary,
            "scenario_label": scenario_label,
            "initial_branch_label": initial_branch_label,
            "execution_mode": execution_mode,
            "exploration_mode": exploration_mode,
            "branch_hypotheses": derived_hypotheses,
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
            "exploration_mode": exploration_mode,
            "max_stage_iterations": max_stage_iterations,
        }
    )
    state_store.write_run_snapshot(run_snapshot)
    branch_snapshot = start_response["structuredContent"]["branch"]

    should_multi_branch = bool(derived_hypotheses and len(derived_hypotheses) > 1) or bool(
        hypothesis_specs and len(hypothesis_specs) > 1
    )
    if should_multi_branch:
        workspace_manager = BranchWorkspaceManager(getattr(state_store, "_root", ".state"))
        board_service = BranchBoardService(state_store)
        convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
        dag_service = DAGService(state_store) if hypothesis_specs is not None else None
        prune_service = (
            BranchPruneService(state_store=state_store, board_service=board_service)
            if hypothesis_specs is not None
            else None
        )
        select_parents_service = (
            SelectParentsService(state_store, dag_service)
            if hypothesis_specs is not None and dag_service is not None
            else None
        )

        # MemoryService requires MemoryStorePort, which is implemented by
        # MemoryStateStore (NOT ArtifactStateStore -- they are independent classes).
        # Use explicit memory_store if provided; otherwise construct from state_store._root.
        if memory_store is None:
            memory_store_root = getattr(state_store, "_root", ".state")
            memory_store = MemoryStateStore(memory_store_root)
        memory_service = MemoryService(memory_store)

        # holdout_evaluation_port is REQUIRED when hypothesis_specs is provided.
        # Without a real evaluator, HoldoutValidationService.finalize() would crash
        # with AttributeError (None.evaluate()), and _try_finalize only catches
        # ValueError/KeyError -- so the error propagates destructively.
        if hypothesis_specs is not None and holdout_evaluation_port is None:
            raise ValueError(
                "holdout_evaluation_port is required when hypothesis_specs is provided. "
                "Pass a real EvaluationPort for holdout finalization, or use "
                "StubEvaluationPort() for testing."
            )

        branch_share_service = (
            BranchShareService(
                state_store,
                memory_service,
                board_service=board_service,
                dag_service=dag_service,
            )
            if hypothesis_specs is not None and dag_service is not None
            else None
        )
        holdout_validation_service = (
            HoldoutValidationService(
                state_store=state_store,
                dag_service=dag_service,
                split_port=holdout_split_port or StratifiedKFoldSplitter(),
                evaluation_port=holdout_evaluation_port,
            )
            if hypothesis_specs is not None and dag_service is not None
            else None
        )
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
            dag_service=dag_service,
            prune_service=prune_service,
            select_parents_service=select_parents_service,
            branch_share_service=branch_share_service,
            holdout_validation_service=holdout_validation_service,
        )
        explore_round = multi_branch_service.run_exploration_round(
            ExploreRoundRequest(
                run_id=run_snapshot.run_id,
                hypotheses=derived_hypotheses or [],
                hypothesis_specs=hypothesis_specs,
                auto_prune=auto_prune,
            )
        )
        converge_round = multi_branch_service.run_convergence_round(
            ConvergeRoundRequest(
                run_id=run_snapshot.run_id,
            )
        )

        finalization_guidance = None
        finalization_submission_data = None
        if explore_round.finalization_submission is not None:
            fg = build_finalization_guidance(submission=explore_round.finalization_submission)
            finalization_guidance = operator_guidance_to_dict(fg)
            finalization_submission_data = explore_round.finalization_submission.model_dump(mode="json")

        run_snapshot = state_store.load_run_snapshot(run_snapshot.run_id) or run_snapshot
        return {
            "structuredContent": {
                "run": run_snapshot.model_dump(mode="json"),
                "board": converge_round.board.model_dump(mode="json"),
                "mode": converge_round.board.mode.value,
                "recommended_next_step": converge_round.recommended_next_step,
                "selected_branch_id": converge_round.selected_branch_id,
                "dispatches": explore_round.dispatched_branch_ids,
                "merge_summary": converge_round.merge_summary,
                "finalization_guidance": finalization_guidance,
                "finalization_submission": finalization_submission_data,
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
