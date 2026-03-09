"""Prompt-Schema alignment tests.

Catches mock-reality divergence: MockLLMProvider returns correct schema keys,
but a real LLM follows the prompt's Output Fields names. If they disagree,
real LLM calls silently produce empty/default objects.
"""

import dataclasses
import re

from llm.prompts import (
    reasoning_analysis_prompt,
    reasoning_design_prompt,
    reasoning_hypothesize_prompt,
    reasoning_identify_prompt,
    virtual_eval_prompt,
)
from llm.schemas import (
    AnalysisResult,
    ExperimentDesign,
    HypothesisFormulation,
    ProblemIdentification,
    VirtualEvalResult,
)


def _extract_output_field_names(prompt_text: str) -> list[str]:
    # regex: everything after "## Output Fields\n" until next "## " or end of string
    match = re.search(r"## Output Fields\s*\n(.*?)(?:\n##|\Z)", prompt_text, re.DOTALL)
    if not match:
        return []
    section = match.group(1)
    # regex: backtick-quoted identifiers like `field_name`
    return re.findall(r"`(\w+)`", section)


def _get_schema_field_names(schema_cls: type) -> list[str]:
    assert dataclasses.is_dataclass(schema_cls), f"{schema_cls} is not a dataclass"
    return [f.name for f in dataclasses.fields(schema_cls)]


def _assert_alignment(prompt_text: str, schema_cls: type, prompt_name: str) -> None:
    prompt_fields = set(_extract_output_field_names(prompt_text))
    schema_fields = set(_get_schema_field_names(schema_cls))

    missing_from_prompt = schema_fields - prompt_fields
    extra_in_prompt = prompt_fields - schema_fields

    errors = []
    if missing_from_prompt:
        errors.append(f"Schema fields NOT in prompt: {sorted(missing_from_prompt)}")
    if extra_in_prompt:
        errors.append(f"Prompt fields NOT in schema: {sorted(extra_in_prompt)}")

    assert not errors, (
        f"\nMISALIGNMENT: {prompt_name} <-> {schema_cls.__name__}\n"
        f"Prompt: {sorted(prompt_fields)}\n"
        f"Schema: {sorted(schema_fields)}\n" + "\n".join(errors)
    )


class TestPromptSchemaAlignment:
    def test_analysis_prompt_matches_analysis_result(self):
        prompt = reasoning_analysis_prompt(
            task_summary="Test task",
            scenario_name="test",
            iteration=1,
            previous_results=["r1"],
            current_scores=[0.5],
        )
        _assert_alignment(prompt, AnalysisResult, "reasoning_analysis_prompt")

    def test_identify_prompt_matches_problem_identification(self):
        prompt = reasoning_identify_prompt(
            analysis_text="Some analysis",
            task_summary="Test task",
            scenario_name="test",
        )
        _assert_alignment(prompt, ProblemIdentification, "reasoning_identify_prompt")

    def test_hypothesize_prompt_matches_hypothesis_formulation(self):
        prompt = reasoning_hypothesize_prompt(
            analysis_text="Some analysis",
            problem_text="Some problem",
            task_summary="Test task",
            scenario_name="test",
        )
        _assert_alignment(prompt, HypothesisFormulation, "reasoning_hypothesize_prompt")

    def test_design_prompt_matches_experiment_design(self):
        prompt = reasoning_design_prompt(
            analysis_text="Some analysis",
            problem_text="Some problem",
            hypothesis_text="Some hypothesis",
            task_summary="Test task",
            scenario_name="test",
            iteration=0,
        )
        _assert_alignment(prompt, ExperimentDesign, "reasoning_design_prompt")

    def test_virtual_eval_prompt_matches_virtual_eval_result(self):
        prompt = virtual_eval_prompt(
            candidates=[{"summary": "c1"}, {"summary": "c2"}],
            task_summary="Test task",
            scenario_name="test",
            evaluation_criteria="accuracy",
        )
        _assert_alignment(prompt, VirtualEvalResult, "virtual_eval_prompt")


class TestSchemaHintAlignment:
    def test_schema_hint_covers_list_int_fields(self):
        import json

        from llm.adapter import LLMAdapter, MockLLMProvider

        adapter = LLMAdapter(MockLLMProvider())
        hint = adapter._build_schema_hint(VirtualEvalResult)
        parsed = json.loads(hint)

        assert isinstance(parsed["rankings"], list)
        assert isinstance(parsed["selected_indices"], list)
        assert parsed["rankings"] == [0]
        assert parsed["selected_indices"] == [0]

    def test_schema_hint_covers_all_fc3_schemas(self):
        import json

        from llm.adapter import LLMAdapter, MockLLMProvider

        adapter = LLMAdapter(MockLLMProvider())

        for schema_cls in [
            AnalysisResult,
            ProblemIdentification,
            HypothesisFormulation,
            ExperimentDesign,
            VirtualEvalResult,
        ]:
            hint = adapter._build_schema_hint(schema_cls)
            assert hint, f"Empty hint for {schema_cls.__name__}"
            parsed = json.loads(hint)
            schema_fields = {f.name for f in dataclasses.fields(schema_cls)}
            hint_fields = set(parsed.keys())
            assert schema_fields == hint_fields, f"{schema_cls.__name__}: hint {hint_fields} != schema {schema_fields}"
