from __future__ import annotations

from v2.state import MAX_COSTEER_FEEDBACK_ENTRIES, capped_feedback_reducer


def test_reducer_appends_when_under_limit() -> None:
    existing = [{"round": 0, "score": 0.5, "output": "full log"}]
    new = [{"round": 1, "score": 0.7, "output": "another log"}]
    result = capped_feedback_reducer(existing, new)
    assert len(result) == 2
    assert result[1]["output"] == "another log"


def test_reducer_compresses_old_entries_when_over_limit() -> None:
    existing = [{"round": i, "score": 0.1 * i, "output": f"log-{i}"} for i in range(5)]
    new = [{"round": 5, "score": 0.9, "output": "latest"}]
    result = capped_feedback_reducer(existing, new)
    assert result[-1]["output"] == "latest"
    compressed = [e for e in result if "output" not in e]
    assert len(compressed) >= 1


def test_reducer_handles_empty_existing() -> None:
    result = capped_feedback_reducer([], [{"round": 0, "score": 0.5}])
    assert len(result) == 1


def test_reducer_preserves_cap_size() -> None:
    """Total full entries never exceed MAX_COSTEER_FEEDBACK_ENTRIES."""
    existing = [{"round": i, "score": 0.1 * i, "output": f"log-{i}"} for i in range(10)]
    new = [{"round": 10, "score": 1.0, "output": "new"}]
    result = capped_feedback_reducer(existing, new)
    full_entries = [e for e in result if "output" in e]
    assert len(full_entries) <= MAX_COSTEER_FEEDBACK_ENTRIES


def test_reducer_compressed_entries_only_have_round_and_score() -> None:
    existing = [{"round": i, "score": 0.1 * i, "output": f"log-{i}", "code": "x"} for i in range(8)]
    new = [{"round": 8, "score": 0.9, "output": "latest"}]
    result = capped_feedback_reducer(existing, new)
    compressed = [e for e in result if "output" not in e]
    for entry in compressed:
        assert set(entry.keys()) == {"round", "score"}
