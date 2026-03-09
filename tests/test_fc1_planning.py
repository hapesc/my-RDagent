import unittest
import json
from data_models import PlanningContext, LoopState, BudgetLedger
from planner.service import Planner, PlannerConfig
from llm.adapter import LLMAdapter, MockLLMProvider
from llm.schemas import PlanningStrategy


class TestPlannerBackwardCompatibility(unittest.TestCase):
    def test_generate_plan_no_llm(self):
        planner = Planner(PlannerConfig())
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=30.0),
        )
        plan = planner.generate_plan(ctx)
        self.assertTrue(plan.plan_id.startswith("plan-"))
        self.assertGreaterEqual(plan.exploration_strength, 0.0)
        self.assertLessEqual(plan.exploration_strength, 1.0)

    def test_planner_config_default(self):
        config = PlannerConfig()
        self.assertEqual(config.max_exploration_strength, 1.0)
        self.assertFalse(config.use_llm_planning)

    def test_update_planning_state(self):
        planner = Planner(PlannerConfig())
        planner.update_planning_state({"result": "ok"})


class TestPlannerWithLLM(unittest.TestCase):
    def setUp(self):
        self.provider = MockLLMProvider()
        self.adapter = LLMAdapter(self.provider)
        self.planner = Planner(
            PlannerConfig(use_llm_planning=True),
            llm_adapter=self.adapter,
        )

    def test_generate_strategy_returns_planning_strategy(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=10.0),
        )
        strategy = self.planner.generate_strategy(ctx)
        self.assertIsInstance(strategy, PlanningStrategy)
        self.assertIsNotNone(strategy)
        assert strategy is not None
        self.assertTrue(strategy.strategy_name)
        self.assertTrue(strategy.method_selection)

    def test_generate_plan_uses_llm_strategy(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=2),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=50.0),
        )
        plan = self.planner.generate_plan(ctx)
        self.assertTrue(plan.plan_id)
        self.assertGreaterEqual(plan.exploration_strength, 0.0)
        self.assertLessEqual(plan.exploration_strength, 1.0)

    def test_generate_plan_early_progress(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=0),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=10.0),
        )
        plan = self.planner.generate_plan(ctx)
        self.assertGreater(plan.exploration_strength, 0.3)

    def test_generate_plan_late_progress(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=9),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=90.0),
        )
        plan = self.planner.generate_plan(ctx)
        self.assertLess(plan.exploration_strength, 0.7)

    def test_generate_plan_mid_progress(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=5),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=50.0),
        )
        plan = self.planner.generate_plan(ctx)
        self.assertGreaterEqual(plan.exploration_strength, 0.0)
        self.assertLessEqual(plan.exploration_strength, 1.0)


class TestPlannerLLMFallback(unittest.TestCase):
    def test_llm_failure_falls_back_to_heuristic(self):
        class FailingProvider:
            def complete(self, prompt, model_config=None):
                raise RuntimeError("LLM unavailable")

        adapter = LLMAdapter(FailingProvider())
        planner = Planner(
            PlannerConfig(use_llm_planning=True),
            llm_adapter=adapter,
        )
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=30.0),
        )
        plan = planner.generate_plan(ctx)
        self.assertTrue(plan.plan_id)
        self.assertGreaterEqual(plan.exploration_strength, 0.0)

    def test_no_llm_adapter_no_strategy(self):
        planner = Planner(PlannerConfig())
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=30.0),
        )
        strategy = planner.generate_strategy(ctx)
        self.assertIsNone(strategy)
