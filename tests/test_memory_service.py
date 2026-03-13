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

            self.assertEqual(service.get_memory_stats(), {"items": 1, "hypothesis_count": 0})

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
            expected_timestamp = max(
                hypothesis.timestamp
                for hypothesis in [
                    *service.query_hypotheses(branch_id="branch-a", limit=5),
                    *service.get_cross_branch_hypotheses("branch-a", limit=5),
                ]
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
            self.assertEqual(context.source_type, "cross_branch")
            self.assertEqual(len(context.scored_items), 3)
            self.assertIn("branch-b volatility alpha with momentum overlay", [text for text, _ in context.scored_items])
            self.assertGreaterEqual(context.scored_items[0][1], context.scored_items[1][1])
            self.assertGreaterEqual(context.scored_items[1][1], context.scored_items[2][1])
            self.assertEqual(context.highlights[0], context.scored_items[0][0])
            self.assertIsNotNone(context.timestamp)
            self.assertEqual(context.timestamp, expected_timestamp)

    def test_query_context_same_branch_hypotheses_keep_memory_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(
                MemoryServiceConfig(
                    db_path=db_path,
                    enable_hypothesis_storage=True,
                    max_context_items=5,
                )
            )

            service.write_hypothesis(
                text="branch-a local hypothesis",
                score=0.8,
                branch_id="branch-a",
            )
            service.write_hypothesis(
                text="branch-a second local hypothesis",
                score=0.7,
                branch_id="branch-a",
            )
            expected_timestamp = max(
                hypothesis.timestamp for hypothesis in service.query_hypotheses(branch_id="branch-a", limit=5)
            )

            context = service.query_context({"branch_id": "branch-a"})

            self.assertEqual(context.branch_id, "branch-a")
            self.assertEqual(context.source_type, "memory")
            self.assertEqual(len(context.scored_items), 2)
            self.assertIsNotNone(context.timestamp)
            self.assertEqual(context.timestamp, expected_timestamp)

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

    def test_json_extract_exact_match_single_key(self) -> None:
        """Test json_extract matching with single key-value pair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("case 1", {"error_type": "timeout"})
            service.write_memory("case 2", {"error_type": "oom"})

            context = service.query_context({"error_type": "timeout"})

            self.assertEqual(context.items, ["case 1"])

    def test_json_extract_numeric_values(self) -> None:
        """Test json_extract with numeric string values stored as JSON strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("iteration 5 case", {"iteration": "5", "step": "coding"})
            service.write_memory("iteration 3 case", {"iteration": "3", "step": "coding"})

            context = service.query_context({"iteration": "5"})

            self.assertEqual(context.items, ["iteration 5 case"])

    def test_json_extract_multiple_keys_all_must_match(self) -> None:
        """Test that json_extract AND clause requires ALL metadata keys to match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory(
                "both match",
                {"error_type": "timeout", "step": "coding"},
            )
            service.write_memory(
                "only error matches",
                {"error_type": "timeout", "step": "running"},
            )
            service.write_memory(
                "only step matches",
                {"error_type": "oom", "step": "coding"},
            )

            context = service.query_context({"error_type": "timeout", "step": "coding"})

            self.assertEqual(context.items, ["both match"])

    def test_json_extract_key_order_independence(self) -> None:
        """Test that json_extract matches regardless of JSON key order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            # write_memory uses sort_keys=True, so stored JSON always has sorted keys
            service.write_memory("test case", {"scenario": "data_science", "error_type": "timeout"})

            # Query with different order should still match
            context = service.query_context({"error_type": "timeout", "scenario": "data_science"})

            self.assertEqual(context.items, ["test case"])

    def test_json_extract_special_characters_in_values(self) -> None:
        """Test json_extract with special characters in metadata values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory(
                "special case",
                {"error_msg": 'connection refused: "db" timeout'},
            )

            context = service.query_context({"error_msg": 'connection refused: "db" timeout'})

            self.assertEqual(context.items, ["special case"])

    def test_json_extract_substring_does_not_match(self) -> None:
        """Test that json_extract requires exact match, not substring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("timeout case", {"error_type": "timeout_long"})

            context = service.query_context({"error_type": "timeout"})

            self.assertEqual(context.items, [])

    def test_json_extract_no_false_positives_across_keys(self) -> None:
        """Test that json_extract value in one key doesn't match different key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "memory.db")
            service = MemoryService(MemoryServiceConfig(db_path=db_path))

            service.write_memory("case", {"type1": "timeout", "type2": "oom"})

            context = service.query_context({"type2": "timeout"})

            self.assertEqual(context.items, [])


if __name__ == "__main__":
    unittest.main()
