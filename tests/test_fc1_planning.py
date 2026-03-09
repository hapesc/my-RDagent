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

    def test_generate_plan_prefers_valid_llm_budget_allocation(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=2),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=50.0),
        )
        plan = self.planner.generate_plan(ctx)
        self.assertEqual(set(plan.budget_allocation.keys()), {"proposal", "coding", "running", "feedback"})
        self.assertEqual(
            plan.budget_allocation,
            {"proposal": 120.0, "coding": 180.0, "running": 60.0, "feedback": 60.0},
        )
        for seconds in plan.budget_allocation.values():
            self.assertGreater(seconds, 0.0)

    def test_generate_plan_includes_history_and_strategy_guidance(self):
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=2),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=50.0),
            history_summary={"iteration_1": "improved baseline"},
        )

        plan = self.planner.generate_plan(ctx)

        self.assertIn("history:available", plan.guidance)
        self.assertIn("strategy:balanced_exploration", plan.guidance)
        self.assertIn("method:targeted_improvement", plan.guidance)
        self.assertIn("rationale:Mock planning strategy based on current progress", plan.guidance)

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

    def test_invalid_llm_budget_falls_back_to_equal_step_split(self):
        class InvalidBudgetProvider:
            def complete(self, prompt, model_config=None):
                return json.dumps(
                    {
                        "strategy_name": "invalid_budget",
                        "method_selection": "fallback",
                        "exploration_weight": 0.4,
                        "reasoning": "invalid budget payload",
                        "budget_allocation": {"proposal": 10, "coding": 20},
                    }
                )

        adapter = LLMAdapter(InvalidBudgetProvider())
        planner = Planner(
            PlannerConfig(use_llm_planning=True),
            llm_adapter=adapter,
        )
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=100.0, elapsed_time=20.0),
        )
        plan = planner.generate_plan(ctx)
        self.assertEqual(set(plan.budget_allocation.keys()), {"proposal", "coding", "running", "feedback"})
        self.assertEqual(
            plan.budget_allocation,
            {"proposal": 20.0, "coding": 20.0, "running": 20.0, "feedback": 20.0},
        )
        self.assertTrue(all(seconds == 20.0 for seconds in plan.budget_allocation.values()))

    def test_default_budget_allocation_uses_default_total_when_budget_invalid(self):
        planner = Planner(PlannerConfig())
        allocation = planner._build_budget_allocation(total_budget=0.0, elapsed_time=100.0)
        self.assertEqual(
            allocation,
            {"proposal": 125.0, "coding": 125.0, "running": 125.0, "feedback": 125.0},
        )

    def test_default_budget_allocation_uses_minimum_when_remaining_depleted(self):
        planner = Planner(PlannerConfig())
        allocation = planner._build_budget_allocation(total_budget=100.0, elapsed_time=120.0)
        self.assertEqual(
            allocation,
            {"proposal": 1.0, "coding": 1.0, "running": 1.0, "feedback": 1.0},
        )
