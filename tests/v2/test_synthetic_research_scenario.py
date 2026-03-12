from v2.plugins.contracts import ScenarioBundle
from v2.scenarios.synthetic_research.plugin import SyntheticResearchBundle


def test_synthetic_research_bundle_returns_scenario_bundle() -> None:
    bundle = SyntheticResearchBundle()

    assert isinstance(bundle, ScenarioBundle)
    assert bundle.name == "synthetic_research"


def test_proposer_uses_task_summary_from_state() -> None:
    bundle = SyntheticResearchBundle()

    result = bundle.proposer.propose({"task_summary": "test topic"})

    assert "test topic" in result["summary"]


def test_proposer_uses_reference_topics_from_state() -> None:
    bundle = SyntheticResearchBundle()

    result = bundle.proposer.propose({"reference_topics": ["topic_a"]})

    assert result["reference_topics"] == ["topic_a"]


def test_runner_returns_success_result() -> None:
    bundle = SyntheticResearchBundle()

    result = bundle.runner.run({"location": "workspace/research.py"})

    assert result["success"] is True
    assert result["exit_code"] == 0


def test_evaluator_returns_higher_score_on_success() -> None:
    bundle = SyntheticResearchBundle()

    success_result = bundle.evaluator.evaluate({}, {"success": True})
    failure_result = bundle.evaluator.evaluate({}, {"success": False})

    assert success_result["score"] > failure_result["score"]
