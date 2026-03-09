from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from app.runtime import build_run_service, build_runtime
from data_models import EventType, ExecutionResult, StopConditions
from evaluation_service.service import EvaluationService, EvaluationServiceConfig
from evaluation_service.stratified_splitter import StratifiedSplitter
from evaluation_service.validation_selector import ValidationSelector
from llm.adapter import MockLLMProvider
from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.interaction_kernel import HypothesisRecord, InteractionKernel
from memory_service.service import MemoryService, MemoryServiceConfig

from tests._llm_test_utils import patch_runtime_llm_provider


class TestFC1456E2E(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._env_patch = patch.dict(
            os.environ,
            {
                "AGENTRD_ARTIFACT_ROOT": self._tmpdir.name,
                "AGENTRD_WORKSPACE_ROOT": self._tmpdir.name,
                "AGENTRD_TRACE_STORAGE_PATH": os.path.join(self._tmpdir.name, "trace", "events.jsonl"),
                "AGENTRD_SQLITE_PATH": os.path.join(self._tmpdir.name, "meta.db"),
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                "RD_AGENT_LLM_PROVIDER": "mock",
            },
            clear=False,
        )
        self._env_patch.start()
        self._llm_patch = patch_runtime_llm_provider()
        self._llm_patch.start()

    def tearDown(self) -> None:
        self._llm_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_fc1_time_aware_planning_in_loop(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="FC-1 time-aware test",
            stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
        )

        context = run_service.start_run(
            run.run_id,
            task_summary="FC-1 time-aware test",
            loops_per_call=2,
        )

        self.assertIsNotNone(context)
        self.assertGreater(context.budget.elapsed_time, 0.0)
        self.assertEqual(len(context.budget.iteration_durations), 2)
        self.assertTrue(all(d > 0.0 for d in context.budget.iteration_durations))

        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        event_types = {event.event_type for event in events}
        self.assertTrue(
            {
                EventType.HYPOTHESIS_GENERATED,
                EventType.EXPERIMENT_GENERATED,
                EventType.CODING_ROUND,
                EventType.EXECUTION_FINISHED,
                EventType.FEEDBACK_GENERATED,
                EventType.TRACE_RECORDED,
            }.issubset(event_types)
        )

    def test_fc4_hypothesis_memory_integration(self) -> None:
        config = MemoryServiceConfig(enable_hypothesis_storage=True)
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        memory_service = MemoryService(
            config,
            hypothesis_selector=selector,
            interaction_kernel=kernel,
        )

        memory_service.write_hypothesis("Use gradient boosting", 0.8, "branch-1")
        memory_service.write_hypothesis("Use neural network", 0.6, "branch-2")
        memory_service.write_hypothesis("Use random forest", 0.7, "branch-1")

        all_hypotheses = memory_service.query_hypotheses()
        self.assertEqual(len(all_hypotheses), 3)

        branch_one_hypotheses = memory_service.query_hypotheses(branch_id="branch-1")
        self.assertEqual(len(branch_one_hypotheses), 2)
        for hypothesis in branch_one_hypotheses:
            self.assertEqual(hypothesis.branch_id, "branch-1")

        cross_branch = memory_service.get_cross_branch_hypotheses("branch-1")
        self.assertEqual(len(cross_branch), 1)
        self.assertEqual(cross_branch[0].branch_id, "branch-2")

        context_pack = memory_service.query_context({})
        self.assertGreaterEqual(len(context_pack.scored_items), 0)

        stats = memory_service.get_memory_stats()
        self.assertIn("hypothesis_count", stats)
        self.assertEqual(stats["hypothesis_count"], 3)

    def test_fc4_kernel_selector_integration(self) -> None:
        kernel = InteractionKernel()
        provider = MockLLMProvider()
        selector = HypothesisSelector(kernel, llm_adapter=provider)

        now = time.time()
        h1 = HypothesisRecord("Use XGBoost for classification", 0.8, now, "b1")
        h2 = HypothesisRecord("Use neural network for regression", 0.4, now, "b2")
        h3 = HypothesisRecord("Use random forest for classification", 0.9, now, "b1")

        best = selector.select_hypothesis([h1, h2, h3], "context")
        self.assertEqual(best.score, 0.9)

        early = selector.adaptive_select([h1, h2, h3], 1, 10, ["context"], "task", "data_science")
        self.assertIn(early.modification_type, ("generate", "modify", "none"))
        self.assertTrue(isinstance(early.modified_hypothesis, str))

        late = selector.adaptive_select([h1, h2, h3], 9, 10, ["context"], "task", "data_science")
        self.assertEqual(late.modification_type, "select")
        self.assertEqual(late.modified_hypothesis, h3.text)

    def test_fc5_evaluation_multi_stage(self) -> None:
        evaluation_service = EvaluationService(EvaluationServiceConfig())

        execution_result = ExecutionResult(
            run_id="test-run",
            exit_code=0,
            logs_ref="all tests passed",
            artifacts_ref="artifact://test-run",
            duration_sec=1.5,
            timed_out=False,
        )
        result = evaluation_service.evaluate_run(execution_result)

        self.assertGreaterEqual(result.score.value, 0.0)
        self.assertLessEqual(result.score.value, 1.0)
        self.assertIn("stages", result.score.details)
        self.assertIn("execution", result.score.details["stages"])

    def test_fc6_stratified_split_and_selector(self) -> None:
        splitter = StratifiedSplitter(train_ratio=0.9, test_ratio=0.1, seed=42)

        ids = [f"item-{i}" for i in range(100)]
        labels = [str(i % 3) for i in range(100)]
        manifest = splitter.split(ids, labels)

        self.assertEqual(len(manifest.train_ids) + len(manifest.test_ids), 100)
        self.assertAlmostEqual(len(manifest.train_ids) / 100.0, 0.9, delta=0.05)

        manifest_second = splitter.split(ids, labels)
        self.assertEqual(manifest.train_ids, manifest_second.train_ids)
        self.assertEqual(manifest.test_ids, manifest_second.test_ids)

        evaluation_service = EvaluationService(EvaluationServiceConfig())
        selector = ValidationSelector(evaluation_service)
        candidate_fail = ExecutionResult(
            run_id="r-fail",
            exit_code=1,
            logs_ref="log://fail",
            artifacts_ref="artifact://fail",
            duration_sec=2.0,
            timed_out=False,
        )
        candidate_ok = ExecutionResult(
            run_id="r-ok",
            exit_code=0,
            logs_ref="log://ok",
            artifacts_ref="artifact://ok",
            duration_sec=1.0,
            timed_out=False,
        )
        ranked = selector.rank_candidates([candidate_fail, candidate_ok])
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0][0].run_id, "r-ok")
        self.assertGreaterEqual(ranked[0][1].value, ranked[1][1].value)

    def test_regression_default_config_no_fc_features(self) -> None:
        runtime = build_runtime()
        self.assertFalse(runtime.config.enable_hypothesis_storage)
        self.assertFalse(runtime.config.use_llm_planning)
        self.assertFalse(runtime.config.debug_mode)

        run_service = build_run_service(runtime, "data_science")
        run = run_service.create_run(
            task_summary="regression test",
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
        )
        context = run_service.start_run(
            run.run_id,
            task_summary="regression test",
            loops_per_call=1,
        )

        self.assertIsNotNone(context)
        run_session = context.run_session
        self.assertIsNotNone(run_session)
        assert run_session is not None
        self.assertEqual(run_session.status.name, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
