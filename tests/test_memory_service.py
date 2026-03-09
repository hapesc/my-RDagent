from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_service import MemoryService, MemoryServiceConfig


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


if __name__ == "__main__":
    unittest.main()
