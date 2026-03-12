from __future__ import annotations

from v2.plugins.contracts import CoderPlugin, EvaluatorPlugin, ProposerPlugin, RunnerPlugin, ScenarioBundle


class QuantProposer:
    def __init__(self, data_source: str | None = None) -> None:
        self._data_source = data_source

    def propose(self, state: dict) -> dict:
        task_summary = state.get("task_summary", "")
        data_source = self._data_source or state.get("data_source", "")
        return {
            "summary": f"quant proposal for: {task_summary}",
            "hypothesis": f"Mine alpha factor from OHLCV data: {task_summary}",
            "data_source": data_source,
        }


class QuantCoder:
    def develop(self, experiment: dict, proposal: dict) -> dict:
        _ = experiment
        return {
            "code": f"# quant code\nprint('Computing factor: {proposal.get('summary', '')}')\n",
            "location": "workspace/factor.py",
        }


class QuantRunner:
    def run(self, code: dict) -> dict:
        return {
            "exit_code": 0,
            "logs": f"Executed: {code.get('location', 'unknown')}",
            "artifacts": {},
            "success": True,
        }


class QuantEvaluator:
    def evaluate(self, experiment: dict, result: dict) -> dict:
        _ = experiment
        success = result.get("success", False)
        return {
            "score": 0.6 if success else 0.1,
            "decision": "continue" if success else "retry",
            "reason": "quant evaluation",
            "metrics": {"ic": 0.6 if success else 0.1, "sharpe": 1.2 if success else 0.0},
        }


def QuantBundle(data_source: str | None = None) -> ScenarioBundle:  # noqa: N802
    return ScenarioBundle(
        proposer=QuantProposer(data_source=data_source),
        coder=QuantCoder(),
        runner=QuantRunner(),
        evaluator=QuantEvaluator(),
        name="quant",
    )


assert isinstance(QuantProposer(), ProposerPlugin)
assert isinstance(QuantCoder(), CoderPlugin)
assert isinstance(QuantRunner(), RunnerPlugin)
assert isinstance(QuantEvaluator(), EvaluatorPlugin)
