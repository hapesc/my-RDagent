from v2.plugins.contracts import ScenarioBundle
from v2.scenarios.quant.plugin import QuantBundle, QuantEvaluator, QuantProposer, QuantRunner


def test_quant_bundle_returns_scenario_bundle() -> None:
    bundle = QuantBundle()

    assert isinstance(bundle, ScenarioBundle)
    assert bundle.name == "quant"


def test_proposer_uses_task_summary_from_state() -> None:
    proposer = QuantProposer()

    result = proposer.propose({"task_summary": "momentum factor"})

    assert "momentum factor" in result["summary"]


def test_proposer_uses_data_source_from_constructor() -> None:
    proposer = QuantProposer(data_source="/data/ohlcv.csv")

    result = proposer.propose({})

    assert result["data_source"] == "/data/ohlcv.csv"


def test_runner_returns_success_result() -> None:
    runner = QuantRunner()

    result = runner.run({"location": "workspace/factor.py"})

    assert result["success"] is True
    assert result["exit_code"] == 0


def test_evaluator_returns_ic_and_sharpe_metrics() -> None:
    evaluator = QuantEvaluator()

    result = evaluator.evaluate({}, {"success": True})

    assert "ic" in result["metrics"]
    assert "sharpe" in result["metrics"]
