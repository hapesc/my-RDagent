from __future__ import annotations

from v2.plugins.contracts import CoderPlugin, EvaluatorPlugin, ProposerPlugin, RunnerPlugin, ScenarioBundle


class DataScienceProposer:
    def propose(self, state: dict) -> dict:
        task_summary = state.get("task_summary", "")
        history = state.get("metrics", [])
        return {
            "summary": f"data_science proposal for: {task_summary}",
            "hypothesis": f"Improve model performance on: {task_summary}",
            "history_count": len(history),
        }


class DataScienceCoder:
    def develop(self, experiment: dict, proposal: dict) -> dict:
        return {
            "code": f"# data_science code\nprint('Running experiment: {proposal.get('summary', '')}')\n",
            "location": "workspace/model.py",
        }


class DataScienceRunner:
    def run(self, code: dict) -> dict:
        return {
            "exit_code": 0,
            "logs": f"Executed: {code.get('location', 'unknown')}",
            "artifacts": {},
            "success": True,
        }


class DataScienceEvaluator:
    def evaluate(self, experiment: dict, result: dict) -> dict:
        success = result.get("success", False)
        return {
            "score": 0.7 if success else 0.1,
            "decision": "continue" if success else "retry",
            "reason": "data_science evaluation",
            "metrics": {"accuracy": 0.7 if success else 0.1},
        }


def DataScienceBundle() -> ScenarioBundle:
    return ScenarioBundle(
        proposer=DataScienceProposer(),
        coder=DataScienceCoder(),
        runner=DataScienceRunner(),
        evaluator=DataScienceEvaluator(),
        name="data_science",
    )


assert isinstance(DataScienceProposer(), ProposerPlugin)
assert isinstance(DataScienceCoder(), CoderPlugin)
assert isinstance(DataScienceRunner(), RunnerPlugin)
assert isinstance(DataScienceEvaluator(), EvaluatorPlugin)
