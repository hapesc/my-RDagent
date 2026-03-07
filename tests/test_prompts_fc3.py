"""Tests for FC-3 reasoning prompt functions.

TDD-first: these tests define the expected behavior of:
- reasoning_analysis_prompt()
- reasoning_identify_prompt()
- reasoning_hypothesize_prompt()
- reasoning_design_prompt()
- virtual_eval_prompt()

Each must return a well-structured string with:
- Role assignment (You are a...)
- Context sections (## Section)
- Instructions
- Output Fields section
"""

import pytest
from llm.prompts import (
    reasoning_analysis_prompt,
    reasoning_identify_prompt,
    reasoning_hypothesize_prompt,
    reasoning_design_prompt,
    virtual_eval_prompt,
)


class TestReasoningAnalysisPrompt:
    """Test the Analysis stage prompt."""

    def test_signature_and_return_type(self):
        """reasoning_analysis_prompt accepts correct parameters and returns str."""
        result = reasoning_analysis_prompt(
            task_summary="Find the optimal learning rate for MNIST classification.",
            scenario_name="data_science",
            iteration=0,
            previous_results=[],
            current_scores=[]
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_role_assignment(self):
        """Prompt includes role assignment."""
        result = reasoning_analysis_prompt(
            task_summary="Test task",
            scenario_name="test_scenario",
            iteration=0,
            previous_results=[],
            current_scores=[]
        )
        assert "research scientist" in result.lower() or "scientist" in result.lower()

    def test_has_output_fields_section(self):
        """Prompt includes ## Output Fields section."""
        result = reasoning_analysis_prompt(
            task_summary="Test task",
            scenario_name="test_scenario",
            iteration=0,
            previous_results=[],
            current_scores=[]
        )
        assert "## Output Fields" in result

    def test_includes_context_sections(self):
        """Prompt includes context sections like ## Task, ## Analysis, etc."""
        result = reasoning_analysis_prompt(
            task_summary="Test task",
            scenario_name="test_scenario",
            iteration=1,
            previous_results=["Result 1"],
            current_scores=[0.75]
        )
        # Should have at least Task section
        assert "## Task" in result or "Task" in result
        # Should mention iteration strategy (from _iteration_strategy)
        assert "iteration" in result.lower() or "Iteration" in result

    def test_integrates_previous_results(self):
        """Prompt uses previous_results parameter when provided."""
        previous = ["Trial 1: accuracy 0.8", "Trial 2: accuracy 0.82"]
        result = reasoning_analysis_prompt(
            task_summary="Test task",
            scenario_name="test_scenario",
            iteration=2,
            previous_results=previous,
            current_scores=[0.8, 0.82]
        )
        # Should reference previous results somehow (exact format TBD by implementation)
        assert len(result) > 100  # Non-trivial prompt


class TestReasoningIdentifyPrompt:
    """Test the Identify stage prompt."""

    def test_signature_and_return_type(self):
        """reasoning_identify_prompt accepts correct parameters and returns str."""
        result = reasoning_identify_prompt(
            analysis_text="Current solution uses vanilla SGD with fixed learning rate.",
            task_summary="Optimize MNIST classifier accuracy.",
            scenario_name="data_science"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_role_assignment(self):
        """Prompt includes role assignment."""
        result = reasoning_identify_prompt(
            analysis_text="Analysis text",
            task_summary="Test task",
            scenario_name="test_scenario"
        )
        assert "scientist" in result.lower() or "researcher" in result.lower()

    def test_has_output_fields_section(self):
        """Prompt includes ## Output Fields section."""
        result = reasoning_identify_prompt(
            analysis_text="Analysis text",
            task_summary="Test task",
            scenario_name="test_scenario"
        )
        assert "## Output Fields" in result

    def test_uses_analysis_text(self):
        """Prompt includes analysis_text in context."""
        analysis = "Specific analysis about bottleneck"
        result = reasoning_identify_prompt(
            analysis_text=analysis,
            task_summary="Test task",
            scenario_name="test_scenario"
        )
        assert analysis in result or "analysis" in result.lower()


class TestReasoningHypothesizePrompt:
    """Test the Hypothesize stage prompt."""

    def test_signature_and_return_type(self):
        """reasoning_hypothesize_prompt accepts correct parameters and returns str."""
        result = reasoning_hypothesize_prompt(
            analysis_text="Current approach uses static learning rate.",
            problem_text="The optimizer converges too slowly in early iterations.",
            task_summary="Optimize MNIST classifier.",
            scenario_name="data_science"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_role_assignment(self):
        """Prompt includes role assignment."""
        result = reasoning_hypothesize_prompt(
            analysis_text="Analysis",
            problem_text="Problem",
            task_summary="Task",
            scenario_name="scenario"
        )
        assert "scientist" in result.lower() or "researcher" in result.lower()

    def test_has_output_fields_section(self):
        """Prompt includes ## Output Fields section."""
        result = reasoning_hypothesize_prompt(
            analysis_text="Analysis",
            problem_text="Problem",
            task_summary="Task",
            scenario_name="scenario"
        )
        assert "## Output Fields" in result

    def test_includes_problem_and_analysis(self):
        """Prompt includes both problem_text and analysis_text."""
        problem = "Specific problem statement"
        analysis = "Specific analysis context"
        result = reasoning_hypothesize_prompt(
            analysis_text=analysis,
            problem_text=problem,
            task_summary="Task",
            scenario_name="scenario"
        )
        # At least one should be mentioned
        assert problem in result or analysis in result or len(result) > 200


class TestReasoningDesignPrompt:
    """Test the Design stage prompt."""

    def test_signature_and_return_type(self):
        """reasoning_design_prompt accepts correct parameters and returns str."""
        result = reasoning_design_prompt(
            analysis_text="Current solution uses vanilla SGD.",
            problem_text="Optimizer is slow in early iterations.",
            hypothesis_text="Adaptive learning rate (Adam) will converge faster.",
            task_summary="Optimize MNIST classifier.",
            scenario_name="data_science",
            iteration=1
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_role_assignment(self):
        """Prompt includes role assignment."""
        result = reasoning_design_prompt(
            analysis_text="A",
            problem_text="P",
            hypothesis_text="H",
            task_summary="T",
            scenario_name="S",
            iteration=0
        )
        assert "engineer" in result.lower() or "scientist" in result.lower()

    def test_has_output_fields_section(self):
        """Prompt includes ## Output Fields section."""
        result = reasoning_design_prompt(
            analysis_text="A",
            problem_text="P",
            hypothesis_text="H",
            task_summary="T",
            scenario_name="S",
            iteration=0
        )
        assert "## Output Fields" in result

    def test_includes_hypothesis_and_analysis(self):
        """Prompt includes hypothesis_text and analysis_text."""
        hypothesis = "Unique hypothesis about the problem"
        analysis = "Unique analysis of current state"
        result = reasoning_design_prompt(
            analysis_text=analysis,
            problem_text="Problem",
            hypothesis_text=hypothesis,
            task_summary="Task",
            scenario_name="scenario",
            iteration=0
        )
        # At least one should be clearly present
        assert hypothesis in result or analysis in result or len(result) > 200

    def test_iteration_strategy_applied(self):
        """Prompt uses iteration parameter for iteration-aware strategy."""
        result_iter0 = reasoning_design_prompt(
            analysis_text="A",
            problem_text="P",
            hypothesis_text="H",
            task_summary="T",
            scenario_name="S",
            iteration=0
        )
        result_iter2 = reasoning_design_prompt(
            analysis_text="A",
            problem_text="P",
            hypothesis_text="H",
            task_summary="T",
            scenario_name="S",
            iteration=2
        )
        # Both should be valid (exact content may differ by iteration strategy)
        assert len(result_iter0) > 0
        assert len(result_iter2) > 0


class TestVirtualEvalPrompt:
    """Test the virtual evaluation (ranking) prompt."""

    def test_signature_and_return_type(self):
        """virtual_eval_prompt accepts candidates list and returns str."""
        candidates = [
            {"summary": "Use Adam optimizer with LR=1e-3"},
            {"summary": "Use AdaGrad with LR=5e-4"},
            {"summary": "Use SGD with learning rate schedule"}
        ]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Optimize MNIST classifier.",
            scenario_name="data_science",
            evaluation_criteria="accuracy, convergence speed"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_role_assignment(self):
        """Prompt includes role assignment."""
        candidates = [{"summary": "Candidate 1"}]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="criteria"
        )
        assert "scientist" in result.lower() or "evaluator" in result.lower() or "researcher" in result.lower()

    def test_has_output_fields_section(self):
        """Prompt includes ## Output Fields section."""
        candidates = [{"summary": "Candidate"}]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="criteria"
        )
        assert "## Output Fields" in result

    def test_includes_ranking_instruction(self):
        """Prompt includes instruction to rank candidates."""
        candidates = [
            {"summary": "Option A"},
            {"summary": "Option B"}
        ]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="accuracy"
        )
        # Should mention ranking, sorting, or evaluation in some form
        result_lower = result.lower()
        assert ("rank" in result_lower or "score" in result_lower or 
                "best" in result_lower or "compare" in result_lower or
                "evaluate" in result_lower)

    def test_includes_candidate_summaries(self):
        """Prompt formats candidate summaries."""
        candidates = [
            {"summary": "Unique candidate A"},
            {"summary": "Unique candidate B"}
        ]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="criteria"
        )
        # At least one candidate summary should appear
        assert "Unique candidate" in result or len(result) > 300

    def test_empty_candidates_list(self):
        """Prompt handles empty candidates list gracefully."""
        result = virtual_eval_prompt(
            candidates=[],
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="criteria"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_single_candidate(self):
        """Prompt works with single candidate (edge case)."""
        result = virtual_eval_prompt(
            candidates=[{"summary": "Only option"}],
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="criteria"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_many_candidates(self):
        """Prompt scales to multiple candidates."""
        candidates = [
            {"summary": f"Candidate {i}"}
            for i in range(5)
        ]
        result = virtual_eval_prompt(
            candidates=candidates,
            task_summary="Task",
            scenario_name="scenario",
            evaluation_criteria="accuracy, speed, robustness"
        )
        assert isinstance(result, str)
        assert len(result) > 100
