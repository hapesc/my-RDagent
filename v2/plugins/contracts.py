"""V2 plugin protocol contracts — pure Python Protocol interfaces for LangGraph state machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProposerPlugin(Protocol):
    """Protocol for generating proposals from loop state."""

    def propose(self, state: dict) -> dict:
        """Generate a proposal from the current state.

        Args:
            state: MainState dict containing loop context.

        Returns:
            dict: Proposal dict with keys like 'summary', 'constraints'.
        """
        ...


@runtime_checkable
class CoderPlugin(Protocol):
    """Protocol for developing code from proposal."""

    def develop(self, experiment: dict, proposal: dict) -> dict:
        """Develop code artifact from proposal and experiment.

        Args:
            experiment: Experiment dict describing the task.
            proposal: Proposal dict from proposer.

        Returns:
            dict: Code artifact dict with keys like 'code', 'location'.
        """
        ...


@runtime_checkable
class RunnerPlugin(Protocol):
    """Protocol for executing code artifacts."""

    def run(self, code: dict) -> dict:
        """Execute a code artifact.

        Args:
            code: Code artifact dict from coder.

        Returns:
            dict: Execution result dict with keys like 'exit_code', 'logs', 'artifacts'.
        """
        ...


@runtime_checkable
class EvaluatorPlugin(Protocol):
    """Protocol for evaluating execution results and providing feedback."""

    def evaluate(self, experiment: dict, result: dict) -> dict:
        """Evaluate execution result and provide feedback.

        Args:
            experiment: Experiment dict describing the task.
            result: Execution result dict from runner.

        Returns:
            dict: Feedback/score dict with keys like 'decision', 'reason', 'score'.
        """
        ...


@dataclass
class ScenarioBundle:
    """Bundle of four plugin implementations for a scenario."""

    proposer: ProposerPlugin
    coder: CoderPlugin
    runner: RunnerPlugin
    evaluator: EvaluatorPlugin
    name: str = ""
