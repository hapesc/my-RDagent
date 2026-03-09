from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_service import MemoryService, MemoryServiceConfig
from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.interaction_kernel import InteractionKernel


class MemoryServiceTests(unittest.TestCase):
    def test_write_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("LLM timeout", {"error_type": "timeout"})

            self.assertEqual(service.get_memory_stats(), {"items": 1})

    def test_write_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory(
                "LLM timeout on large prompt",
                {
                    "scenario": "data_science",
                    "step": "coding",
                    "error_type": "timeout",
                },
            )

            context = service.query_context({"error_type": "timeout"})

            self.assertIn("LLM timeout on large prompt", context.items)

    def test_query_empty_db(self) -> None:
        service = MemoryService(MemoryServiceConfig())

        context = service.query_context({"error_type": "timeout"})

        self.assertEqual(context.items, [])
        self.assertEqual(context.highlights, [])

    def test_max_context_items_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path, max_context_items=10))

            for index in range(15):
                service.write_memory(
                    f"failure-{index}",
                    {"error_type": "timeout", "index": str(index)},
                )

            context = service.query_context({"error_type": "timeout"})

            self.assertLessEqual(len(context.items), 10)

    def test_query_filters_by_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("timeout case", {"error_type": "timeout", "step": "coding"})
            service.write_memory("oom case", {"error_type": "oom", "step": "running"})

            context = service.query_context({"error_type": "timeout"})

            self.assertEqual(context.items, ["timeout case"])

    def test_default_config_backward_compat(self) -> None:
        service = MemoryService(MemoryServiceConfig())
        self.assertIsInstance(service, MemoryService)

    def test_query_context_populates_ranked_cross_branch_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(
                MemoryServiceConfig(
                    db_path=db_path,
                    enable_hypothesis_storage=True,
                    max_context_items=5,
                ),
                hypothesis_selector=HypothesisSelector(InteractionKernel()),
                interaction_kernel=InteractionKernel(),
            )

            service.write_hypothesis(
                text="branch-a volatility alpha with quality filter",
                score=0.8,
                branch_id="branch-a",
            )
            service.write_hypothesis(
                text="branch-a quality alpha variant",
                score=0.7,
                branch_id="branch-a",
            )
            service.write_hypothesis(
                text="branch-b volatility alpha with momentum overlay",
                score=0.9,
                branch_id="branch-b",
            )

            context = service.query_context(
                {
                    "branch_id": "branch-a",
                    "task_summary": "find volatility alpha",
                    "scenario": "quant",
                    "iteration": "3",
                    "max_iterations": "6",
                }
            )

            self.assertEqual(context.branch_id, "branch-a")
            self.assertEqual(context.source_type, "memory")
            self.assertEqual(len(context.scored_items), 3)
            self.assertIn("branch-b volatility alpha with momentum overlay", [text for text, _ in context.scored_items])
            self.assertGreaterEqual(context.scored_items[0][1], context.scored_items[1][1])
            self.assertGreaterEqual(context.scored_items[1][1], context.scored_items[2][1])
            self.assertEqual(context.highlights[0], context.scored_items[0][0])

    def test_query_context_ignores_branch_control_key_for_failure_case_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path, max_context_items=5))

            service.write_memory("same timeout across branches", {"error_type": "timeout", "step": "coding"})

            context = service.query_context({"branch_id": "branch-x", "error_type": "timeout"})

            self.assertEqual(context.items, ["same timeout across branches"])
            self.assertEqual(context.highlights, ["error_type"])

    def test_query_context_without_failure_cases_uses_hypothesis_highlights(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(
                MemoryServiceConfig(
                    db_path=db_path,
                    enable_hypothesis_storage=True,
                    max_context_items=3,
                ),
                interaction_kernel=InteractionKernel(),
            )

            service.write_hypothesis("top ranked branch memory", score=0.95, branch_id="branch-x")
            service.write_hypothesis("second ranked memory", score=0.65, branch_id="branch-y")

            context = service.query_context({"branch_id": "branch-x"})

            self.assertEqual(context.items, [])
            self.assertEqual(context.highlights[0], "top ranked branch memory")
            self.assertEqual(len(context.scored_items), 2)


if __name__ == "__main__":
    unittest.main()
