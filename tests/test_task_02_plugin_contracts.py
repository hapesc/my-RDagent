"""Task-02 contract tests for plugin protocols and registry."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from data_models import ContextPack, LoopState, Plan, RunSession, RunStatus, Score, StopConditions
from plugins import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    ProposalEngine,
    Runner,
    ScenarioPlugin,
    build_default_registry,
)
from plugins.examples import build_minimal_data_science_bundle
from plugins.registry import PluginRegistry
from tests._llm_test_utils import make_mock_llm_adapter


class PluginContractTests(unittest.TestCase):
    def test_builtin_registry_loads_data_science_bundle(self) -> None:
        registry = build_default_registry(llm_adapter=make_mock_llm_adapter())
        self.assertIn("data_science", registry.list_scenarios())

        bundle = registry.create_bundle("data_science")
        self.assertIsInstance(bundle.scenario_plugin, ScenarioPlugin)
        self.assertIsInstance(bundle.proposal_engine, ProposalEngine)
        self.assertIsInstance(bundle.experiment_generator, ExperimentGenerator)
        self.assertIsInstance(bundle.coder, Coder)
        self.assertIsInstance(bundle.runner, Runner)
        self.assertIsInstance(bundle.feedback_analyzer, FeedbackAnalyzer)

    def test_registry_rejects_duplicate_and_unknown_scenario(self) -> None:
        registry = PluginRegistry()
        registry.register("data_science", build_minimal_data_science_bundle)

        with self.assertRaises(ValueError):
            registry.register("data_science", build_minimal_data_science_bundle)
        with self.assertRaises(KeyError):
            registry.create_bundle("unknown")

    def test_minimal_plugin_bundle_executes_full_chain(self) -> None:
        bundle = build_minimal_data_science_bundle()
        run_session = RunSession(
            run_id="run-test-02",
            scenario="data_science",
            status=RunStatus.RUNNING,
            stop_conditions=StopConditions(max_loops=3, max_duration_sec=120),
            entry_input={"task_id": "task-02"},
        )
        scenario = bundle.scenario_plugin.build_context(
            run_session=run_session,
            input_payload={"task_summary": "improve baseline"},
        )

        plan = Plan(plan_id="plan-1", exploration_strength=0.5)
        proposal = bundle.proposal_engine.propose(
            task_summary="improve baseline",
            context=ContextPack(items=[], highlights=[]),
            parent_ids=[],
            plan=plan,
            scenario=scenario,
        )
        experiment = bundle.experiment_generator.generate(
            proposal=proposal,
            run_session=run_session,
            loop_state=LoopState(loop_id="loop-test", iteration=0, status=RunStatus.RUNNING),
            parent_ids=[],
        )
        artifact = bundle.coder.develop(experiment=experiment, proposal=proposal, scenario=scenario)
        result = bundle.runner.run(artifact, scenario)
        feedback = bundle.feedback_analyzer.summarize(
            experiment=experiment,
            result=result,
            score=Score(score_id="score-1", value=0.1, metric_name="acc"),
        )

        self.assertEqual(proposal.summary, "improve baseline")
        self.assertEqual(experiment.run_id, run_session.run_id)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(feedback.acceptable)


class MainFlowAcceptanceTests(unittest.TestCase):
    def test_entry_point_uses_registry_without_scenario_if_else(self) -> None:
        source = Path("agentrd_cli.py").read_text(encoding="utf-8")
        self.assertIn("plugin_registry", source)
        self.assertIsNone(re.search(r"if\s+.*scenario\s*==", source))


if __name__ == "__main__":
    unittest.main()
