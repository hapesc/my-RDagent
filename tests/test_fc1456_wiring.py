from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from app.config import load_config
from app.runtime import build_runtime
from core.loop.engine import LoopEngine, LoopEngineConfig
from data_models import (
    ContextPack,
    Plan,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from tests._llm_test_utils import patch_runtime_llm_provider


class TestFC1456Wiring(unittest.TestCase):
    def _make_run_session(self, max_loops: int = 2) -> RunSession:
        return RunSession(
            run_id="test-run-001",
            scenario="synthetic_research",
            status=RunStatus.CREATED,
            stop_conditions=StopConditions(max_loops=max_loops, max_duration_sec=3600),
            entry_input={},
            active_branch_ids=["main"],
        )

    def _make_engine(self, max_loops: int = 1, branches: int = 1, planner=None) -> LoopEngine:
        mock_planner = planner or MagicMock()
        if planner is None:
            mock_planner.generate_plan.return_value = Plan(
                plan_id="plan-test",
                exploration_strength=0.5,
                budget_allocation={},
                guidance=[],
            )

        mock_memory = MagicMock()
        mock_memory.query_context.return_value = ContextPack(items=[], highlights=[])

        mock_exploration = MagicMock()
        mock_exploration.select_parents.return_value = ["root"]
        mock_exploration.register_node.side_effect = lambda g, n: g
        mock_exploration.prune_branches.side_effect = lambda g: g

        mock_step = MagicMock()

        call_count = {"value": 0}

        def _execute_iteration(**_kwargs):
            call_count["value"] += 1
            idx = call_count["value"]
            mock_result = MagicMock()
            mock_result.experiment = MagicMock()
            mock_result.experiment.node_id = f"node-{idx}"
            mock_result.experiment.parent_node_id = None
            mock_result.proposal = MagicMock()
            mock_result.proposal.proposal_id = f"proposal-{idx}"
            mock_result.artifact_id = f"artifact-{idx}"
            mock_result.score = Score(score_id=f"score-{idx}", value=0.5, metric_name="mock")
            return mock_result

        mock_step.execute_iteration.side_effect = _execute_iteration

        mock_run_store = MagicMock()
        mock_event_store = MagicMock()

        return LoopEngine(
            config=LoopEngineConfig(default_max_loops=max_loops, branches_per_iteration=branches),
            planner=mock_planner,
            exploration_manager=mock_exploration,
            memory_service=mock_memory,
            step_executor=mock_step,
            run_store=mock_run_store,
            event_store=mock_event_store,
        )

    def test_config_loads_hypothesis_storage_true(self):
        config = load_config({"RD_AGENT_HYPOTHESIS_STORAGE": "true"})
        self.assertTrue(config.enable_hypothesis_storage)

    def test_config_loads_hypothesis_storage_default(self):
        config = load_config({})
        self.assertFalse(config.enable_hypothesis_storage)

    def test_config_loads_llm_planning_true(self):
        config = load_config({"RD_AGENT_LLM_PLANNING": "true"})
        self.assertTrue(config.use_llm_planning)

    def test_config_loads_llm_planning_default(self):
        config = load_config({})
        self.assertFalse(config.use_llm_planning)

    def test_config_loads_debug_mode(self):
        config = load_config({"RD_AGENT_DEBUG_MODE": "true"})
        self.assertTrue(config.debug_mode)

    def test_build_runtime_succeeds(self):
        with (
            patch.dict(
                os.environ,
                {
                    "RD_AGENT_LLM_PROVIDER": "mock",
                    "RD_AGENT_HYPOTHESIS_STORAGE": "false",
                    "RD_AGENT_LLM_PLANNING": "false",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()
        self.assertIsNotNone(runtime)
        self.assertFalse(runtime.config.enable_hypothesis_storage)
        self.assertFalse(runtime.config.use_llm_planning)

    def test_loop_engine_updates_elapsed_time(self):
        engine = self._make_engine(max_loops=1)
        session = self._make_run_session(max_loops=1)
        ctx = engine.run(session, task_summary="test")
        self.assertGreater(ctx.budget.elapsed_time, 0.0)

    def test_loop_engine_populates_iteration_durations(self):
        engine = self._make_engine(max_loops=2)
        session = self._make_run_session(max_loops=2)
        ctx = engine.run(session, task_summary="test")
        self.assertEqual(len(ctx.budget.iteration_durations), 2)
        for duration in ctx.budget.iteration_durations:
            self.assertGreater(duration, 0.0)

    def test_loop_engine_computes_estimated_remaining(self):
        checks = {"saw_positive": False}

        def _plan_side_effect(context):
            if context.loop_state.iteration == 1 and context.budget.estimated_remaining > 0.0:
                checks["saw_positive"] = True
            return Plan(
                plan_id=f"plan-{context.loop_state.iteration}",
                exploration_strength=0.5,
                budget_allocation={},
                guidance=[],
            )

        planner = MagicMock()
        planner.generate_plan.side_effect = _plan_side_effect
        engine = self._make_engine(max_loops=3, planner=planner)
        session = self._make_run_session(max_loops=3)

        ctx = engine.run(session, task_summary="test")

        self.assertTrue(checks["saw_positive"])
        self.assertEqual(len(ctx.budget.iteration_durations), 3)
        self.assertEqual(ctx.budget.estimated_remaining, 0.0)


if __name__ == "__main__":
    unittest.main()
