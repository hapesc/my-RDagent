"""Service scaffold for the Planner module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

from data_models import Plan, PlanningContext

logger = logging.getLogger(__name__)


@dataclass
class PlannerConfig:
    """Configuration for planning behavior."""

    max_exploration_strength: float = 1.0
    default_budget_allocation: Dict[str, float] = None


class Planner:
    """Generates a plan for exploration and exploitation within a loop."""

    def __init__(self, config: PlannerConfig) -> None:
        """Initialize planner with strategy constraints and defaults."""

        self._config = config
        self._history: List[Dict[str, str]] = []
        if self._config.default_budget_allocation is None:
            self._config.default_budget_allocation = {}

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

        loop_state = context.loop_state
        budget = context.budget
        progress = self._compute_progress(budget.total_time_budget, budget.elapsed_time)
        stage = self._stage_from_progress(progress)

        exploration_strength = max(0.0, self._config.max_exploration_strength * (1.0 - progress))
        budget_allocation = self._build_budget_allocation(progress)
        guidance = self._build_guidance(stage, progress, context.history_summary)

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

    def update_planning_state(self, loop_result: Dict[str, str]) -> None:
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

    def _build_budget_allocation(self, progress: float) -> Dict[str, float]:
        allocation = dict(self._config.default_budget_allocation)
        if "exploration" not in allocation:
            allocation["exploration"] = 1.0 - progress
        if "exploitation" not in allocation:
            allocation["exploitation"] = progress
        return allocation

    def _build_guidance(
        self,
        stage: str,
        progress: float,
        history_summary: Dict[str, str],
    ) -> List[str]:
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
