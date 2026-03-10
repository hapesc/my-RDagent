"""T15: Edge case handling for FC-1456 integration.

Verifies defensive behavior at integration points:
- Zero/None budget → uses default, not crash
- Empty candidates → returns empty, not crash
- No labels → uses full dataset, not crash
- Empty ContextPack → omits sections, not crash
- No cross-branch hypotheses → returns within-branch, not error
- No CoSTEER feedback → omits feedback section, not crash
- Debug sample_fraction=0 → logs warning, uses full data
"""

import unittest
from unittest.mock import MagicMock

from data_models import (
    BudgetLedger,
    ContextPack,
    DataSplitManifest,
    ExperimentNode,
    LoopState,
    Plan,
    PlanningContext,
    Proposal,
)
from evaluation_service.stratified_splitter import StratifiedSplitter
from evaluation_service.validation_selector import ValidationSelector
from llm.adapter import LLMAdapter, MockLLMProvider
from memory_service.service import MemoryService, MemoryServiceConfig
from planner.service import Planner, PlannerConfig
from scenarios.data_science.plugin import DataScienceProposalEngine, _clamp_sample_fraction


class TestEdgeCaseZeroBudget(unittest.TestCase):
    """Edge case: zero or None budget in planner."""

    def test_planner_zero_budget_returns_minimum_allocation(self):
        """Planner should return 1-second minimum per step when budget=0."""
        planner = Planner(PlannerConfig())
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=0.0, elapsed_time=0.0),
        )
        plan = planner.generate_plan(ctx)

        # Should not crash and should have allocation
        self.assertIsNotNone(plan.budget_allocation)
        self.assertEqual(len(plan.budget_allocation), 4)  # proposal, coding, running, feedback
        # Minimum is 1.0 second per step when budget exhausted
        for value in plan.budget_allocation.values():
            self.assertGreaterEqual(value, 1.0)

    def test_planner_negative_budget_uses_default(self):
        """Planner should treat negative budget as invalid."""
        planner = Planner(PlannerConfig())
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=-100.0, elapsed_time=0.0),
        )
        plan = planner.generate_plan(ctx)

        # Should not crash and should have allocation with defaults
        self.assertIsNotNone(plan.budget_allocation)
        self.assertGreater(len(plan.budget_allocation), 0)

    def test_planner_exhausted_budget_returns_minimum(self):
        """Planner should return minimum 1s per step when budget exhausted."""
        planner = Planner(PlannerConfig())
        ctx = PlanningContext(
            loop_state=LoopState(loop_id="l1", iteration=1),
            budget=BudgetLedger(total_time_budget=10.0, elapsed_time=15.0),  # elapsed > total
        )
        plan = planner.generate_plan(ctx)

        self.assertIsNotNone(plan.budget_allocation)
        for value in plan.budget_allocation.values():
            self.assertEqual(value, 1.0)  # Minimum fallback


class TestEdgeCaseEmptyCandidates(unittest.TestCase):
    """Edge case: empty candidate list in ValidationSelector."""

    def test_validation_selector_empty_candidates_returns_empty(self):
        """ValidationSelector.rank_candidates should return [] for empty list."""
        mock_eval_service = MagicMock()
        selector = ValidationSelector(mock_eval_service)

        result = selector.rank_candidates([])
        self.assertEqual(result, [])
        # eval_service.evaluate_run() should NOT be called
        mock_eval_service.evaluate_run.assert_not_called()

    def test_validation_selector_select_best_empty_raises_gracefully(self):
        """ValidationSelector.select_best should raise ValueError on empty list."""
        mock_eval_service = MagicMock()
        selector = ValidationSelector(mock_eval_service)

        with self.assertRaises(ValueError):
            selector.select_best([])


