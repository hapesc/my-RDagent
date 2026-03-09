"""Reward calculation for MCTS backpropagation (FC-2).

Supports score-based (tanh normalization) and decision-based modes,
matching the official RDAgent trace_scheduler reward computation.
"""

from __future__ import annotations

import math
from typing import Optional


class RewardCalculator:
    """Calculate reward for MCTS backpropagation.

    Modes:
        score_based: reward = tanh(score) * direction
        decision_based: reward = 1.0 if decision else 0.0

    Args:
        mode: "score_based" or "decision_based"
        direction: 1 for bigger_is_better, -1 for smaller_is_better
    """

    def __init__(self, mode: str = "score_based", direction: int = 1) -> None:
        self._mode = mode
        self._direction = direction

    def calculate(self, score: Optional[float], decision: Optional[bool]) -> float:
        """Calculate reward based on score or decision.

        Args:
            score: Numeric score (used in score_based mode)
            decision: Boolean decision (used in decision_based mode or fallback)

        Returns:
            Reward value (typically 0.0 to 1.0 for score_based, 0.0 or 1.0 for decision_based)
        """
        if self._mode == "score_based":
            if score is not None:
                return math.tanh(score) * self._direction
            # Fall back to decision-based when score is None
            if decision is not None:
                return 1.0 if decision else 0.0
            return 0.0
        elif self._mode == "decision_based":
            if decision is not None:
                return 1.0 if decision else 0.0
            return 0.0
        return 0.0
