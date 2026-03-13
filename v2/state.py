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
    iteration_history: Annotated[list[dict], sliding_window_reducer]


class CoSTEERState(MainState):
    round_number: int
    max_rounds: int
    code_candidates: Annotated[list[dict], operator.add]
    best_candidate: dict | None
    improvement_history: Annotated[list[dict], capped_feedback_reducer]


class CoSTEERInput(TypedDict):
    proposal_summary: str
    initial_code: str
    scenario_context: dict
    max_rounds: int


class CoSTEEROutput(TypedDict):
    final_code: str
    feedback_summary: str
    rounds_used: int
    best_score: float | None


class ExplorationState(TypedDict):
    branch_id: str
    parent_branch_ids: list[str]
    branch_state: str
    reward: float | None


__all__ = [
    "MainState",
    "CoSTEERState",
    "CoSTEERInput",
    "CoSTEEROutput",
    "ExplorationState",
    "sliding_window_reducer",
    "HISTORY_WINDOW_SIZE",
    "MAX_COSTEER_FEEDBACK_ENTRIES",
    "capped_feedback_reducer",
]
