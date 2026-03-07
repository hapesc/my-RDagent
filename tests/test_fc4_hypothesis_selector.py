import time
import unittest
from unittest.mock import patch

from llm.adapter import MockLLMProvider
from llm.schemas import HypothesisModification
from memory_service.hypothesis_selector import HypothesisSelector, rank_by_kernel
from memory_service.interaction_kernel import HypothesisRecord, InteractionKernel


class TestFCHypothesisSelector(unittest.TestCase):
    def _record(self, text: str, score: float, ts: float, branch: str) -> HypothesisRecord:
        return HypothesisRecord(text=text, score=score, timestamp=ts, branch_id=branch)

    def test_select_hypothesis_picks_highest_score(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [
            self._record("h1", 0.2, now, "b1"),
            self._record("h2", 0.9, now - 1.0, "b2"),
            self._record("h3", 0.6, now - 2.0, "b3"),
        ]

        best = selector.select_hypothesis(candidates, "ctx")
        self.assertEqual(best.text, "h2")
        self.assertEqual(best.score, 0.9)

    def test_select_hypothesis_empty_raises(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)

        with self.assertRaises(ValueError):
            selector.select_hypothesis([], "ctx")

    def test_adaptive_select_early_generates(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        generated = HypothesisModification(
            modified_hypothesis="generated hypothesis",
            modification_type="generate",
            source_hypothesis="",
            reasoning="early exploration",
        )
        with patch.object(selector, "generate_hypothesis", return_value=generated) as generate_spy:
            result = selector.adaptive_select(
                candidates=[],
                iteration=1,
                max_iterations=10,
                context_items=["c1"],
                task_summary="task",
                scenario_name="scenario",
            )
        generate_spy.assert_called_once()
        self.assertIsInstance(result, HypothesisModification)
        self.assertIn("generate", result.modification_type)

    def test_adaptive_select_mid_modifies(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [self._record("source", 0.8, now, "b1")]
        modified = HypothesisModification(
            modified_hypothesis="modified hypothesis",
            modification_type="modify",
            source_hypothesis="source",
            reasoning="mid-stage refinement",
        )
        with patch.object(selector, "modify_hypothesis", return_value=modified) as modify_spy:
            result = selector.adaptive_select(
                candidates=candidates,
                iteration=5,
                max_iterations=10,
                context_items=["c1"],
                task_summary="task",
                scenario_name="scenario",
            )
        modify_spy.assert_called_once()
        self.assertIsInstance(result, HypothesisModification)
        self.assertIn("modify", result.modification_type)

    def test_adaptive_select_late_selects(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [
            self._record("h1", 0.5, now - 2.0, "b1"),
            self._record("h2", 0.7, now - 1.0, "b2"),
            self._record("h3", 0.6, now, "b3"),
        ]

        result = selector.adaptive_select(
            candidates=candidates,
            iteration=9,
            max_iterations=10,
            context_items=["c1"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertIsInstance(result, HypothesisModification)
        self.assertEqual(result.modification_type, "select")
        self.assertEqual(result.modified_hypothesis, "h2")

    def test_adaptive_select_boundary_033(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [self._record("source", 0.8, now, "b1")]
        modified = HypothesisModification(
            modified_hypothesis="boundary modified",
            modification_type="modify-boundary",
            source_hypothesis="source",
            reasoning="boundary check",
        )
        with patch.object(selector, "modify_hypothesis", return_value=modified) as modify_spy:
            result = selector.adaptive_select(
                candidates=candidates,
                iteration=33,
                max_iterations=100,
                context_items=["c1"],
                task_summary="task",
                scenario_name="scenario",
            )
        modify_spy.assert_called_once()
        self.assertIn("modify", result.modification_type)

    def test_adaptive_select_boundary_066(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [self._record("source", 0.8, now, "b1")]

        result = selector.adaptive_select(
            candidates=candidates,
            iteration=66,
            max_iterations=100,
            context_items=["c1"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertEqual(result.modification_type, "select")

    def test_modify_hypothesis_without_llm(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        source = self._record("original hypothesis", 0.8, now, "b1")

        result = selector.modify_hypothesis(
            source=source,
            context_items=["c1"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertEqual(result.modification_type, "identity")
        self.assertEqual(result.source_hypothesis, source.text)
        self.assertEqual(result.modified_hypothesis, source.text)

    def test_generate_hypothesis_without_llm(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)

        result = selector.generate_hypothesis(
            context_items=["c1"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertEqual(result.modification_type, "none")
        self.assertEqual(result.modified_hypothesis, "")

    def test_modify_hypothesis_with_mock_llm(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel, llm_adapter=MockLLMProvider())
        now = time.time()
        source = self._record("original hypothesis", 0.8, now, "b1")

        result = selector.modify_hypothesis(
            source=source,
            context_items=["c1", "c2"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertIsInstance(result, HypothesisModification)
        self.assertNotEqual(result.modified_hypothesis, "")

    def test_generate_hypothesis_with_mock_llm(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel, llm_adapter=MockLLMProvider())

        result = selector.generate_hypothesis(
            context_items=["c1", "c2"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertIsInstance(result, HypothesisModification)
        self.assertNotEqual(result.modified_hypothesis, "")

    def test_rank_by_kernel(self):
        kernel = InteractionKernel()
        now = time.time()
        target = self._record("use random forest model", 0.8, now, "t")
        candidates = [
            self._record("try random forest with tuning", 0.78, now - 10.0, "c1"),
            self._record("switch to linear regression", 0.4, now - 600.0, "c2"),
            self._record("random forest with feature selection", 0.82, now - 5.0, "c3"),
        ]

        ranked = rank_by_kernel(target, candidates, kernel)
        self.assertEqual(len(ranked), 3)
        self.assertTrue(all(isinstance(item, tuple) and len(item) == 2 for item in ranked))
        self.assertTrue(all(isinstance(item[0], HypothesisRecord) for item in ranked))
        self.assertTrue(all(isinstance(item[1], float) for item in ranked))
        scores = [score for _, score in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(ranked[0][1], max(scores))

    def test_adaptive_select_max_iterations_zero(self):
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel)
        now = time.time()
        candidates = [self._record("safe candidate", 0.9, now, "b1")]

        result = selector.adaptive_select(
            candidates=candidates,
            iteration=1,
            max_iterations=0,
            context_items=["c1"],
            task_summary="task",
            scenario_name="scenario",
        )
        self.assertEqual(result.modification_type, "select")


if __name__ == "__main__":
    unittest.main()
