"""Loop engine for single-threaded iteration orchestration."""

from __future__ import annotations

import traceback
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from exploration_manager.scheduler import MCTSScheduler

from core.storage.interfaces import EventMetadataStore, RunMetadataStore
from data_models import (
    BranchState,
    BudgetLedger,
    Event,
    EventType,
    ExplorationGraph,
    LoopContext,
    LoopState,
    NodeRecord,
    PlanningContext,
    RunSession,
    RunStatus,
)


@dataclass
class LoopEngineConfig:
    """Configuration for loop engine execution."""

    exception_archive_root: str = "/tmp/rd_agent_artifacts"
    default_max_loops: int = 1
    branches_per_iteration: int = 1


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
    ) -> None:
        self._config = config
        self._planner = planner
        self._exploration_manager = exploration_manager
        self._memory_service = memory_service
        self._step_executor = step_executor
        self._run_store = run_store
        self._event_store = event_store
        self._scheduler = scheduler

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
        if self._scheduler is not None and not graph.nodes:
            if hasattr(self._exploration_manager, "generate_diverse_roots"):
                graph = self._exploration_manager.generate_diverse_roots(
                    graph,
                    task_summary,
                    run_session.scenario,
                    n_candidates=5,
                    k_forward=2,
                )
            if not graph.nodes:
                graph.nodes.append(NodeRecord(node_id="root"))

        total_loop_limit = run_session.stop_conditions.max_loops or self._config.default_max_loops
        loops_this_call = max_loops if max_loops is not None else total_loop_limit
        target_iteration = min(total_loop_limit, start_iteration + max(0, loops_this_call))
        source_workspace = restored_workspace

        while loop_state.iteration < target_iteration:
            iter_start = time.monotonic()
            planning_context = PlanningContext(loop_state=loop_state, budget=budget, history_summary={})
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
                    self._archive_exception(run_session.run_id, loop_state.iteration, exc)
                    run_session.entry_input["last_error"] = str(exc)
                    run_session.update_status(RunStatus.FAILED)
                    loop_state.status = RunStatus.FAILED
                    self._run_store.create_run(run_session)
                    self._event_store.append_event(
                        Event(
                            event_id=f"event-{uuid.uuid4().hex}",
                            run_id=run_session.run_id,
                            branch_id=run_session.active_branch_ids[0]
                            if run_session.active_branch_ids
                            else "main",
                            loop_index=loop_state.iteration,
                            step_name="record",
                            event_type=EventType.TRACE_RECORDED,
                            payload={"status": "FAILED", "error": str(exc)},
                        )
                    )
                    return loop_context

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
                graph = self._exploration_manager.register_node(graph, node)
                pruned_graph = self._exploration_manager.prune_branches(graph)
                if isinstance(pruned_graph, ExplorationGraph):
                    graph = pruned_graph
            else:
                for branch_index in range(self._config.branches_per_iteration):
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
                        self._archive_exception(run_session.run_id, loop_state.iteration, exc)
                        if self._config.branches_per_iteration <= 1:
                            run_session.entry_input["last_error"] = str(exc)
                            run_session.update_status(RunStatus.FAILED)
                            loop_state.status = RunStatus.FAILED
                            self._run_store.create_run(run_session)
                            self._event_store.append_event(
                                Event(
                                    event_id=f"event-{uuid.uuid4().hex}",
                                    run_id=run_session.run_id,
                                    branch_id=run_session.active_branch_ids[0]
                                    if run_session.active_branch_ids
                                    else "main",
                                    loop_index=loop_state.iteration,
                                    step_name="record",
                                    event_type=EventType.TRACE_RECORDED,
                                    payload={"status": "FAILED", "error": str(exc)},
                                )
                            )
                            return loop_context
                        traceback.print_exc()
                        continue

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
                    node.score = step_result.score.value
                    graph = self._exploration_manager.register_node(graph, node)
                    pruned_graph = self._exploration_manager.prune_branches(graph)
                    if isinstance(pruned_graph, ExplorationGraph):
                        graph = pruned_graph
                    self._exploration_manager.observe_feedback(
                        graph,
                        node.node_id,
                        score=step_result.score.value,
                        decision=step_result.feedback.decision,
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
        if len(active_nodes) > 1 and hasattr(self._exploration_manager, "merge_traces"):
            merged = self._exploration_manager.merge_traces(graph, task_summary, run_session.scenario)
            if merged is not None:
                loop_context.merged_result = merged

        if loop_state.iteration >= total_loop_limit:
            run_session.update_status(RunStatus.COMPLETED)
            loop_state.status = RunStatus.COMPLETED
        else:
            run_session.update_status(RunStatus.RUNNING)
            loop_state.status = RunStatus.RUNNING
        self._run_store.create_run(run_session)
        return loop_context

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
