"""Service scaffold for the Orchestrator / R&D Loop Engine."""

from __future__ import annotations

from dataclasses import dataclass

from data_models import BudgetLedger, LoopContext, LoopState, PhaseResultMeta, RunSession, RunStatus, StopConditions


@dataclass
class OrchestratorConfig:
    """Configuration for loop orchestration."""

    time_budget_seconds: float
    termination_policy: str = "time_budget"


class OrchestratorRDLoopEngine:
    """Drives the research and development loop within a fixed budget."""

    def __init__(self, config: OrchestratorConfig) -> None:
        """Initialize with time budget and termination policy."""

        self._config = config

    def start_loop(self, task_id: str) -> LoopContext:
        """Start a new R&D loop instance.

        Responsibility:
            Initialize loop state and budget tracking for orchestration.
        Input semantics:
            - task_id: Identifier for the task
        Output semantics:
            LoopContext containing LoopState and BudgetLedger.
        Architecture mapping:
            Orchestrator / R&D Loop Engine -> start_loop
        """

        run_session = RunSession(
            run_id=f"run-{task_id}",
            scenario="data_science",
            status=RunStatus.RUNNING,
            stop_conditions=StopConditions(max_duration_sec=int(self._config.time_budget_seconds)),
            entry_input={"task_id": task_id},
        )
        loop_state = LoopState(loop_id=f"loop-{task_id}", iteration=0, status=RunStatus.RUNNING)
        budget = BudgetLedger(total_time_budget=self._config.time_budget_seconds, elapsed_time=0.0)
        return LoopContext(loop_state=loop_state, budget=budget, run_session=run_session)

    def tick_loop(self, loop_context: LoopContext, phase_result: PhaseResultMeta) -> LoopContext:
        """Advance the loop by one placeholder step.

        Responsibility:
            Record phase metadata and advance loop state deterministically.
        Input semantics:
            - loop_context: Current loop context
            - phase_result: Minimal metadata from the completed phase
        Output semantics:
            Updated LoopContext with incremented iteration.
        Architecture mapping:
            Orchestrator / R&D Loop Engine -> tick_loop
        """

        _ = phase_result
        loop_context.loop_state.iteration += 1
        return loop_context

    def stop_loop(self, loop_context: LoopContext) -> LoopContext:
        """Stop the loop execution.

        Responsibility:
            Mark loop state as stopped for final submission.
        Input semantics:
            - loop_context: Current loop context
        Output semantics:
            Updated LoopContext with stopped status.
        Architecture mapping:
            Orchestrator / R&D Loop Engine -> stop_loop
        """

        loop_context.loop_state.status = RunStatus.STOPPED
        if loop_context.run_session is not None:
            loop_context.run_session.update_status(RunStatus.STOPPED)
        return loop_context