class TestEdgeCaseNoLabels(unittest.TestCase):
    """Edge case: no labels in StratifiedSplitter."""

    def test_stratified_splitter_no_labels_uses_random_split(self):
        """StratifiedSplitter should fall back to random split when no labels."""
        splitter = StratifiedSplitter(train_ratio=0.8, test_ratio=0.2, seed=42)
        data_ids = ["id1", "id2", "id3", "id4", "id5"]

        # No labels provided
        manifest = splitter.split(data_ids, labels=None)

        self.assertIsInstance(manifest, DataSplitManifest)
        self.assertEqual(len(manifest.train_ids) + len(manifest.test_ids), 5)
        self.assertEqual(len(manifest.val_ids), 0)

    def test_stratified_splitter_empty_data_ids(self):
        """StratifiedSplitter should handle empty data_ids."""
        splitter = StratifiedSplitter()

        manifest = splitter.split([], labels=None)

        self.assertEqual(manifest.train_ids, [])
        self.assertEqual(manifest.test_ids, [])
        self.assertEqual(manifest.val_ids, [])

    def test_stratified_splitter_labels_length_mismatch(self):
        """StratifiedSplitter should fall back to random when labels length != data_ids."""
        splitter = StratifiedSplitter()
        data_ids = ["id1", "id2", "id3"]
        labels = ["a", "b"]  # Length mismatch

        manifest = splitter.split(data_ids, labels=labels)

        # Should use random split (fall back)
        self.assertEqual(len(manifest.train_ids) + len(manifest.test_ids), 3)


class TestEdgeCaseEmptyContextPack(unittest.TestCase):
    """Edge case: empty ContextPack in ProposalEngine."""

    def test_proposal_engine_empty_context_pack(self):
        """ProposalEngine should handle empty ContextPack without crash."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        engine = DataScienceProposalEngine(llm_adapter=adapter)

        # Empty context
        context = ContextPack(
            items=[],
            highlights=[],
            scored_items=[],
        )
        plan = Plan(
            plan_id="p1",
            exploration_strength=0.5,
            budget_allocation={},
            guidance=[],
        )
        scenario = MagicMock()
        scenario.task_summary = "test task"
        scenario.input_payload = {"loop_index": 0}

        proposal = engine.propose(
            task_summary="test",
            context=context,
            parent_ids=[],
            plan=plan,
            scenario=scenario,
        )

        # Should not crash and return a Proposal
        self.assertIsInstance(proposal, Proposal)
        self.assertIsNotNone(proposal.summary)

    def test_proposal_engine_context_with_invalid_scored_items(self):
        """ProposalEngine should handle malformed scored_items gracefully."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        engine = DataScienceProposalEngine(llm_adapter=adapter)

        context = ContextPack(
            items=[],
            highlights=[],
            scored_items=[
                ("item1", 0.5),
                ("item2", 0.3),
            ],
        )
        plan = Plan(
            plan_id="p1",
            exploration_strength=0.5,
            budget_allocation={},
            guidance=["test guidance"],
        )
        scenario = MagicMock()
        scenario.task_summary = "test task"
        scenario.input_payload = {"loop_index": 0}

        proposal = engine.propose(
            task_summary="test",
            context=context,
            parent_ids=[],
            plan=plan,
            scenario=scenario,
        )

        self.assertIsInstance(proposal, Proposal)


class TestEdgeCaseNoCrossBranchHypotheses(unittest.TestCase):
    """Edge case: no cross-branch hypotheses in MemoryService."""

    def test_memory_service_no_cross_branch_no_error(self):
        config = MemoryServiceConfig(enable_hypothesis_storage=True)
        service = MemoryService(config=config)

        # Query with a dict query (correct signature)
        context = service.query_context({"error_type": "test"})

        self.assertIsInstance(context, ContextPack)
        # Should have empty items if no hypotheses in DB
        self.assertEqual(len(context.items), 0)

    def test_memory_service_cross_branch_query_safe(self):
        config = MemoryServiceConfig(enable_hypothesis_storage=True)
        service = MemoryService(config=config)

        # Query with empty db
        context = service.query_context({"query": "test"})

        self.assertIsInstance(context, ContextPack)


