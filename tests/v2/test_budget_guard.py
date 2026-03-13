from __future__ import annotations

from v2.graph.budget_guard import budget_check


def test_budget_check_returns_continue_when_under_budget() -> None:
    state = {"tokens_used": 500, "token_budget": 1000}
    assert budget_check(state) == "continue"


def test_budget_check_returns_over_budget_at_85_percent() -> None:
    state = {"tokens_used": 860, "token_budget": 1000}
    assert budget_check(state) == "over_budget"


def test_budget_check_returns_continue_when_budget_is_zero() -> None:
    state = {"tokens_used": 999999, "token_budget": 0}
    assert budget_check(state) == "continue"


def test_budget_check_returns_continue_when_tokens_used_missing() -> None:
    state: dict = {"token_budget": 1000}
    assert budget_check(state) == "continue"


def test_budget_check_returns_continue_at_exactly_85_percent() -> None:
    state = {"tokens_used": 850, "token_budget": 1000}
    assert budget_check(state) == "continue"


def test_budget_check_returns_over_budget_when_exceeds_total() -> None:
    state = {"tokens_used": 1200, "token_budget": 1000}
    assert budget_check(state) == "over_budget"
