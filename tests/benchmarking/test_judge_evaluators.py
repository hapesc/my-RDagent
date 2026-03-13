from __future__ import annotations

from benchmarking.evaluators.judge import (
    JudgeScore,
    create_feedback_actionability_judge,
    create_hypothesis_feasibility_judge,
    create_hypothesis_specificity_judge,
    create_report_coherence_judge,
    create_report_depth_judge,
    create_report_faithfulness_judge,
)


class FakeJudgeAdapter:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.payload = payload or {"score": 0.8, "reasoning": "looks good"}
        self.prompts: list[str] = []

    def generate_structured(self, prompt: str, schema_cls, model_config=None):
        _ = model_config
        self.prompts.append(prompt)
        return schema_cls.from_dict(dict(self.payload))


class ExplodingJudgeAdapter:
    def generate_structured(self, prompt: str, schema_cls, model_config=None):
        _ = (prompt, schema_cls, model_config)
        raise RuntimeError("judge adapter failure")


def test_judge_factories_return_normalized_scores() -> None:
    adapter = FakeJudgeAdapter()
    evaluators = [
        create_hypothesis_specificity_judge(adapter),
        create_hypothesis_feasibility_judge(adapter, scenario="quant"),
        create_feedback_actionability_judge(adapter),
        create_report_depth_judge(adapter),
        create_report_coherence_judge(adapter),
        create_report_faithfulness_judge(adapter),
    ]

    for evaluator in evaluators:
        result = evaluator(
            inputs={"task_summary": "test task"},
            outputs={"artifact": "output"},
            reference_outputs={"reference_facts": ["fact-1"]},
        )
        assert result["score"] == 0.8
        assert result["reasoning"] == "looks good"


def test_judge_handles_empty_input_safely() -> None:
    adapter = FakeJudgeAdapter()
    evaluator = create_report_faithfulness_judge(adapter)

    result = evaluator(inputs={}, outputs={}, reference_outputs={})

    assert result["score"] == 0.0
    assert "empty" in result["reasoning"].lower()


def test_feasibility_judge_uses_scenario_specific_constraints() -> None:
    adapter = FakeJudgeAdapter()
    evaluator = create_hypothesis_feasibility_judge(adapter, scenario="data_science")

    result = evaluator(
        inputs={"task_summary": "train a classifier"},
        outputs={"hypothesis": "use sklearn random forest"},
        reference_outputs={},
    )

    assert result["score"] == 0.8
    assert any("metrics.json" in prompt for prompt in adapter.prompts)


def test_judge_score_from_dict_round_trip() -> None:
    score = JudgeScore.from_dict({"score": 0.5, "reasoning": "ok"})
    assert score.score == 0.5
    assert score.reasoning == "ok"


def test_judge_score_requires_required_fields() -> None:
    try:
        JudgeScore.from_dict({"reasoning": "missing score"})
    except ValueError as exc:
        assert "score" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing score")


def test_judge_propagates_adapter_failures() -> None:
    evaluator = create_report_depth_judge(ExplodingJudgeAdapter())

    try:
        evaluator(
            inputs={"task_summary": "task"},
            outputs={"artifact": "output"},
            reference_outputs={},
        )
    except RuntimeError as exc:
        assert "judge adapter failure" in str(exc)
    else:
        raise AssertionError("expected adapter failure to propagate")
