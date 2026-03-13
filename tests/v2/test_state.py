from __future__ import annotations

import operator
import sys
from typing import Annotated, Union, get_args, get_origin, get_type_hints

from v2.state import CoSTEERState, ExplorationState, MainState


def _is_optional_of(hint, expected_type: type) -> bool:
    """Check if hint is Optional[expected_type], handling both Union and UnionType."""
    origin = get_origin(hint)
    args = get_args(hint)
    # Handle both typing.Union (Py3.9) and types.UnionType (Py3.10+)
    is_union = origin is Union or (sys.version_info >= (3, 10) and isinstance(hint, type(int | None)))
    if not is_union:
        return False
    return args == (expected_type, type(None))


def test_main_state_has_required_fields() -> None:
    hints = get_type_hints(MainState)
    assert hints["run_id"] is str
    assert hints["loop_iteration"] is int
    assert hints["max_loops"] is int
    assert hints["step_state"] is str
    assert _is_optional_of(hints["proposal"], dict)
    assert _is_optional_of(hints["experiment"], dict)
    assert _is_optional_of(hints["code_result"], dict)
    assert _is_optional_of(hints["run_result"], dict)
    assert _is_optional_of(hints["feedback"], dict)
    assert _is_optional_of(hints["metrics"], list[dict])
    assert _is_optional_of(hints["error"], str)


def test_costeer_state_extends_main_state_and_has_reducer() -> None:
    hints = get_type_hints(CoSTEERState)
    assert hints["round_number"] is int
    assert hints["max_rounds"] is int
    assert hints["code_candidates"] == list[dict]  # resolved without extras strips Annotated
    assert _is_optional_of(hints["best_candidate"], dict)

    resolved_hints = get_type_hints(CoSTEERState, include_extras=True)

    # code_candidates reducer
    code_cand_annotated = resolved_hints["code_candidates"]
    assert get_origin(code_cand_annotated) is not None
    assert get_origin(code_cand_annotated).__name__ == "Annotated"
    code_cand_args = get_args(code_cand_annotated)
    assert code_cand_args[0] == list[dict]
    assert code_cand_args[1] is operator.add

    # improvement_history reducer
    reducer_annotated = resolved_hints["improvement_history"]
    assert get_origin(reducer_annotated) is not None
    assert get_origin(reducer_annotated).__name__ == "Annotated"
    annotated_args = get_args(reducer_annotated)
    assert annotated_args[0] == list[dict]
    assert annotated_args[1] is operator.add


def test_main_state_has_token_tracking_fields() -> None:
    hints = get_type_hints(MainState, include_extras=True)
    assert "tokens_used" in hints
    assert "token_budget" in hints

    meta = hints["tokens_used"]
    assert get_origin(meta) is Annotated
    args = get_args(meta)
    assert args[0] is int
    assert args[1] is operator.add


def test_exploration_state_supports_dag_parent_branches() -> None:
    hints = get_type_hints(ExplorationState)
    assert hints["branch_id"] is str
    assert hints["parent_branch_ids"] == list[str]
    assert hints["branch_state"] is str
    assert _is_optional_of(hints["reward"], float)
