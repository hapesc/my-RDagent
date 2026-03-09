"""Loop engine for single-threaded iteration orchestration."""

from __future__ import annotations

import traceback
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, cast

from exploration_manager.scheduler import MCTSScheduler
from exploration_manager.service import supports_diverse_roots, supports_trace_merge

from core.storage.interfaces import EventMetadataStore, RunMetadataStore
from data_models import (
    BranchState,
    BudgetLedger,
    Event,
    EventType,
    ExecutionResult,
    ExplorationGraph,
    LoopContext,
    LoopState,
    NodeRecord,
    PlanningContext,
    RunSession,
    RunStatus,
    StepState,
)
from evaluation_service.validation_selector import ValidationSelector


@dataclass
class LoopEngineConfig:
    """Configuration for loop engine execution."""

    exception_archive_root: str = "/tmp/rd_agent_artifacts"
    default_max_loops: int = 1
    branches_per_iteration: int = 1
    layer0_n_candidates: int = 5
    layer0_k_forward: int = 2


class LoopEngine:
    """Coordinates loop iterations and persistence across services."""

    def __init__(
        self,
        config: LoopEngineConfig,
        planner,
        exploration_manager,
        memory_service,
        step_executor,
        run_store: RunMetadataStore,
        event_store: EventMetadataStore,
        scheduler: Optional[MCTSScheduler] = None,
        evaluation_service=None,
    ) -> None:
        self._config = config
        self._planner = planner
        self._exploration_manager = exploration_manager
        self._memory_service = memory_service
        self._step_executor = step_executor
        self._run_store = run_store
        self._event_store = event_store
        self._scheduler = scheduler
        self._evaluation_service = evaluation_service
        self._validation_selector = (
            ValidationSelector(evaluation_service) if evaluation_service is not None else None
        )

    def run(
        self,
        run_session: RunSession,
        task_summary: str,
        max_loops: Optional[int] = None,
        start_iteration: int = 0,
        restored_workspace: Optional[str] = None,
    ) -> LoopContext:
        run_session.update_status(RunStatus.RUNNING)
        self._run_store.create_run(run_session)

        loop_state = LoopState(
            loop_id=f"loop-{run_session.run_id}",
            iteration=start_iteration,
            status=RunStatus.RUNNING,
        )
        budget = BudgetLedger(total_time_budget=float(run_session.stop_conditions.max_duration_sec), elapsed_time=0.0)
        loop_context = LoopContext(loop_state=loop_state, budget=budget, run_session=run_session)
        graph = ExplorationGraph()
        layer0_n_candidates, layer0_k_forward = self._effective_layer0_width(run_session)
        if self._scheduler is not None and not graph.nodes:
            if supports_diverse_roots(self._exploration_manager):
                graph = self._exploration_manager.generate_diverse_roots(
                    graph,
                    task_summary,
                    run_session.scenario,
                    n_candidates=layer0_n_candidates,
                    k_forward=layer0_k_forward,
                )
            if not graph.nodes:
                graph.nodes.append(NodeRecord(node_id="root"))

        total_loop_limit = run_session.stop_conditions.max_loops or self._config.default_max_loops
        loops_this_call = max_loops if max_loops is not None else total_loop_limit
        target_iteration = min(total_loop_limit, start_iteration + max(0, loops_this_call))
        source_workspace = restored_workspace
        saw_usefulness_reject = False
        history_summary: Dict[str, Dict[str, Any]] = {}

        while loop_state.iteration < target_iteration:
            iter_start = time.monotonic()
            planning_context = PlanningContext(
                loop_state=loop_state,
                budget=budget,
                history_summary=cast(Dict[str, str], dict(history_summary)),
            )
            plan = self._planner.generate_plan(planning_context)
            context_pack = self._memory_service.query_context(
                {"run_id": run_session.run_id, "iteration": str(loop_state.iteration)}
            )

            if self._scheduler is None:
                parent_ids = self._exploration_manager.select_parents(graph, plan)

                try:
                    step_result = self._step_executor.execute_iteration(
                        run_session=run_session,
                        loop_state=loop_state,
                        task_summary=task_summary,
                        plan=plan,
                        parent_ids=parent_ids,
                        context_pack=context_pack,
                        source_workspace=source_workspace,
                    )
                except Exception as exc:
                    self._mark_iteration_failed(
                        run_session=run_session,
                        loop_state=loop_state,
                        error_message=str(exc),
                    )
                    self._archive_exception(run_session.run_id, loop_state.iteration, exc)
                    return loop_context

                if self._is_fatal_step_result(step_result):
                    self._mark_iteration_failed(
                        run_session=run_session,
                        loop_state=loop_state,
                        error_message=step_result.error_message
                        or self._build_fatal_result_message(step_result),
                        failed_stage=step_result.failed_stage,
                    )
                    return loop_context
                saw_usefulness_reject = saw_usefulness_reject or self._is_usefulness_rejected(step_result)

                node = NodeRecord(
                    node_id=step_result.experiment.node_id,
                    parent_ids=(
                        [step_result.experiment.parent_node_id]
                        if step_result.experiment.parent_node_id is not None
                        else parent_ids
                    ),
                    proposal_id=step_result.proposal.proposal_id,
                    artifact_id=step_result.artifact_id,
                    score_id=step_result.score.score_id,
                )
                node.score = self._continuation_score(step_result)
                graph = self._exploration_manager.register_node(graph, node)
                pruned_graph = self._exploration_manager.prune_branches(graph)
                if isinstance(pruned_graph, ExplorationGraph):
                    graph = pruned_graph
                history_summary[f"iteration_{loop_state.iteration}"] = self._build_iteration_history_entry(step_result)
            else:
                branches_per_iteration = self._effective_branches_per_iteration(run_session)
                successful_branches = 0
                failed_branches = 0
                successful_step_results = []
                branch_nodes = []
                
                for branch_index in range(branches_per_iteration):
                    selected_node_id = self._scheduler.select_node(graph)
                    if selected_node_id is None:
                        break

                    branch_source_workspace = source_workspace if branch_index == 0 else None
                    fork_parent_node_id = run_session.entry_input.get("fork_parent_node_id")
                    if branch_index == 0 and isinstance(fork_parent_node_id, str) and fork_parent_node_id:
                        parent_ids = []
                    else:
                        parent_ids = [selected_node_id]
                    try:
                        step_result = self._step_executor.execute_iteration(
                            run_session=run_session,
                            loop_state=loop_state,
                            task_summary=task_summary,
                            plan=plan,
                            parent_ids=parent_ids,
                            context_pack=context_pack,
                            source_workspace=branch_source_workspace,
                        )
                    except Exception as exc:
                        failed_branches += 1
                        self._archive_exception(run_session.run_id, loop_state.iteration, exc)
                        if branches_per_iteration <= 1:
                            self._mark_iteration_failed(
                                run_session=run_session,
                                loop_state=loop_state,
                                error_message=str(exc),
                            )
                            return loop_context
                        continue

                    if self._is_fatal_step_result(step_result):
                        failed_branches += 1
                        continue

                    saw_usefulness_reject = saw_usefulness_reject or self._is_usefulness_rejected(step_result)
                    successful_branches += 1
                    successful_step_results.append(step_result)

                    node = NodeRecord(
                        node_id=step_result.experiment.node_id,
                        parent_ids=(
                            [step_result.experiment.parent_node_id]
                            if step_result.experiment.parent_node_id is not None
                            else parent_ids
                        ),
                        proposal_id=step_result.proposal.proposal_id,
                        artifact_id=step_result.artifact_id,
                        score_id=step_result.score.score_id,
                    )
                    useful_decision = self._positive_continuation_decision(step_result)
                    node.score = self._continuation_score(step_result)
                    graph = self._exploration_manager.register_node(graph, node)
                    pruned_graph = self._exploration_manager.prune_branches(graph)
                    if isinstance(pruned_graph, ExplorationGraph):
                        graph = pruned_graph
                    
                    branch_nodes.append((node.node_id, step_result, useful_decision))

                if successful_branches > 1 and self._validation_selector is not None:
                    best_node_id = self._select_best_branch(successful_step_results, branch_nodes)
                    for node_id, step_result, original_decision in branch_nodes:
                        is_best = (node_id == best_node_id)
                        feedback_decision = original_decision if is_best else False
                        feedback_score = self._continuation_score(step_result) if is_best else None
                        self._exploration_manager.observe_feedback(
                            graph,
                            node_id,
                            score=feedback_score,
                            decision=feedback_decision,
                        )
                else:
                    for node_id, step_result, useful_decision in branch_nodes:
                        self._exploration_manager.observe_feedback(
                            graph,
                            node_id,
                            score=self._continuation_score(step_result),
                            decision=useful_decision,
                        )

                if failed_branches > 0 and successful_branches == 0:
                    self._mark_iteration_failed(
                        run_session=run_session,
                        loop_state=loop_state,
                        error_message="all branches failed in iteration",
                    )
                    return loop_context

                if successful_step_results:
                    selected_result = self._select_history_source_result(successful_step_results, branch_nodes)
                    history_summary[f"iteration_{loop_state.iteration}"] = self._build_iteration_history_entry(
                        selected_result
                    )

            source_workspace = None
            iter_elapsed = time.monotonic() - iter_start
            budget.elapsed_time += iter_elapsed
            budget.iteration_durations.append(iter_elapsed)
            recent = budget.iteration_durations[-3:]
            avg_duration = sum(recent) / len(recent)
            remaining_iters = max(0, target_iteration - loop_state.iteration - 1)
            budget.estimated_remaining = avg_duration * remaining_iters
            loop_state.iteration += 1
            self._run_store.create_run(run_session)

        active_nodes = []
        if isinstance(graph, ExplorationGraph):
            active_nodes = [node for node in graph.nodes if node.branch_state == BranchState.ACTIVE]
        if len(active_nodes) > 1 and supports_trace_merge(self._exploration_manager):
            merged = self._exploration_manager.merge_traces(graph, task_summary, run_session.scenario)
            if merged is not None:
                loop_context.merged_result = merged

        fail_on_usefulness_reject = self._is_real_provider_run(run_session)
        if loop_state.iteration >= total_loop_limit and not (fail_on_usefulness_reject and saw_usefulness_reject):
            run_session.update_status(RunStatus.COMPLETED)
            loop_state.status = RunStatus.COMPLETED
        elif loop_state.iteration >= total_loop_limit and fail_on_usefulness_reject and saw_usefulness_reject:
            run_session.update_status(RunStatus.FAILED)
            loop_state.status = RunStatus.FAILED
            run_session.entry_input["last_error"] = "run completed loops but usefulness gate rejected output"
        else:
            run_session.update_status(RunStatus.RUNNING)
            loop_state.status = RunStatus.RUNNING
        self._run_store.create_run(run_session)
        return loop_context

    def _is_fatal_step_result(self, step_result) -> bool:
        step_state = getattr(step_result, "step_state", None)
        if step_state == StepState.FAILED:
            return True
        outcome = getattr(step_result, "outcome", None)
        if outcome is not None:
            process_succeeded = getattr(outcome, "process_succeeded", None)
            if process_succeeded is False:
                return True
            if process_succeeded is True:
                artifacts_verified = getattr(outcome, "artifacts_verified", None)
                if artifacts_verified is False:
                    return True
        return False

    def _is_usefulness_rejected(self, step_result) -> bool:
        outcome = getattr(step_result, "outcome", None)
        if outcome is None:
            return False
        usefulness_eligible = getattr(outcome, "usefulness_eligible", None)
        return usefulness_eligible is False

    def _runtime_snapshot(self, run_session: RunSession) -> Dict[str, Any]:
        runtime_snapshot = run_session.config_snapshot.get("runtime")
        if isinstance(runtime_snapshot, dict):
            return runtime_snapshot
        return {}

    def _is_real_provider_run(self, run_session: RunSession) -> bool:
        return bool(self._runtime_snapshot(run_session).get("uses_real_llm_provider"))

    def _has_guardrail_warning(self, run_session: RunSession, field_name: str) -> bool:
        warnings = self._runtime_snapshot(run_session).get("guardrail_warnings")
        if not isinstance(warnings, list):
            return False
        token = f"{field_name}="
        return any(isinstance(item, str) and token in item for item in warnings)

    def _safe_profile_value(self, run_session: RunSession, field_name: str, fallback: int) -> int:
        safe_profile = self._runtime_snapshot(run_session).get("real_provider_safe_profile")
        if not isinstance(safe_profile, dict):
            return fallback
        value = safe_profile.get(field_name)
        if isinstance(value, int) and value > 0:
            return value
        return fallback

    def _effective_layer0_width(self, run_session: RunSession) -> tuple[int, int]:
        n_candidates = max(1, int(self._config.layer0_n_candidates))
        k_forward = max(1, int(self._config.layer0_k_forward))
        if not self._is_real_provider_run(run_session):
            return n_candidates, min(k_forward, n_candidates)

        if not self._has_guardrail_warning(run_session, "layer0_n_candidates"):
            n_candidates = min(
                n_candidates,
                self._safe_profile_value(run_session, "layer0_n_candidates", fallback=1),
            )
        if not self._has_guardrail_warning(run_session, "layer0_k_forward"):
            k_forward = min(
                k_forward,
                self._safe_profile_value(run_session, "layer0_k_forward", fallback=1),
            )
        return n_candidates, min(k_forward, n_candidates)

    def _effective_branches_per_iteration(self, run_session: RunSession) -> int:
        branches = max(1, int(self._config.branches_per_iteration))
        if self._is_real_provider_run(run_session):
            return 1
        return branches

    def _positive_continuation_decision(self, step_result) -> bool:
        outcome = getattr(step_result, "outcome", None)
        if outcome is not None:
            return bool(getattr(outcome, "usefulness_eligible", False))
        feedback = getattr(step_result, "feedback", None)
        if feedback is None:
            return False
        return bool(getattr(feedback, "decision", False))

    def _continuation_score(self, step_result) -> Optional[float]:
        if not self._positive_continuation_decision(step_result):
            return None
        score = getattr(step_result, "score", None)
        if score is None:
            return None
        value = getattr(score, "value", None)
        if isinstance(value, (float, int)):
            return float(value)
        return None

    def _build_fatal_result_message(self, step_result) -> str:
        outcome = getattr(step_result, "outcome", None)
        if outcome is None:
            return "iteration failed"
        return (
            "fatal step result: "
            f"process_status={outcome.process_status.value}, "
            f"artifact_status={outcome.artifact_status.value}, "
            f"usefulness_status={outcome.usefulness_status.value}"
        )

    def _select_history_source_result(self, successful_step_results: list, branch_nodes: list):
        if len(successful_step_results) == 1:
            return successful_step_results[0]

        best_node_id = None
        if self._validation_selector is not None:
            best_node_id = self._select_best_branch(successful_step_results, branch_nodes)

        if best_node_id is not None:
            for node_id, step_result, _ in branch_nodes:
                if node_id == best_node_id:
                    return step_result

        return max(successful_step_results, key=lambda result: self._continuation_score(result) or float("-inf"))

    def _build_iteration_history_entry(self, step_result) -> Dict[str, Any]:
        score = self._continuation_score(step_result)
        if score is None:
            raw_score = getattr(getattr(step_result, "score", None), "value", None)
            if isinstance(raw_score, (int, float)):
                score = float(raw_score)

        return {
            "hypothesis": self._extract_hypothesis_text(step_result),
            "score": float(score) if score is not None else 0.0,
            "outcome": self._extract_outcome_text(step_result),
        }

    def _extract_hypothesis_text(self, step_result) -> str:
        proposal_summary = getattr(getattr(step_result, "proposal", None), "summary", None)
        if isinstance(proposal_summary, str) and proposal_summary.strip():
            return proposal_summary.strip()

        experiment_hypothesis = getattr(getattr(step_result, "experiment", None), "hypothesis", None)
        if isinstance(experiment_hypothesis, str):
            return experiment_hypothesis.strip()
        if isinstance(experiment_hypothesis, dict):
            for key in ("hypothesis", "summary", "statement", "text"):
                value = experiment_hypothesis.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return str(experiment_hypothesis)
        return ""

    def _extract_outcome_text(self, step_result) -> str:
        outcome = getattr(step_result, "outcome", None)
        if outcome is not None:
            usefulness_status = getattr(outcome, "usefulness_status", None)
            if isinstance(usefulness_status, Enum):
                return str(usefulness_status.value)
            process_status = getattr(outcome, "process_status", None)
            if isinstance(process_status, Enum):
                return str(process_status.value)

        feedback = getattr(step_result, "feedback", None)
        if feedback is not None:
            decision = getattr(feedback, "decision", None)
            if isinstance(decision, bool):
                return "accepted" if decision else "rejected"

        step_state = getattr(step_result, "step_state", None)
        if isinstance(step_state, Enum):
            return str(step_state.value)
        if isinstance(step_state, str):
            return step_state
        return "unknown"

    def _mark_iteration_failed(
        self,
        run_session: RunSession,
        loop_state: LoopState,
        error_message: str,
        failed_stage: Optional[str] = None,
    ) -> None:
        run_session.entry_input["last_error"] = error_message
        run_session.update_status(RunStatus.FAILED)
        loop_state.status = RunStatus.FAILED
        self._run_store.create_run(run_session)
        self._event_store.append_event(
            Event(
                event_id=f"event-{uuid.uuid4().hex}",
                run_id=run_session.run_id,
                branch_id=run_session.active_branch_ids[0] if run_session.active_branch_ids else "main",
                loop_index=loop_state.iteration,
                step_name="record",
                event_type=EventType.TRACE_RECORDED,
                payload={"status": "FAILED", "error": error_message, "failed_stage": failed_stage},
            )
        )

    def _archive_exception(self, run_id: str, loop_index: int, exc: Exception) -> None:
        archive_dir = Path(self._config.exception_archive_root) / run_id / "exceptions"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"loop-{loop_index:04d}.log"
        archive_path.write_text(
            "\n".join(
                [
                    f"run_id={run_id}",
                    f"loop_index={loop_index}",
                    f"error={exc}",
                    traceback.format_exc(),
                ]
            ),
            encoding="utf-8",
        )

    def _select_best_branch(self, step_results: list, branch_nodes: list) -> Optional[str]:
        if not step_results or len(step_results) <= 1 or self._validation_selector is None:
            return None

        try:
            execution_results = []
            for step_result in step_results:
                exec_result = ExecutionResult(
                    run_id=step_result.experiment.node_id,
                    exit_code=0 if not self._is_fatal_step_result(step_result) else 1,
                    logs_ref="",
                    artifacts_ref=step_result.artifact_id or "",
                    duration_sec=0.0,
                    timed_out=False,
                )
                execution_results.append(exec_result)

            best_candidate, best_score = self._validation_selector.select_best(execution_results)
            
            best_node_id = best_candidate.run_id
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                "ValidationSelector.select_best() chose candidate with score %.4f (node_id=%s)",
                best_score.value,
                best_node_id,
            )
            return best_node_id
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("ValidationSelector.select_best() failed: %s; proceeding without selection", str(e))
            return None
