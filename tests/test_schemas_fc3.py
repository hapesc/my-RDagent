"""TDD tests for FC-3 reasoning schemas."""

from llm.schemas import (
    AnalysisResult,
    ExperimentDesign,
    HypothesisFormulation,
    ProblemIdentification,
    VirtualEvalResult,
)


class TestAnalysisResult:
    """Test AnalysisResult schema."""

    def test_from_empty_dict(self):
        """Test AnalysisResult can be constructed from empty dict with defaults."""
        result = AnalysisResult.from_dict({})
        assert result.strengths == []
        assert result.weaknesses == []
        assert result.current_performance == ""
        assert result.key_observations == ""

    def test_from_full_dict(self):
        """Test AnalysisResult round-trip with full data."""
        data = {
            "strengths": ["Strong A", "Strong B"],
            "weaknesses": ["Weak A"],
            "current_performance": "85% accuracy",
            "key_observations": "Some observation",
        }
        result = AnalysisResult.from_dict(data)
        assert result.strengths == ["Strong A", "Strong B"]
        assert result.weaknesses == ["Weak A"]
        assert result.current_performance == "85% accuracy"
        assert result.key_observations == "Some observation"

    def test_from_partial_dict(self):
        """Test AnalysisResult with missing fields uses defaults."""
        data = {"strengths": ["Good"]}
        result = AnalysisResult.from_dict(data)
        assert result.strengths == ["Good"]
        assert result.weaknesses == []
        assert result.current_performance == ""
        assert result.key_observations == ""


class TestProblemIdentification:
    """Test ProblemIdentification schema."""

    def test_from_empty_dict(self):
        """Test ProblemIdentification can be constructed from empty dict with defaults."""
        result = ProblemIdentification.from_dict({})
        assert result.problem == ""
        assert result.severity == ""
        assert result.evidence == ""
        assert result.affected_component == ""

    def test_from_full_dict(self):
        """Test ProblemIdentification round-trip with full data."""
        data = {
            "problem": "Performance degradation",
            "severity": "high",
            "evidence": "10% slowdown observed",
            "affected_component": "data_loading",
        }
        result = ProblemIdentification.from_dict(data)
        assert result.problem == "Performance degradation"
        assert result.severity == "high"
        assert result.evidence == "10% slowdown observed"
        assert result.affected_component == "data_loading"


class TestHypothesisFormulation:
    """Test HypothesisFormulation schema."""

    def test_from_empty_dict(self):
        """Test HypothesisFormulation can be constructed from empty dict with defaults."""
        result = HypothesisFormulation.from_dict({})
        assert result.hypothesis == ""
        assert result.mechanism == ""
        assert result.expected_improvement == ""
        assert result.testable_prediction == ""

    def test_from_full_dict(self):
        """Test HypothesisFormulation round-trip with full data."""
        data = {
            "hypothesis": "Batch size affects performance",
            "mechanism": "GPU memory optimization",
            "expected_improvement": "15% faster",
            "testable_prediction": "Doubling batch size increases throughput",
        }
        result = HypothesisFormulation.from_dict(data)
        assert result.hypothesis == "Batch size affects performance"
        assert result.mechanism == "GPU memory optimization"
        assert result.expected_improvement == "15% faster"
        assert result.testable_prediction == "Doubling batch size increases throughput"


class TestExperimentDesign:
    """Test ExperimentDesign schema."""

    def test_from_empty_dict(self):
        """Test ExperimentDesign can be constructed from empty dict with defaults."""
        result = ExperimentDesign.from_dict({})
        assert result.summary == ""
        assert result.constraints == []
        assert result.virtual_score == 0.0
        assert result.implementation_steps == []

    def test_from_full_dict(self):
        """Test ExperimentDesign round-trip with full data."""
        data = {
            "summary": "Test batch size optimization",
            "constraints": ["Memory < 8GB", "Time < 1 hour"],
            "virtual_score": 0.85,
            "implementation_steps": ["Step 1", "Step 2"],
        }
        result = ExperimentDesign.from_dict(data)
        assert result.summary == "Test batch size optimization"
        assert result.constraints == ["Memory < 8GB", "Time < 1 hour"]
        assert result.virtual_score == 0.85
        assert result.implementation_steps == ["Step 1", "Step 2"]

    def test_virtual_score_type_conversion(self):
        """Test virtual_score is properly converted to float."""
        result = ExperimentDesign.from_dict({"virtual_score": "0.75"})
        assert result.virtual_score == 0.75
        assert isinstance(result.virtual_score, float)


class TestVirtualEvalResult:
    """Test VirtualEvalResult schema."""

    def test_from_empty_dict(self):
        """Test VirtualEvalResult can be constructed from empty dict with defaults."""
        result = VirtualEvalResult.from_dict({})
        assert result.rankings == []
        assert result.reasoning == ""
        assert result.selected_indices == []

    def test_from_full_dict(self):
        """Test VirtualEvalResult round-trip with full data."""
        data = {
            "rankings": [2, 0, 4, 1, 3],
            "reasoning": "Candidate 2 best",
            "selected_indices": [2, 0],
        }
        result = VirtualEvalResult.from_dict(data)
        assert result.rankings == [2, 0, 4, 1, 3]
        assert result.reasoning == "Candidate 2 best"
        assert result.selected_indices == [2, 0]

    def test_rankings_type_conversion(self):
        """Test rankings are properly converted to list of ints."""
        result = VirtualEvalResult.from_dict({"rankings": [2, 0, 4]})
        assert result.rankings == [2, 0, 4]
        assert all(isinstance(x, int) for x in result.rankings)

    def test_selected_indices_type_conversion(self):
        """Test selected_indices are properly converted to list of ints."""
        result = VirtualEvalResult.from_dict({"selected_indices": [0, 2]})
        assert result.selected_indices == [0, 2]
        assert all(isinstance(x, int) for x in result.selected_indices)
