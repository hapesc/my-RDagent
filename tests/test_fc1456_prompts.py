"""Tests for planning_strategy_prompt, hypothesis_modification_prompt, and coding_prompt."""

from llm.prompts import coding_prompt, hypothesis_modification_prompt, planning_strategy_prompt


class TestPlanningStrategyPrompt:
    """Tests for planning_strategy_prompt function."""

    def test_planning_strategy_prompt_returns_non_empty_string(self):
        """Test that planning_strategy_prompt returns a non-empty string."""
        result = planning_strategy_prompt(
            task_summary="Test optimization task",
            scenario_name="test_scenario",
            progress=0.5,
            stage="exploration",
            iteration=1,
            history_summary={"best_score": "0.85", "last_attempt": "baseline"},
            budget_remaining=100.0,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_planning_strategy_prompt_contains_all_schema_fields(self):
        """Test that prompt mentions all PlanningStrategy schema fields."""
        result = planning_strategy_prompt(
            task_summary="Test optimization task",
            scenario_name="test_scenario",
            progress=0.5,
            stage="exploration",
            iteration=1,
            history_summary={"best_score": "0.85", "last_attempt": "baseline"},
            budget_remaining=100.0,
        )
        # Check for all required field names
        assert "strategy_name" in result
        assert "method_selection" in result
        assert "exploration_weight" in result
        assert "reasoning" in result

    def test_planning_strategy_prompt_includes_context_info(self):
        """Test that prompt includes progress and stage information."""
        result = planning_strategy_prompt(
            task_summary="Test optimization task",
            scenario_name="test_scenario",
            progress=0.5,
            stage="exploration",
            iteration=2,
            history_summary={"best_score": "0.85"},
            budget_remaining=100.0,
        )
        # Should include stage and progress indicators
        assert "exploration" in result or "stage" in result.lower()
        assert "progress" in result.lower() or "0.5" in result or "50" in result

    def test_planning_strategy_prompt_uses_parameters(self):
        """Test that prompt actually uses the input parameters."""
        task = "unique_task_xyz"
        scenario = "unique_scenario_abc"
        result = planning_strategy_prompt(
            task_summary=task,
            scenario_name=scenario,
            progress=0.75,
            stage="refinement",
            iteration=3,
            history_summary={"test": "data"},
            budget_remaining=50.0,
        )
        # Parameters should appear in result
        assert task in result
        assert scenario in result


class TestHypothesisModificationPrompt:
    """Tests for hypothesis_modification_prompt function."""

    def test_hypothesis_modification_prompt_returns_non_empty_string(self):
        """Test that hypothesis_modification_prompt returns a non-empty string."""
        result = hypothesis_modification_prompt(
            source_hypothesis="Current hypothesis text",
            action="modify_parameters",
            context_items=["result1", "result2"],
            task_summary="Test task",
            scenario_name="test_scenario",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hypothesis_modification_prompt_contains_all_schema_fields(self):
        """Test that prompt mentions all HypothesisModification schema fields."""
        result = hypothesis_modification_prompt(
            source_hypothesis="Current hypothesis text",
            action="modify_parameters",
            context_items=["result1", "result2"],
            task_summary="Test task",
            scenario_name="test_scenario",
        )
        # Check for all required field names
        assert "modified_hypothesis" in result
        assert "modification_type" in result
        assert "source_hypothesis" in result
        assert "reasoning" in result

    def test_hypothesis_modification_prompt_includes_action_parameter(self):
        """Test that prompt includes the action parameter in output."""
        action = "refine_approach"
        result = hypothesis_modification_prompt(
            source_hypothesis="Current hypothesis text",
            action=action,
            context_items=["result1"],
            task_summary="Test task",
            scenario_name="test_scenario",
        )
        # Action should be mentioned in prompt
        assert "action" in result.lower() or action in result

    def test_hypothesis_modification_prompt_uses_parameters(self):
        """Test that prompt actually uses the input parameters."""
        hyp = "unique_hypothesis_xyz"
        task = "unique_task_abc"
        scenario = "unique_scenario_def"
        result = hypothesis_modification_prompt(
            source_hypothesis=hyp,
            action="modify",
            context_items=["ctx1", "ctx2"],
            task_summary=task,
            scenario_name=scenario,
        )
        # Parameters should appear in result
        assert hyp in result
        assert task in result
        assert scenario in result


class TestCodingPrompt:
    def test_coding_prompt_includes_few_shot_when_available(self):
        prompt = coding_prompt(
            proposal_summary="classify iris dataset",
            constraints=["overfitting risk"],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert "## Example" in prompt or "## Reference Implementation" in prompt

    def test_coding_prompt_includes_output_format_spec(self):
        prompt = coding_prompt(
            proposal_summary="test",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert "metrics.json" in prompt or "output format" in prompt.lower()

    def test_coding_prompt_includes_no_placeholder_instruction(self):
        prompt = coding_prompt(
            proposal_summary="test",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert "placeholder" in prompt.lower() or "template" in prompt.lower()

    def test_coding_prompt_includes_constraint_block(self):
        prompt = coding_prompt(
            proposal_summary="test",
            constraints=["no file I/O"],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="quant",
        )
        assert "no file I/O" in prompt

    def test_coding_prompt_requires_raw_artifact_output(self):
        prompt = coding_prompt(
            proposal_summary="build a pipeline",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert "return only one fenced python code block" in prompt.lower()
        assert "no json wrapper" in prompt.lower()

    def test_coding_prompt_requires_exact_synthetic_sections(self):
        prompt = coding_prompt(
            proposal_summary="compare optimizers",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="synthetic_research",
        )
        assert "## Findings" in prompt
        assert "## Methodology" in prompt
        assert "## Conclusion" in prompt

    def test_coding_prompt_discourages_json_wrapper_for_data_science(self):
        prompt = coding_prompt(
            proposal_summary="build a regression pipeline",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert "return only one fenced python code block" in prompt.lower()
        assert "no json wrapper" in prompt.lower()

    def test_coding_prompt_discourages_json_wrapper_for_synthetic_report(self):
        prompt = coding_prompt(
            proposal_summary="analyze temperature trends",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="synthetic_research",
        )
        assert "return only markdown" in prompt.lower()
        assert "no json wrapper" in prompt.lower()

    def test_coding_prompt_stays_compact_enough_for_single_round_codegen(self):
        prompt = coding_prompt(
            proposal_summary="build a feature engineering pipeline",
            constraints=[],
            experiment_node_id="node-1",
            workspace_ref="/tmp/ws",
            scenario_name="data_science",
        )
        assert len(prompt) < 1800
