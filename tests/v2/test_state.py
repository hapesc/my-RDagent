from __future__ import annotations

import operator
from typing import Optional, get_args, get_origin, get_type_hints

from v2.state import CoSTEERState, ExplorationState, MainState


def test_main_state_has_required_fields() -> None:
    hints = get_type_hints(MainState)
    assert hints["run_id"] is str
    assert hints["loop_iteration"] is int
    assert hints["max_loops"] is int
    assert hints["step_state"] is str
    assert hints["proposal"] == Optional[dict]
    assert hints["experiment"] == Optional[dict]
    assert hints["code_result"] == Optional[dict]
    assert hints["run_result"] == Optional[dict]
    assert hints["feedback"] == Optional[dict]
    assert hints["metrics"] == Optional[dict]
    assert hints["error"] == Optional[str]


def test_costeer_state_extends_main_state_and_has_reducer() -> None:
    hints = get_type_hints(CoSTEERState)
    assert hints["round_number"] is int
    assert hints["max_rounds"] is int
    assert hints["code_candidates"] == list[dict]
    assert hints["best_candidate"] == Optional[dict]

    resolved_hints = get_type_hints(CoSTEERState, include_extras=True)
    reducer_annotated = resolved_hints["improvement_history"]
    assert get_origin(reducer_annotated) is not None
    assert get_origin(reducer_annotated).__name__ == "Annotated"
    annotated_args = get_args(reducer_annotated)
    assert annotated_args[0] == list[dict]
    assert annotated_args[1] is operator.add


def test_exploration_state_supports_dag_parent_branches() -> None:
    hints = get_type_hints(ExplorationState)
    assert hints["branch_id"] is str
    assert hints["parent_branch_ids"] == list[str]
    assert hints["branch_state"] is str
    assert hints["reward"] == Optional[float]
