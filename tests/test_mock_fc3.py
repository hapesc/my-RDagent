"""TDD tests for MockLLMProvider FC-3 reasoning stage extensions."""

import json
import pytest
from llm.adapter import LLMAdapter, MockLLMProvider
from llm.schemas import (
    AnalysisResult,
    ProblemIdentification,
    HypothesisFormulation,
    ExperimentDesign,
    VirtualEvalResult,
)


class TestMockAnalysisDetection:
    """Test AnalysisResult detection and response generation."""

    def test_analysis_detection_on_strengths_field(self):
        """Mock should detect and respond to analysis prompts with strengths field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Analyze the proposal.\n"
            "## Output Fields\n"
            "- `strengths`: list of strengths\n"
            "- `weaknesses`: list of weaknesses"
        )
        
        result = adapter.generate_structured(prompt, AnalysisResult)
        assert isinstance(result, AnalysisResult)
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.current_performance, str)
        assert isinstance(result.key_observations, str)

    def test_analysis_detection_on_weaknesses_field(self):
        """Mock should detect analysis on weaknesses field too."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Analyze the approach.\n"
            "## Output Fields\n"
            "- `weaknesses`: list of limitations"
        )
        
        result = adapter.generate_structured(prompt, AnalysisResult)
        assert isinstance(result, AnalysisResult)
        assert isinstance(result.strengths, list)


class TestMockProblemDetection:
    """Test ProblemIdentification detection and response generation."""

    def test_problem_detection_on_severity_field(self):
        """Mock should detect problem prompts with severity field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Identify the problem.\n"
            "## Output Fields\n"
            "- `severity`: how critical is this\n"
            "- `problem`: description"
        )
        
        result = adapter.generate_structured(prompt, ProblemIdentification)
        assert isinstance(result, ProblemIdentification)
        assert isinstance(result.problem, str)
        assert isinstance(result.severity, str)
        assert isinstance(result.evidence, str)
        assert isinstance(result.affected_component, str)

    def test_problem_detection_on_affected_component_field(self):
        """Mock should detect problem on affected_component field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "What component is affected?\n"
            "## Output Fields\n"
            "- `affected_component`: which part"
        )
        
        result = adapter.generate_structured(prompt, ProblemIdentification)
        assert isinstance(result, ProblemIdentification)
        assert isinstance(result.affected_component, str)


class TestMockHypothesisDetection:
    """Test HypothesisFormulation detection and response generation."""

    def test_hypothesis_detection_on_mechanism_field(self):
        """Mock should detect hypothesis prompts with mechanism field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Formulate a hypothesis.\n"
            "## Output Fields\n"
            "- `mechanism`: how it works\n"
            "- `hypothesis`: the claim"
        )
        
        result = adapter.generate_structured(prompt, HypothesisFormulation)
        assert isinstance(result, HypothesisFormulation)
        assert isinstance(result.hypothesis, str)
        assert isinstance(result.mechanism, str)
        assert isinstance(result.expected_improvement, str)
        assert isinstance(result.testable_prediction, str)

    def test_hypothesis_detection_on_testable_prediction_field(self):
        """Mock should detect hypothesis on testable_prediction field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "What is testable?\n"
            "## Output Fields\n"
            "- `testable_prediction`: the measurable outcome"
        )
        
        result = adapter.generate_structured(prompt, HypothesisFormulation)
        assert isinstance(result, HypothesisFormulation)
        assert isinstance(result.testable_prediction, str)


