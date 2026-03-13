from __future__ import annotations

from collections.abc import Callable


def persist_knowledge(
    *,
    write_fn: Callable[[str, dict], None],
    iteration: int,
    hypothesis: str,
    score: float | None,
    acceptable: bool,
    reason: str,
    scenario: str,
) -> None:
    """Persist a knowledge entry (success or failure) via the provided write function."""
    outcome = "success" if acceptable else "failure"
    item = f"[{outcome}] iteration={iteration}: {hypothesis} (score={score}) — {reason[:300]}"
    metadata = {
        "iteration": str(iteration),
        "outcome": outcome,
        "scenario": scenario,
        "score": str(score if score is not None else 0),
    }
    write_fn(item, metadata)


def retrieve_knowledge(past_entries: list[dict], limit: int = 5) -> list[dict]:
    """Return up to ``limit`` entries from the knowledge store."""
    return past_entries[:limit]


__all__ = ["persist_knowledge", "retrieve_knowledge"]
