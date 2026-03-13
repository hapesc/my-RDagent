from __future__ import annotations

BUDGET_THRESHOLD = 0.85


def budget_check(state: dict) -> str:
    """Return 'over_budget' when token usage exceeds the threshold, else 'continue'.

    If ``token_budget`` is zero or missing the check is disabled (always continue).
    """
    budget = state.get("token_budget", 0)
    if budget <= 0:
        return "continue"
    used = state.get("tokens_used", 0)
    if used > budget * BUDGET_THRESHOLD:
        return "over_budget"
    return "continue"


__all__ = ["budget_check", "BUDGET_THRESHOLD"]
