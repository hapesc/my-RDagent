import json
import unittest

from memory_service.interaction_kernel import HypothesisRecord
from memory_service.service import MemoryService, MemoryServiceConfig


class TestFC4Memory(unittest.TestCase):
    def test_write_hypothesis_stores_correctly(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("hyp-1", 0.9, "branch-1")

        results = service.query_hypotheses()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "hyp-1")
        self.assertEqual(results[0].score, 0.9)
        self.assertEqual(results[0].branch_id, "branch-1")

    def test_query_hypotheses_returns_stored(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("h1", 0.1, "b1")
        service.write_hypothesis("h2", 0.2, "b1")
        service.write_hypothesis("h3", 0.3, "b2")

        results = service.query_hypotheses()
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(item, HypothesisRecord) for item in results))
        self.assertEqual({item.text for item in results}, {"h1", "h2", "h3"})

    def test_query_hypotheses_by_branch(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("h1", 0.1, "branch-1")
        service.write_hypothesis("h2", 0.2, "branch-2")
        service.write_hypothesis("h3", 0.3, "branch-1")

        results = service.query_hypotheses(branch_id="branch-1")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.branch_id == "branch-1" for item in results))
        self.assertEqual({item.text for item in results}, {"h1", "h3"})

    def test_query_hypotheses_limit(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        for index in range(5):
            service.write_hypothesis(f"h{index}", float(index), "b1")

        results = service.query_hypotheses(limit=2)
        self.assertEqual(len(results), 2)

    def test_get_cross_branch_hypotheses_excludes_current(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("h1", 0.1, "b1")
        service.write_hypothesis("h2", 0.8, "b2")
        service.write_hypothesis("h3", 0.7, "b2")

        results = service.get_cross_branch_hypotheses("b1")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.branch_id == "b2" for item in results))

    def test_get_cross_branch_hypotheses_empty_when_only_same_branch(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("h1", 0.1, "b1")
        service.write_hypothesis("h2", 0.2, "b1")

        results = service.get_cross_branch_hypotheses("b1")
        self.assertEqual(results, [])

    def test_query_context_backward_compatible(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=False))
        service.write_memory("memory-1", {"error_type": "timeout"})

        context = service.query_context({"error_type": "timeout"})

        self.assertEqual(context.items, ["memory-1"])
        self.assertEqual(context.scored_items, [])

    def test_query_context_with_hypotheses_populates_scored_items(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))
        service.write_memory("memory-1", {"error_type": "timeout"})
        service.write_hypothesis("h1", 0.3, "b1")
        service.write_hypothesis("h2", 0.7, "b2")

        context = service.query_context({"error_type": "timeout"})

        self.assertEqual(context.items, ["memory-1"])
        self.assertGreater(len(context.scored_items), 0)
        self.assertTrue(all(isinstance(item[0], str) and isinstance(item[1], float) for item in context.scored_items))

    def test_get_memory_stats_includes_hypothesis_count(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))

        service.write_hypothesis("h1", 0.1, "b1")
        service.write_hypothesis("h2", 0.2, "b1")
        service.write_hypothesis("h3", 0.3, "b2")

        stats = service.get_memory_stats()
        self.assertEqual(stats.get("hypothesis_count"), 3)

    def test_get_memory_stats_no_hypothesis_key_when_disabled(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=False))
        service.write_memory("memory-1", {"k": "v"})

        stats = service.get_memory_stats()
        self.assertNotIn("hypothesis_count", stats)
        self.assertEqual(stats.get("items"), 1)

    def test_hypothesis_table_not_created_when_disabled(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=False))

        with service._managed_connection() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='hypotheses'"
            ).fetchone()

        self.assertIsNone(row)

    def test_write_hypothesis_with_metadata(self) -> None:
        service = MemoryService(MemoryServiceConfig(enable_hypothesis_storage=True))
        metadata = {"source": "selector", "tag": "candidate"}

        service.write_hypothesis("h-meta", 0.42, "b1", metadata=metadata)

        with service._managed_connection() as conn:
            row = conn.execute(
                "SELECT metadata FROM hypotheses ORDER BY id DESC LIMIT 1"
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(json.loads(str(row["metadata"])), metadata)


if __name__ == "__main__":
    unittest.main()
