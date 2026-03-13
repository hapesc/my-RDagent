from __future__ import annotations

import operator
from typing import Annotated, TypedDict

MAX_COSTEER_FEEDBACK_ENTRIES = 5


def capped_feedback_reducer(existing: list, new: list) -> list:
    """Merge feedback lists, compressing old entries when the cap is exceeded.

    Keeps the most recent *MAX_COSTEER_FEEDBACK_ENTRIES* entries in full.
    Older entries beyond the cap are compressed to just ``round`` and ``score``
    (up to 3 compressed summaries are retained).
    """
    combined = existing + new
    if len(combined) <= MAX_COSTEER_FEEDBACK_ENTRIES:
        return combined
    keep_full = combined[-MAX_COSTEER_FEEDBACK_ENTRIES:]
    compress = combined[:-MAX_COSTEER_FEEDBACK_ENTRIES]
    compressed = [{"round": e.get("round"), "score": e.get("score")} for e in compress]
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
    tokens_used: Annotated[int, operator.add]
    token_budget: int


class CoSTEERState(MainState):
    round_number: int
    max_rounds: int
    code_candidates: Annotated[list[dict], operator.add]
    best_candidate: dict | None
    improvement_history: Annotated[list[dict], capped_feedback_reducer]


class ExplorationState(TypedDict):
    branch_id: str
    parent_branch_ids: list[str]
    branch_state: str
    reward: float | None


__all__ = [
    "MainState",
    "CoSTEERState",
    "ExplorationState",
    "MAX_COSTEER_FEEDBACK_ENTRIES",
    "capped_feedback_reducer",
]
