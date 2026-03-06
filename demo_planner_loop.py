"""Demo for Planner within a single R&D loop."""

from __future__ import annotations

import logging

from data_models import PhaseResultMeta, PlanningContext
from orchestrator_rd_loop_engine import OrchestratorConfig, OrchestratorRDLoopEngine
from planner import Planner, PlannerConfig


def run_demo() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    orchestrator = OrchestratorRDLoopEngine(OrchestratorConfig(time_budget_seconds=120.0))
    loop_context = orchestrator.start_loop("demo-task")

    planner = Planner(PlannerConfig(max_exploration_strength=1.0))

    loop_context.budget.elapsed_time = 30.0
    planning_context = PlanningContext(
        loop_state=loop_context.loop_state,
        budget=loop_context.budget,
        history_summary={},
    )
    plan = planner.generate_plan(planning_context)
    print("[Planner] plan", plan.plan_id, plan.exploration_strength, plan.budget_allocation, plan.guidance)

    planner.update_planning_state({"last_score": "0.0", "notes": "demo"})
    loop_context = orchestrator.tick_loop(loop_context, PhaseResultMeta(notes="demo"))
    loop_context = orchestrator.stop_loop(loop_context)
    print(f"[R&D Loop] stopped (status={loop_context.loop_state.status})")


if __name__ == "__main__":
    run_demo()
