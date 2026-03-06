"""Plugin contracts for scenario-extensible loop execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from data_models import (
    CodeArtifact,
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    Score,
)
from service_contracts import StepOverrideConfig


@dataclass
class ScenarioContext:
    """Scenario-scoped runtime context."""

    run_id: str
    scenario_name: str
    input_payload: Dict[str, Any]
    task_summary: str = ""
    step_config: StepOverrideConfig = field(default_factory=StepOverrideConfig)


@runtime_checkable
class ScenarioPlugin(Protocol):
    """Builds scenario context from run metadata and input payload."""

    def build_context(self, run_session: RunSession, input_payload: Dict[str, Any]) -> ScenarioContext:
        ...


@runtime_checkable
class ProposalEngine(Protocol):
    """Generates proposals from loop state and memory context."""

    def propose(
        self,
        task_summary: str,
        context: ContextPack,
        parent_ids: List[str],
        plan: Plan,
        scenario: ScenarioContext,
    ) -> Proposal:
        ...


@runtime_checkable
class ExperimentGenerator(Protocol):
    """Converts proposal output into an executable experiment node."""

    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids: List[str],
    ) -> ExperimentNode:
        ...


@runtime_checkable
class Coder(Protocol):
    """Turns experiment definition into runnable code artifact."""

    def develop(
        self,
        experiment: ExperimentNode,
        proposal: Proposal,
        scenario: ScenarioContext,
    ) -> CodeArtifact:
        ...


@runtime_checkable
class Runner(Protocol):
    """Executes a code artifact and returns runtime result."""

    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        ...


@runtime_checkable
class FeedbackAnalyzer(Protocol):
    """Summarizes run outputs into a normalized feedback record."""

    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Optional[Score] = None,
    ) -> FeedbackRecord:
        ...


@dataclass
class PluginBundle:
    """Complete plugin bundle required by the loop engine."""

    scenario_name: str
    scenario_plugin: ScenarioPlugin
    proposal_engine: ProposalEngine
    experiment_generator: ExperimentGenerator
    coder: Coder
    runner: Runner
    feedback_analyzer: FeedbackAnalyzer
    default_step_overrides: StepOverrideConfig = field(default_factory=StepOverrideConfig)
