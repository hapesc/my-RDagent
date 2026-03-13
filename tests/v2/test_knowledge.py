from __future__ import annotations

from unittest.mock import MagicMock

from v2.graph.knowledge import persist_knowledge, retrieve_knowledge


class TestPersistKnowledgeSuccess:
    def test_persist_knowledge_success(self) -> None:
        write_fn = MagicMock()

        persist_knowledge(
            write_fn=write_fn,
            iteration=3,
            hypothesis="increase learning rate",
            score=0.85,
            acceptable=True,
            reason="score above threshold",
            scenario="data_science",
        )

        write_fn.assert_called_once()
        item, metadata = write_fn.call_args[0]
        assert "[success]" in item
        assert "iteration=3" in item
        assert "increase learning rate" in item
        assert metadata["outcome"] == "success"
        assert metadata["iteration"] == "3"
        assert metadata["scenario"] == "data_science"
        assert metadata["score"] == "0.85"


class TestPersistKnowledgeFailure:
    def test_persist_knowledge_failure(self) -> None:
        write_fn = MagicMock()

        persist_knowledge(
            write_fn=write_fn,
            iteration=1,
            hypothesis="try random forest",
            score=0.2,
            acceptable=False,
            reason="score too low",
            scenario="quant",
        )

        write_fn.assert_called_once()
        item, metadata = write_fn.call_args[0]
        assert "[failure]" in item
        assert "iteration=1" in item
        assert "try random forest" in item
        assert metadata["outcome"] == "failure"
        assert metadata["iteration"] == "1"
        assert metadata["scenario"] == "quant"
        assert metadata["score"] == "0.2"


class TestRetrieveKnowledge:
    def test_retrieve_knowledge_returns_list(self) -> None:
        entries = [{"id": i} for i in range(10)]
        result = retrieve_knowledge(entries, limit=5)
        assert len(result) == 5
        assert result == entries[:5]

    def test_retrieve_knowledge_fewer_than_limit(self) -> None:
        entries = [{"id": 1}, {"id": 2}]
        result = retrieve_knowledge(entries, limit=5)
        assert len(result) == 2

    def test_retrieve_knowledge_empty(self) -> None:
        result = retrieve_knowledge([], limit=5)
        assert result == []
