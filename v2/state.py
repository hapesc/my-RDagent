from __future__ import annotations

import operator
from typing import Annotated, TypedDict


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
    improvement_history: Annotated[list[dict], operator.add]


class ExplorationState(TypedDict):
    branch_id: str
    parent_branch_ids: list[str]
    branch_state: str
    reward: float | None


__all__ = ["MainState", "CoSTEERState", "ExplorationState"]
