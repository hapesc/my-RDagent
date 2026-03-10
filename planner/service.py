"""Service scaffold for the Planner module."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from data_models import Plan, PlanningContext
from llm.prompts import planning_strategy_prompt
from llm.schemas import PlanningStrategy

logger = logging.getLogger(__name__)

PLANNER_STEP_KEYS = ("proposal", "coding", "running", "feedback")
DEFAULT_TOTAL_TIME_BUDGET = 600.0
MINIMUM_STEP_TIME_BUDGET = 1.0


@dataclass
class PlannerConfig:
    """Configuration for planning behavior."""

    max_exploration_strength: float = 1.0
    default_budget_allocation: dict[str, float] | None = None
    use_llm_planning: bool = False


class Planner:
    """Generates a plan for exploration and exploitation within a loop."""

    def __init__(self, config: PlannerConfig, llm_adapter=None) -> None:
        """Initialize planner with strategy constraints and defaults."""

        self._config = config
        self._history: list[dict[str, str]] = []
        self._llm_adapter = llm_adapter
        if self._config.default_budget_allocation is None:
            self._config.default_budget_allocation = {}

    def generate_strategy(self, context: PlanningContext) -> PlanningStrategy | None:
        if self._llm_adapter is None or not self._config.use_llm_planning:
            return None

        budget = context.budget
        progress = self._compute_progress(budget.total_time_budget, budget.elapsed_time)
        stage = self._stage_from_progress(progress)
        budget_remaining = max(0.0, budget.total_time_budget - budget.elapsed_time)

        try:
            prompt = planning_strategy_prompt(
                task_summary="R&D exploration task",
                scenario_name="default",
                progress=progress,
                stage=stage,
                iteration=context.loop_state.iteration,
                history_summary=context.history_summary,
                budget_remaining=budget_remaining,
            )
            strategy = self._llm_adapter.generate_structured(prompt, PlanningStrategy)
            logger.info(
                "planner.strategy_generated name=%s weight=%.2f",
                strategy.strategy_name,
                strategy.exploration_weight,
            )
            return strategy
        except Exception as exc:
            logger.warning("planner.strategy_failed error=%s, falling back to heuristic", exc)
            return None

    def generate_plan(self, context: PlanningContext) -> Plan:
        """Generate a plan for the current loop iteration.

        Responsibility:
            Produce a Plan that allocates exploration strength and budget guidance.
        Input semantics:
            - context: PlanningContext with loop state and budget summary
        Output semantics:
            Plan with exploration strength and budget allocation placeholders.
        Architecture mapping:
            Planner -> generate_plan
        """

        strategy = self.generate_strategy(context)

        loop_state = context.loop_state
        budget = context.budget
        progress = self._compute_progress(budget.total_time_budget, budget.elapsed_time)
        stage = self._stage_from_progress(progress)
        if strategy is not None:
            exploration_strength = max(0.0, min(1.0, strategy.exploration_weight))
        else:
            exploration_strength = max(0.0, self._config.max_exploration_strength * (1.0 - progress))

        budget_allocation = self._coerce_strategy_budget_allocation(strategy)
        if budget_allocation is None:
            budget_allocation = self._build_budget_allocation(
                budget.total_time_budget,
                budget.elapsed_time,
            )
        guidance = self._build_guidance(stage, progress, context.history_summary)
        if strategy is not None:
            guidance.append(f"strategy:{strategy.strategy_name}")
            guidance.append(f"method:{strategy.method_selection}")
            if strategy.reasoning:
                guidance.append(f"rationale:{strategy.reasoning}")

        plan_id = f"plan-{loop_state.loop_id}-{loop_state.iteration}"
        logger.info(
            "planner.plan_generated loop_id=%s iteration=%d stage=%s progress=%.2f exploration=%.2f",
            loop_state.loop_id,
            loop_state.iteration,
            stage,
            progress,
            exploration_strength,
        )
        return Plan(
            plan_id=plan_id,
            exploration_strength=exploration_strength,
            budget_allocation=budget_allocation,
            guidance=guidance,
        )

    def update_planning_state(self, loop_result: dict[str, str]) -> None:
        """Update internal planning state from loop results.

        Responsibility:
            Ingest loop summary signals for the next plan.
        Input semantics:
            - loop_result: Key-value summary of loop outcomes
        Output semantics:
            None.
        Architecture mapping:
            Planner -> update_planning_state
        """

        self._history.append(dict(loop_result))
        logger.info("planner.state_updated entries=%d", len(self._history))
        return None

    def _compute_progress(self, total_budget: float, elapsed: float) -> float:
        if total_budget <= 0:
            logger.warning("planner.invalid_budget total=%.2f", total_budget)
            return 1.0
        progress = max(0.0, min(1.0, elapsed / total_budget))
        return progress

    def _stage_from_progress(self, progress: float) -> str:
        if progress < 0.33:
            return "early"
        if progress < 0.66:
            return "mid"
        return "late"

    def _coerce_strategy_budget_allocation(
        self,
        strategy: PlanningStrategy | None,
    ) -> dict[str, float] | None:
        if strategy is None or strategy.budget_allocation is None:
            return None

        allocation = strategy.budget_allocation
        if set(allocation.keys()) != set(PLANNER_STEP_KEYS):
            return None

        normalized: dict[str, float] = {}
        for step in PLANNER_STEP_KEYS:
            value = allocation.get(step)
            if value is None:
                return None

            try:
                seconds = float(value)
            except (TypeError, ValueError):
                return None

            if seconds <= 0:
                return None

            normalized[step] = seconds

        return normalized

    def _build_budget_allocation(self, total_budget: float, elapsed_time: float) -> dict[str, float]:
        effective_total_budget = total_budget if total_budget > 0 else DEFAULT_TOTAL_TIME_BUDGET
        remaining_budget = max(0.0, effective_total_budget - elapsed_time)

        if remaining_budget <= 0:
            return {step: MINIMUM_STEP_TIME_BUDGET for step in PLANNER_STEP_KEYS}

        step_budget = remaining_budget / len(PLANNER_STEP_KEYS)
        return {step: step_budget for step in PLANNER_STEP_KEYS}

    def _build_guidance(
        self,
        stage: str,
        progress: float,
        history_summary: dict[str, str],
    ) -> list[str]:
        guidance = [f"stage:{stage}", f"progress:{progress:.2f}"]
        if stage == "early":
            guidance.append("focus:novelty")
            guidance.append("budget:lightweight")
        elif stage == "mid":
            guidance.append("focus:balance")
            guidance.append("budget:moderate")
        else:
            guidance.append("focus:refine")
            guidance.append("budget:heavy")

        if history_summary:
            guidance.append("history:available")
        else:
            guidance.append("history:empty")
        return guidance
