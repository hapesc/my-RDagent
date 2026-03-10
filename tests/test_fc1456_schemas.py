"""Tests for PlanningStrategy and HypothesisModification schemas."""

from llm.schemas import HypothesisModification, PlanningStrategy


class TestPlanningStrategy:
    def test_from_dict_with_empty_dict(self):
        """Test PlanningStrategy.from_dict({}) returns object with defaults."""
        obj = PlanningStrategy.from_dict({})
        assert obj.strategy_name == ""
        assert obj.method_selection == ""
        assert obj.exploration_weight == 0.5
        assert obj.reasoning == ""

    def test_from_dict_with_full_data(self):
        """Test PlanningStrategy.from_dict with all fields provided."""
        data = {
            "strategy_name": "explore",
            "method_selection": "novelty",
            "exploration_weight": 0.8,
            "reasoning": "early stage",
        }
        obj = PlanningStrategy.from_dict(data)
        assert obj.strategy_name == "explore"
        assert obj.method_selection == "novelty"
        assert obj.exploration_weight == 0.8
        assert obj.reasoning == "early stage"


class TestHypothesisModification:
    def test_from_dict_with_empty_dict(self):
        """Test HypothesisModification.from_dict({}) returns object with defaults."""
        obj = HypothesisModification.from_dict({})
        assert obj.modified_hypothesis == ""
        assert obj.modification_type == ""
        assert obj.source_hypothesis == ""
        assert obj.reasoning == ""

    def test_from_dict_with_full_data(self):
        """Test HypothesisModification.from_dict with all fields provided."""
        data = {
            "modified_hypothesis": "test",
            "modification_type": "modify",
            "source_hypothesis": "orig",
            "reasoning": "because",
        }
        obj = HypothesisModification.from_dict(data)
        assert obj.modified_hypothesis == "test"
        assert obj.modification_type == "modify"
        assert obj.source_hypothesis == "orig"
        assert obj.reasoning == "because"