class TestMockExperimentDetection:
    """Test ExperimentDesign detection and response generation."""

    def test_experiment_detection_on_implementation_steps(self):
        """Mock should detect experiment design prompts with implementation_steps field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Design an experiment.\n"
            "## Output Fields\n"
            "- `implementation_steps`: steps to execute\n"
            "- `summary`: overview"
        )
        
        result = adapter.generate_structured(prompt, ExperimentDesign)
        assert isinstance(result, ExperimentDesign)
        assert isinstance(result.summary, str)
        assert isinstance(result.constraints, list)
        assert isinstance(result.virtual_score, float)
        assert isinstance(result.implementation_steps, list)


class TestMockVirtualEvalDetection:
    """Test VirtualEvalResult detection and response generation."""

    def test_virtual_eval_detection_on_rankings_field(self):
        """Mock should detect virtual eval prompts with rankings field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Rank candidates.\n"
            "## Output Fields\n"
            "- `rankings`: ordered indices\n"
            "- `reasoning`: why this order"
        )
        
        result = adapter.generate_structured(prompt, VirtualEvalResult)
        assert isinstance(result, VirtualEvalResult)
        assert isinstance(result.rankings, list)
        assert isinstance(result.selected_indices, list)
        assert isinstance(result.reasoning, str)

    def test_virtual_eval_detection_on_selected_indices_field(self):
        """Mock should detect virtual eval on selected_indices field."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Select top candidates.\n"
            "## Output Fields\n"
            "- `selected_indices`: indices to advance"
        )
        
        result = adapter.generate_structured(prompt, VirtualEvalResult)
        assert isinstance(result, VirtualEvalResult)
        assert isinstance(result.selected_indices, list)

    def test_virtual_eval_with_candidate_count(self):
        """Mock should adapt rankings based on candidate count in prompt."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Rank these 3 candidates.\n"
            "## Output Fields\n"
            "- `rankings`: ordered indices\n"
            "- `selected_indices`: top candidates"
        )
        
        result = adapter.generate_structured(prompt, VirtualEvalResult)
        # Should have 3 candidates
        assert len(result.rankings) == 3
        assert all(i in result.rankings for i in range(3))

    def test_virtual_eval_with_five_candidates(self):
        """Mock should default to 5 candidates when not specified."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        prompt = (
            "Rank candidates.\n"
            "## Output Fields\n"
            "- `rankings`: ordered indices"
        )
        
        result = adapter.generate_structured(prompt, VirtualEvalResult)
        # Should have 5 candidates by default
        assert len(result.rankings) == 5


class TestMockBackwardCompatibility:
    """Test that existing proposal/coding/feedback detection unchanged."""

    def test_proposal_detection_unchanged(self):
        """Existing proposal detection should still work."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        from llm.schemas import ProposalDraft
        
        prompt = (
            "You are a research scientist.\n"
            "## Task\nmy task\n"
            "## Output Fields\n"
            "- `summary`: proposal summary\n"
            "- `virtual_score`: score"
        )
        
        result = adapter.generate_structured(prompt, ProposalDraft)
        assert isinstance(result, ProposalDraft)
        assert result.summary != ""
        assert isinstance(result.constraints, list)

    def test_coding_detection_unchanged(self):
        """Existing coding detection should still work."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        from llm.schemas import CodeDraft
        
        prompt = (
            "You are a code expert.\n"
            "## Output Fields\n"
            "- `artifact_id`: the id\n"
            "- `description`: description"
        )
        
        result = adapter.generate_structured(prompt, CodeDraft)
        assert isinstance(result, CodeDraft)
        assert result.artifact_id == "artifact-llm"

    def test_feedback_detection_unchanged(self):
        """Existing feedback detection should still work."""
        provider = MockLLMProvider()
        adapter = LLMAdapter(provider)
        
        from llm.schemas import FeedbackDraft
        
        prompt = (
            "Provide feedback.\n"
            "## Output Fields\n"
            "- `acceptable`: is it acceptable\n"
            "- `reason`: why"
        )
        
        result = adapter.generate_structured(prompt, FeedbackDraft)
        assert isinstance(result, FeedbackDraft)
        assert isinstance(result.acceptable, bool)


class TestMockFC3JSONValidity:
    """Test that mock responses produce valid JSON parseable by schemas."""

    def test_analysis_result_from_mock_raw_json(self):
        """Mock should return valid JSON parseable by AnalysisResult.from_dict()."""
        provider = MockLLMProvider()
        prompt_with_field = "## Output Fields\n- `strengths`: list"
        raw = provider.complete(prompt_with_field)
        payload = json.loads(raw)
        result = AnalysisResult.from_dict(payload)
        assert result is not None

    def test_problem_identification_from_mock_raw_json(self):
        """Mock should return valid JSON parseable by ProblemIdentification.from_dict()."""
        provider = MockLLMProvider()
        prompt_with_field = "## Output Fields\n- `severity`: critical"
        raw = provider.complete(prompt_with_field)
        payload = json.loads(raw)
        result = ProblemIdentification.from_dict(payload)
        assert result is not None

    def test_hypothesis_formulation_from_mock_raw_json(self):
        """Mock should return valid JSON parseable by HypothesisFormulation.from_dict()."""
        provider = MockLLMProvider()
        prompt_with_field = "## Output Fields\n- `mechanism`: how it works"
        raw = provider.complete(prompt_with_field)
        payload = json.loads(raw)
        result = HypothesisFormulation.from_dict(payload)
        assert result is not None

    def test_experiment_design_from_mock_raw_json(self):
        """Mock should return valid JSON parseable by ExperimentDesign.from_dict()."""
        provider = MockLLMProvider()
        prompt_with_field = "## Output Fields\n- `implementation_steps`: the steps"
        raw = provider.complete(prompt_with_field)
        payload = json.loads(raw)
        result = ExperimentDesign.from_dict(payload)
        assert result is not None

    def test_virtual_eval_result_from_mock_raw_json(self):
        """Mock should return valid JSON parseable by VirtualEvalResult.from_dict()."""
        provider = MockLLMProvider()
        prompt_with_field = "## Output Fields\n- `rankings`: the order"
        raw = provider.complete(prompt_with_field)
        payload = json.loads(raw)
        result = VirtualEvalResult.from_dict(payload)
        assert result is not None
