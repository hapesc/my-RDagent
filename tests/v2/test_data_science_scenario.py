from v2.plugins.contracts import ScenarioBundle
from v2.plugins.registry import PluginRegistry
from v2.scenarios.data_science.plugin import DataScienceBundle


def test_data_science_bundle_is_a_scenario_bundle() -> None:
    bundle = DataScienceBundle()

    assert isinstance(bundle, ScenarioBundle)


def test_data_science_bundle_has_all_four_plugins() -> None:
    bundle = DataScienceBundle()

    assert hasattr(bundle, "proposer")
    assert hasattr(bundle, "coder")
    assert hasattr(bundle, "runner")
    assert hasattr(bundle, "evaluator")


def test_data_science_bundle_can_register_and_retrieve() -> None:
    bundle = DataScienceBundle()
    registry = PluginRegistry()

    registry.register("data_science", bundle)

    assert registry.get("data_science") is bundle


def test_data_science_proposer_returns_proposal_dict() -> None:
    bundle = DataScienceBundle()

    result = bundle.proposer.propose({"task_summary": "classify iris", "metrics": []})

    assert "summary" in result
    assert "hypothesis" in result


def test_data_science_evaluator_returns_continue_for_successful_run() -> None:
    bundle = DataScienceBundle()

    result = bundle.evaluator.evaluate({}, {"success": True})

    assert result["decision"] == "continue"
    assert result["score"] == 0.7
