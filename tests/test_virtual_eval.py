import json

from core.reasoning.virtual_eval import VirtualEvaluator
from llm.adapter import LLMAdapter, MockLLMProvider
from service_contracts import ModelSelectorConfig


class CallCountingProvider:
    def __init__(self) -> None:
        self._inner = MockLLMProvider()
        self.call_count = 0
        self.prompts = []
        self.model_configs = []

    def complete(self, prompt, model_config=None):
        self.call_count += 1
        self.prompts.append(prompt)
        self.model_configs.append(model_config)
        return self._inner.complete(prompt, model_config)


class InvalidIndicesProvider:
    def __init__(self) -> None:
        self._inner = MockLLMProvider()
        self.call_count = 0

    def complete(self, prompt, model_config=None):
        self.call_count += 1
        if "`rankings`" in prompt and "`selected_indices`" in prompt:
            return json.dumps(
                {
                    "rankings": [1, 0, 2],
                    "reasoning": "fallback-to-rankings",
                    "selected_indices": [999, -7],
                }
            )
        return self._inner.complete(prompt, model_config)


def _build_evaluator_with_counter(n_candidates=5, k_forward=2):
    provider = CallCountingProvider()
    adapter = LLMAdapter(provider)
    evaluator = VirtualEvaluator(adapter, n_candidates=n_candidates, k_forward=k_forward)
    return evaluator, provider


def test_virtual_evaluator_instantiation_defaults():
    evaluator, _ = _build_evaluator_with_counter()
    assert evaluator._n_candidates == 5
    assert evaluator._k_forward == 2


def test_evaluate_returns_exactly_k_designs_when_n_gt_k():
    evaluator, _ = _build_evaluator_with_counter(n_candidates=5, k_forward=2)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 2


def test_evaluate_returns_all_n_designs_when_n_le_k_without_ranking():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=2, k_forward=2)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 2
    assert all(design.summary.strip() for design in result)
    assert not any("`rankings`" in prompt and "`selected_indices`" in prompt for prompt in provider.prompts)


def test_n_candidates_triggers_semantic_ranking_step_when_n_exceeds_k():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=5, k_forward=2)
    evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert provider.call_count > evaluator._n_candidates
    assert any("`rankings`" in prompt and "`selected_indices`" in prompt for prompt in provider.prompts)


def test_diversify_prompt_behaviour():
    base = "optimize model"
    first = VirtualEvaluator._diversify_prompt(base, 0, 5)
    second = VirtualEvaluator._diversify_prompt(base, 1, 5)
    assert first == base
    assert "[Diversity hint:" in second
    assert "candidate 2 of 5" in second


def test_returned_designs_have_non_empty_summary_and_implementation_steps():
    evaluator, _ = _build_evaluator_with_counter(n_candidates=5, k_forward=2)
    designs = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=1,
        previous_results=["prev result"],
        current_scores=[0.2],
    )
    for design in designs:
        assert design.summary.strip() != ""
        assert len(design.implementation_steps) > 0


def test_custom_n_and_k_supported():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=3, k_forward=1)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 1
    assert any("`rankings`" in prompt and "`selected_indices`" in prompt for prompt in provider.prompts)


def test_edge_case_n1_k1_single_candidate_no_ranking():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=1, k_forward=1)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 1
    assert provider.prompts
    assert not any("`rankings`" in prompt and "`selected_indices`" in prompt for prompt in provider.prompts)


def test_edge_case_n2_k2_returns_both_without_ranking():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=2, k_forward=2)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 2
    assert all(design.summary.strip() for design in result)
    assert not any("`rankings`" in prompt and "`selected_indices`" in prompt for prompt in provider.prompts)


def test_invalid_indices_from_llm_falls_back_gracefully():
    provider = InvalidIndicesProvider()
    adapter = LLMAdapter(provider)
    evaluator = VirtualEvaluator(adapter, n_candidates=3, k_forward=2)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
    )
    assert len(result) == 2
    assert all(design.summary.strip() for design in result)


def test_model_config_propagates_to_pipeline_and_ranking_calls():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=3, k_forward=1)
    model_config = ModelSelectorConfig(
        provider="mock-provider",
        model="mock-model",
        temperature=0.2,
        max_tokens=256,
    )
    evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=2,
        previous_results=["r1"],
        current_scores=[0.4],
        model_config=model_config,
    )
    assert provider.model_configs
    assert len(provider.model_configs) == provider.call_count
    assert all(cfg is model_config for cfg in provider.model_configs)


def test_call_time_n_k_override_is_applied_for_generation_and_ranking():
    evaluator, provider = _build_evaluator_with_counter(n_candidates=5, k_forward=2)
    result = evaluator.evaluate(
        task_summary="improve baseline",
        scenario_name="data_science",
        iteration=0,
        previous_results=[],
        current_scores=[],
        n_candidates=1,
        k_forward=1,
    )

    assert len(result) == 1
    assert provider.call_count == 4
