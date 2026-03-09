"""Tests for FC-1 Planning Strategy and FC-4 Hypothesis Modification mocks."""
import json
import pytest
from llm.adapter import MockLLMProvider


class TestFC1PlanningStrategy:
    """Tests for FC-1 Planning Strategy mock responses."""

    def test_planning_strategy_detection(self):
        """Test that planning strategy prompt returns valid JSON with strategy fields."""
        provider = MockLLMProvider()
        
        # Prompt with planning strategy fields
        prompt = """
        Please generate a planning strategy.
        `strategy_name` should be selected from: balanced_exploration, focused_optimization
        `method_selection` should be one of: targeted_improvement, broad_search
        Based on current progress, recommend the best approach.
        """
        
        response = provider.complete(prompt)
        data = json.loads(response)
        
        # Verify required fields exist
        assert "strategy_name" in data
        assert "method_selection" in data
        assert "exploration_weight" in data
        assert "reasoning" in data
        
        # Verify field types
        assert isinstance(data["strategy_name"], str)
        assert isinstance(data["method_selection"], str)
        assert isinstance(data["exploration_weight"], (int, float))
        assert isinstance(data["reasoning"], str)


class TestFC4HypothesisModification:
    """Tests for FC-4 Hypothesis Modification mock responses."""

    def test_hypothesis_modification_detection(self):
        """Test that hypothesis modification prompt returns valid JSON with modification fields."""
        provider = MockLLMProvider()
        
        # Prompt with hypothesis modification fields
        prompt = """
        Modify the current hypothesis based on experimental results.
        `modified_hypothesis` should describe the updated hypothesis
        `modification_type` should be one of: modify, refine, replace
        Provide the source hypothesis and reasoning.
        `source_hypothesis` is the original hypothesis
        """
        
        response = provider.complete(prompt)
        data = json.loads(response)
        
        # Verify required fields exist
        assert "modified_hypothesis" in data
        assert "modification_type" in data
        assert "source_hypothesis" in data
        assert "reasoning" in data
        
        # Verify field types
        assert isinstance(data["modified_hypothesis"], str)
        assert isinstance(data["modification_type"], str)
        assert isinstance(data["source_hypothesis"], str)
        assert isinstance(data["reasoning"], str)


class TestFC3RegressionChecks:
    """Regression tests to ensure existing FC-3 patterns still work."""

    def test_analysis_detection_still_works(self):
        """Test that FC-3 analysis detection still works (regression check)."""
        provider = MockLLMProvider()
        
        # Prompt with FC-3 analysis fields
        prompt = """
        Analyze the current experimental design.
        `strengths` of the approach:
        - Good coverage
        `weaknesses` to address:
        - Limited depth
        """
        
        response = provider.complete(prompt)
        data = json.loads(response)
        
        # Verify FC-3 analysis fields
        assert "strengths" in data
        assert "weaknesses" in data
        assert "current_performance" in data
        assert "key_observations" in data
        assert isinstance(data["strengths"], list)
        assert isinstance(data["weaknesses"], list)

    def test_experiment_design_detection_still_works(self):
        """Test that FC-3 experiment design detection still works (regression check)."""
        provider = MockLLMProvider()
        
        # Prompt with FC-3 experiment design fields
        prompt = """
        Design an experiment to test the hypothesis.
        `implementation_steps` should be:
        1. Prepare
        2. Execute
        3. Measure
        """
        
        response = provider.complete(prompt)
        data = json.loads(response)
        
        # Verify FC-3 experiment design fields
        assert "summary" in data
        assert "constraints" in data
        assert "virtual_score" in data
        assert "implementation_steps" in data
        assert isinstance(data["implementation_steps"], list)
        assert isinstance(data["virtual_score"], (int, float))
