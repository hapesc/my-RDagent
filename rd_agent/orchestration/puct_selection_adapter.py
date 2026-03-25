"""Explicit Phase 16 adapter around self-contained V3 PUCT scheduling."""

from __future__ import annotations

from dataclasses import dataclass

from rd_agent.algorithms.puct import PuctCandidate, select_next_candidate


@dataclass(frozen=True)
class PUCTBranchCandidate:
    """Minimal adapter input for V3 branch candidates."""

    branch_id: str
    potential: float
    avg_value: float
    visits: int


class PuctSelectionAdapter:
    """Limits selection to a narrow V3-owned seam."""

    def __init__(self, c_puct: float = 1.41) -> None:
        self._c_puct = c_puct

    def select_next_branch(self, candidates: list[PUCTBranchCandidate]) -> str | None:
        return select_next_candidate(
            [
                PuctCandidate(
                    branch_id=candidate.branch_id,
                    potential=candidate.potential,
                    avg_value=candidate.avg_value,
                    visits=max(candidate.visits, 0),
                )
                for candidate in candidates
            ],
            c_puct=self._c_puct,
        )


__all__ = ["PUCTBranchCandidate", "PuctSelectionAdapter"]
