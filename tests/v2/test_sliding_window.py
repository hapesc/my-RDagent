from __future__ import annotations

from v2.state import HISTORY_WINDOW_SIZE, sliding_window_reducer


def test_reducer_appends_when_under_window():
    existing = [{"iteration": 0, "hypothesis": "h0", "score": 0.5, "outcome": "ok"}]
    new = [{"iteration": 1, "hypothesis": "h1", "score": 0.6, "outcome": "ok"}]
    result = sliding_window_reducer(existing, new)
    assert len(result) == 2
    assert result[1]["hypothesis"] == "h1"


def test_reducer_compresses_old_when_over_window():
    entries = [
        {"iteration": i, "hypothesis": f"h{i}", "score": 0.1 * i, "outcome": "ok", "detail": "verbose"}
        for i in range(HISTORY_WINDOW_SIZE + 3)
    ]
    result = sliding_window_reducer(entries, [])
    recent = result[-HISTORY_WINDOW_SIZE:]
    assert all("outcome" in e for e in recent)
    compressed = result[:-HISTORY_WINDOW_SIZE]
    assert all("detail" not in e for e in compressed)
    assert len(compressed) <= 3


def test_reducer_handles_empty():
    assert sliding_window_reducer([], []) == []
