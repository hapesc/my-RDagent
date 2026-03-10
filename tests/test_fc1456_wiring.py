from __future__ import annotations

import os
import re
import unittest
from typing import cast
from unittest.mock import MagicMock, patch

from app.config import load_config
from app.runtime import build_runtime
from core.loop.engine import LoopEngine, LoopEngineConfig
from data_models import (
    ContextPack,
    Plan,
    RunSession,
    RunStatus,
    Score,
    StopConditions,
)
from scenarios.data_science.plugin import DataScienceProposalEngine, DataScienceScenarioPlugin
from scenarios.quant.plugin import QuantProposalEngine, QuantScenarioPlugin
from scenarios.synthetic_research.plugin import SyntheticResearchProposalEngine, SyntheticResearchScenarioPlugin
from tests._llm_test_utils import patch_runtime_llm_provider


class TestFC1456Wiring(unittest.TestCase):
    def _make_run_session(self, max_loops: int = 2) -> RunSession:
        return RunSession(
            run_id="test-run-001",
            scenario="synthetic_research",
            status=RunStatus.CREATED,
            stop_conditions=StopConditions(max_loops=max_loops, max_duration_sec=3600),
            entry_input={},
            active_branch_ids=["main"],
        )

    def _make_engine(self, max_loops: int = 1, branches: int = 1, planner=None) -> LoopEngine:
        mock_planner = planner or MagicMock()
        if planner is None:
            mock_planner.generate_plan.return_value = Plan(
                plan_id="plan-test",
                exploration_strength=0.5,
                budget_allocation={},
                guidance=[],
            )

        mock_memory = MagicMock()
        mock_memory.query_context.return_value = ContextPack(items=[], highlights=[])

        mock_exploration = MagicMock()
        mock_exploration.select_parents.return_value = ["root"]
        mock_exploration.register_node.side_effect = lambda g, n: g
        mock_exploration.prune_branches.side_effect = lambda g: g

        mock_step = MagicMock()

        call_count = {"value": 0}

        def _execute_iteration(**_kwargs):
            call_count["value"] += 1
            idx = call_count["value"]
            mock_result = MagicMock()
            mock_result.experiment = MagicMock()
            mock_result.experiment.node_id = f"node-{idx}"
            mock_result.experiment.parent_node_id = None
            mock_result.experiment.hypothesis = {"hypothesis": f"hypothesis-{idx}"}
            mock_result.proposal = MagicMock()
            mock_result.proposal.proposal_id = f"proposal-{idx}"
            mock_result.proposal.summary = f"summary-{idx}"
            mock_result.artifact_id = f"artifact-{idx}"
            mock_result.score = Score(score_id=f"score-{idx}", value=0.5, metric_name="mock")
            mock_result.feedback = MagicMock()
            mock_result.feedback.decision = True
            return mock_result

        mock_step.execute_iteration.side_effect = _execute_iteration

        mock_run_store = MagicMock()
        mock_event_store = MagicMock()

        return LoopEngine(
            config=LoopEngineConfig(default_max_loops=max_loops, branches_per_iteration=branches),
            planner=mock_planner,
            exploration_manager=mock_exploration,
            memory_service=mock_memory,
            step_executor=mock_step,
            run_store=mock_run_store,
            event_store=mock_event_store,
        )

    def test_config_loads_hypothesis_storage_true(self):
        config = load_config({"RD_AGENT_HYPOTHESIS_STORAGE": "true"})
        self.assertTrue(config.enable_hypothesis_storage)

    def test_config_loads_hypothesis_storage_default(self):
        config = load_config({})
        self.assertFalse(config.enable_hypothesis_storage)

    def test_config_loads_llm_planning_true(self):
        config = load_config({"RD_AGENT_LLM_PLANNING": "true"})
        self.assertTrue(config.use_llm_planning)

    def test_config_loads_llm_planning_default(self):
        config = load_config({})
        self.assertFalse(config.use_llm_planning)

    def test_config_loads_debug_mode(self):
        config = load_config({"RD_AGENT_DEBUG_MODE": "true"})
        self.assertTrue(config.debug_mode)

    def test_build_runtime_succeeds(self):
        with (
            patch.dict(
                os.environ,
                {
                    "RD_AGENT_LLM_PROVIDER": "mock",
                    "RD_AGENT_HYPOTHESIS_STORAGE": "false",
                    "RD_AGENT_LLM_PLANNING": "false",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()
        self.assertIsNotNone(runtime)
        self.assertFalse(runtime.config.enable_hypothesis_storage)
        self.assertFalse(runtime.config.use_llm_planning)

    def test_loop_engine_updates_elapsed_time(self):
        engine = self._make_engine(max_loops=1)
        session = self._make_run_session(max_loops=1)
        ctx = engine.run(session, task_summary="test")
        self.assertGreater(ctx.budget.elapsed_time, 0.0)

    def test_loop_engine_populates_iteration_durations(self):
        engine = self._make_engine(max_loops=2)
        session = self._make_run_session(max_loops=2)
        ctx = engine.run(session, task_summary="test")
        self.assertEqual(len(ctx.budget.iteration_durations), 2)
        for duration in ctx.budget.iteration_durations:
            self.assertGreater(duration, 0.0)

    def test_loop_engine_computes_estimated_remaining(self):
        checks = {"saw_positive": False}

        def _plan_side_effect(context):
            if context.loop_state.iteration == 1 and context.budget.estimated_remaining > 0.0:
                checks["saw_positive"] = True
            return Plan(
                plan_id=f"plan-{context.loop_state.iteration}",
                exploration_strength=0.5,
                budget_allocation={},
                guidance=[],
            )

        planner = MagicMock()
        planner.generate_plan.side_effect = _plan_side_effect
        engine = self._make_engine(max_loops=3, planner=planner)
        session = self._make_run_session(max_loops=3)

        ctx = engine.run(session, task_summary="test")

        self.assertTrue(checks["saw_positive"])
        self.assertEqual(len(ctx.budget.iteration_durations), 3)
        self.assertEqual(ctx.budget.estimated_remaining, 0.0)

    def test_loop_engine_passes_iteration_history_to_planner_context(self):
        captured_history = []

        def _plan_side_effect(context):
            captured_history.append(context.history_summary)
            return Plan(
                plan_id=f"plan-{context.loop_state.iteration}",
                exploration_strength=0.5,
                budget_allocation={},
                guidance=[],
            )

        planner = MagicMock()
        planner.generate_plan.side_effect = _plan_side_effect
        engine = self._make_engine(max_loops=3, planner=planner)
        session = self._make_run_session(max_loops=3)

        engine.run(session, task_summary="test")

        self.assertEqual(captured_history[0], {})
        self.assertIn("iteration_0", captured_history[1])
        self.assertEqual(captured_history[1]["iteration_0"]["hypothesis"], "summary-1")
        self.assertEqual(captured_history[1]["iteration_0"]["outcome"], "accepted")
        self.assertIsInstance(captured_history[1]["iteration_0"]["score"], float)
        self.assertIn("iteration_1", captured_history[2])

    def test_data_science_proposal_prompt_includes_context_guidance_and_parents(self):
        llm = MagicMock()
        llm.generate_structured.return_value = MagicMock(summary="proposal", constraints=["risk"], virtual_score=0.4)
        engine = DataScienceProposalEngine(llm)
        scenario = DataScienceScenarioPlugin().build_context(
            self._make_run_session(),
            {"task_summary": "predict churn", "loop_index": 2},
        )
        context = ContextPack(
            highlights=["recent failure: leakage"],
            scored_items=[("cross-branch idea", 0.91), ("same-branch retry", 0.75)],
        )
        plan = Plan(plan_id="p1", guidance=["focus:refine", "budget:moderate"])

        engine.propose("predict churn", context, ["node-a", "node-b"], plan, scenario)

        prompt = llm.generate_structured.call_args.args[0]
        prompt_lower = prompt.lower()
        
        self.assertIn("prior context", prompt_lower)
        self.assertIn("recent failure: leakage", prompt)
        self.assertIn("strategic guidance", prompt_lower)
        self.assertIn("focus:refine", prompt)
        self.assertIn("parent branch continuity", prompt_lower)
        
        score_match = cast(re.Match | None, re.search(r"cross-branch\s+idea\s*\(score=([0-9.]+)\)", prompt))
        self.assertIsNotNone(score_match)
        if score_match is not None:
            extracted_score = float(score_match.group(1))
            self.assertAlmostEqual(extracted_score, 0.91, places=2)
        
        parent_section = cast(re.Match | None, re.search(r"parent\s+branch\s+continuity[:\s]+(.+?)(?:\n|$)", prompt, re.IGNORECASE))
        self.assertIsNotNone(parent_section)
        if parent_section is not None:
            parent_content = parent_section.group(1)
            self.assertIn("node-a", parent_content)
            self.assertIn("node-b", parent_content)


    def test_quant_proposal_prompt_includes_context_guidance_and_parents(self):
        llm = MagicMock()
        llm.generate_structured.return_value = MagicMock(summary="factor", constraints=["risk"], virtual_score=0.6)
        engine = QuantProposalEngine(llm)
        scenario = QuantScenarioPlugin().build_context(
            self._make_run_session(),
            {"task_summary": "mine alpha", "loop_index": 1, "previous_results": ["factor-a"]},
        )
        context = ContextPack(highlights=["same branch memory"], scored_items=[("cross branch alpha", 0.88)])
        plan = Plan(plan_id="p1", guidance=["focus:novelty"])

        engine.propose("mine alpha", context, ["quant-parent"], plan, scenario)

        prompt = llm.generate_structured.call_args.args[0]
        prompt_lower = prompt.lower()
        
        self.assertIn("prior context", prompt_lower)
        self.assertIn("same branch memory", prompt)
        self.assertIn("strategic guidance", prompt_lower)
        self.assertIn("focus:novelty", prompt)
        self.assertIn("parent branch continuity", prompt_lower)
        
        score_match = cast(re.Match | None, re.search(r"cross\s+branch\s+alpha\s*\(score=([0-9.]+)\)", prompt))
        self.assertIsNotNone(score_match)
        if score_match is not None:
            extracted_score = float(score_match.group(1))
            self.assertAlmostEqual(extracted_score, 0.88, places=2)
        
        parent_section = cast(re.Match | None, re.search(r"parent\s+branch\s+continuity[:\s]+(.+?)(?:\n|$)", prompt, re.IGNORECASE))
        self.assertIsNotNone(parent_section)
        if parent_section is not None:
            parent_content = parent_section.group(1)
            self.assertIn("quant-parent", parent_content)


    def test_synthetic_proposal_placeholder_keeps_context_visible(self):
        engine = SyntheticResearchProposalEngine(llm_adapter=None)
        scenario = SyntheticResearchScenarioPlugin().build_context(
            self._make_run_session(),
            {"task_summary": "survey agents", "loop_index": 0},
        )
        context = ContextPack(highlights=["memory insight"], scored_items=[("cross branch note", 0.5)])
        plan = Plan(plan_id="p1", guidance=["focus:balance"])

        proposal = engine.propose("survey agents", context, ["root-parent"], plan, scenario)

        summary_lower = proposal.summary.lower()
        self.assertIn("prior context", summary_lower)
        self.assertIn("memory insight", proposal.summary)
        self.assertIn("strategic guidance", summary_lower)
        self.assertIn("parent branch continuity", summary_lower)
        
        score_match = cast(re.Match | None, re.search(r"cross\s+branch\s+note\s*\(score=([0-9.]+)\)", proposal.summary))
        self.assertIsNotNone(score_match)
        if score_match is not None:
            extracted_score = float(score_match.group(1))
            self.assertAlmostEqual(extracted_score, 0.5, places=2)


    def test_data_science_build_context_populates_split_manifest(self):
        scenario = DataScienceScenarioPlugin().build_context(
            self._make_run_session(),
            {
                "task_summary": "predict churn",
                "data_ids": [f"id-{idx}" for idx in range(10)],
                "labels": ["A"] * 6 + ["B"] * 4,
                "split_seed": 7,
            },
        )

        manifest = scenario.config["split_manifest"]
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["seed"], 7)
        self.assertEqual(len(manifest["train_ids"]) + len(manifest["test_ids"]), 10)
        self.assertEqual(set(manifest["train_ids"]) | set(manifest["test_ids"]), {f"id-{idx}" for idx in range(10)})

    def test_quant_build_context_prefers_ordered_split_when_labels_missing(self):
        scenario = QuantScenarioPlugin().build_context(
            self._make_run_session(),
            {
                "task_summary": "mine alpha",
                "data_ids": ["d3", "d1", "d2", "d4"],
                "timestamps": ["2024-01-03", "2024-01-01", "2024-01-02", "2024-01-04"],
                "test_ratio": 0.25,
                "split_seed": 11,
            },
        )

        manifest = scenario.config["split_manifest"]
        self.assertEqual(manifest["seed"], 11)
        self.assertEqual(manifest["train_ids"], ["d1", "d2", "d3"])
        self.assertEqual(manifest["test_ids"], ["d4"])


if __name__ == "__main__":
    unittest.main()