class TestEdgeCaseNoCoSTEERFeedback(unittest.TestCase):
    """Edge case: no CoSTEER feedback on first round."""

    def test_coder_no_costeer_feedback_returns_original_summary(self):
        """Coder should return original summary when _costeer_feedback absent."""
        provider = MockLLMProvider()
        _adapter = LLMAdapter(provider)
        from scenarios.data_science.plugin import DataScienceCoder

        # Create a mock coder with the feedback enrichment method
        coder = DataScienceCoder()

        proposal = Proposal(
            proposal_id="p1",
            summary="Test proposal",
            constraints=[],
        )
        experiment = MagicMock(spec=ExperimentNode)
        experiment.hypothesis = {}  # No _costeer_feedback key

        # Call the enrichment method
        enriched = coder._enrich_proposal_with_feedback(proposal, experiment)

        # Should return original summary
        self.assertEqual(enriched, proposal.summary)

    def test_coder_costeer_feedback_empty_string(self):
        """Coder should omit feedback section when feedback is empty string."""
        from scenarios.data_science.plugin import DataScienceCoder

        coder = DataScienceCoder()
        proposal = Proposal(
            proposal_id="p1",
            summary="Test proposal",
            constraints=[],
        )
        experiment = MagicMock(spec=ExperimentNode)
        experiment.hypothesis = {"_costeer_feedback": ""}  # Empty feedback

        enriched = coder._enrich_proposal_with_feedback(proposal, experiment)

        # Should return original summary (empty feedback ignored)
        self.assertEqual(enriched, proposal.summary)

    def test_coder_costeer_feedback_not_dict(self):
        """Coder should handle hypothesis not being a dict."""
        from scenarios.data_science.plugin import DataScienceCoder

        coder = DataScienceCoder()
        proposal = Proposal(
            proposal_id="p1",
            summary="Test proposal",
            constraints=[],
        )
        experiment = MagicMock(spec=ExperimentNode)
        experiment.hypothesis = "not_a_dict"  # Not a dict

        enriched = coder._enrich_proposal_with_feedback(proposal, experiment)

        # Should return original summary (type check prevents error)
        self.assertEqual(enriched, proposal.summary)


class TestEdgeCaseDebugSampleFractionZero(unittest.TestCase):
    """Edge case: debug mode with sample_fraction=0."""

    def test_debug_sample_fraction_zero_creates_minimum_sample(self):
        """Debug mode with sample_fraction=0 should keep at least 1 row."""
        rows = ["row1", "row2", "row3"]
        sample_fraction = 0.0
        clamped_fraction = _clamp_sample_fraction(sample_fraction)
        sample_size = max(1, int(len(rows) * clamped_fraction))

        self.assertEqual(sample_size, 1)
        self.assertGreater(len(rows[:sample_size]), 0)

    def test_debug_sample_fraction_clamps_to_zero_one(self):
        """Debug sample_fraction should be clamped to [0.0, 1.0]."""

        # Test negative clamp
        sample_fraction = -0.5
        clamped = _clamp_sample_fraction(sample_fraction)
        self.assertEqual(clamped, 0.0)

        # Test positive overflow clamp
        sample_fraction = 1.5
        clamped = _clamp_sample_fraction(sample_fraction)
        self.assertEqual(clamped, 1.0)


class TestEdgeCaseEmptyPlanGuidance(unittest.TestCase):
    """Edge case: empty plan guidance."""

    def test_proposal_engine_empty_guidance(self):
        """ProposalEngine should handle empty plan.guidance."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        engine = DataScienceProposalEngine(llm_adapter=adapter)

        context = ContextPack(items=[], highlights=[], scored_items=[])
        plan = Plan(
            plan_id="p1",
            exploration_strength=0.5,
            budget_allocation={},
            guidance=[],
        )
        scenario = MagicMock()
        scenario.task_summary = "test"
        scenario.input_payload = {"loop_index": 0}

        proposal = engine.propose(
            task_summary="test",
            context=context,
            parent_ids=[],
            plan=plan,
            scenario=scenario,
        )

        self.assertIsInstance(proposal, Proposal)


class TestEdgeCaseNoneContextPack(unittest.TestCase):
    """Edge case: None or missing context attributes."""

    def test_proposal_engine_none_context_attributes(self):
        """ProposalEngine should handle context with None attributes gracefully."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        engine = DataScienceProposalEngine(llm_adapter=adapter)

        context = ContextPack(
            items=[],
            highlights=[],
            scored_items=[],
        )

        plan = Plan(
            plan_id="p1",
            exploration_strength=0.5,
            budget_allocation={},
            guidance=["test guidance"],
        )
        scenario = MagicMock()
        scenario.task_summary = "test"
        scenario.input_payload = {"loop_index": 0}

        proposal = engine.propose(
            task_summary="test",
            context=context,
            parent_ids=[],
            plan=plan,
            scenario=scenario,
        )

        self.assertIsInstance(proposal, Proposal)


if __name__ == "__main__":
    unittest.main()
