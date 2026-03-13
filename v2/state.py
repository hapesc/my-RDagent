from __future__ import annotations

import operator
from typing import Annotated, TypedDict

HISTORY_WINDOW_SIZE = 5


def sliding_window_reducer(existing: list, new: list) -> list:
    """Keep recent iterations full and compress older ones.

    The most recent ``HISTORY_WINDOW_SIZE`` entries are kept intact.
    Older entries are compressed to only ``iteration``, ``hypothesis``,
    and ``score`` fields, and at most 3 compressed entries are retained.
    """
    combined = existing + new
    if len(combined) <= HISTORY_WINDOW_SIZE:
        return combined
    keep_full = combined[-HISTORY_WINDOW_SIZE:]
    compress = combined[:-HISTORY_WINDOW_SIZE]
    compressed = [
        {"iteration": e.get("iteration"), "hypothesis": e.get("hypothesis"), "score": e.get("score")}
        for e in compress
    ]
    return compressed[-3:] + keep_full


class MainState(TypedDict):
    run_id: str
    loop_iteration: int
    max_loops: int
    step_state: str
    proposal: dict | None
    experiment: dict | None
    code_result: dict | None
    run_result: dict | None
    feedback: dict | None
    metrics: list[dict] | None
    error: str | None
    iteration_history: Annotated[list[dict], sliding_window_reducer]


class CoSTEERState(MainState):
    round_number: int
    max_rounds: int
    code_candidates: Annotated[list[dict], operator.add]
    best_candidate: dict | None
    improvement_history: Annotated[list[dict], operator.add]


class ExplorationState(TypedDict):
    branch_id: str
    parent_branch_ids: list[str]
    branch_state: str
    reward: float | None


__all__ = ["MainState", "CoSTEERState", "ExplorationState", "sliding_window_reducer", "HISTORY_WINDOW_SIZE"]
