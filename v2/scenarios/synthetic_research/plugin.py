from __future__ import annotations

from v2.plugins.contracts import CoderPlugin, EvaluatorPlugin, ProposerPlugin, RunnerPlugin, ScenarioBundle


class SyntheticResearchProposer:
    def propose(self, state: dict) -> dict:
        task_summary = state.get("task_summary", "")
        reference_topics = state.get("reference_topics", [])
        return {
            "summary": f"synthetic_research proposal for: {task_summary}",
            "hypothesis": f"Synthesize research on: {task_summary}",
            "reference_topics": list(reference_topics),
        }


class SyntheticResearchCoder:
    def develop(self, experiment: dict, proposal: dict) -> dict:  # noqa: ARG002
        return {
            "code": f"# synthetic_research code\nprint('Synthesizing: {proposal.get('summary', '')}')\n",
            "location": "workspace/research.py",
        }


class SyntheticResearchRunner:
    def run(self, code: dict) -> dict:
        return {
            "exit_code": 0,
            "logs": f"Executed: {code.get('location', 'unknown')}",
            "artifacts": {},
            "success": True,
        }


class SyntheticResearchEvaluator:
    def evaluate(self, experiment: dict, result: dict) -> dict:  # noqa: ARG002
        success = result.get("success", False)
        return {
            "score": 0.65 if success else 0.1,
            "decision": "continue" if success else "retry",
            "reason": "synthetic_research evaluation",
            "metrics": {"quality": 0.65 if success else 0.1},
        }


def SyntheticResearchBundle() -> ScenarioBundle:  # noqa: N802
    return ScenarioBundle(
        proposer=SyntheticResearchProposer(),
        coder=SyntheticResearchCoder(),
        runner=SyntheticResearchRunner(),
        evaluator=SyntheticResearchEvaluator(),
        name="synthetic_research",
    )


assert isinstance(SyntheticResearchProposer(), ProposerPlugin)
assert isinstance(SyntheticResearchCoder(), CoderPlugin)
assert isinstance(SyntheticResearchRunner(), RunnerPlugin)
assert isinstance(SyntheticResearchEvaluator(), EvaluatorPlugin)
