"""V3-owned public branch score projection."""

from __future__ import annotations

import math
from dataclasses import dataclass

from v3.contracts.branch import BranchScore, BranchSnapshot
from v3.contracts.recovery import RecoveryAssessment, RecoveryDisposition


@dataclass(frozen=True)
class BranchSelectionSignal:
    """Internal selection inputs projected into public V3 branch scores."""

    branch_id: str
    branch_potential: float
    sibling_potentials: tuple[float, ...]
    avg_value: float
    visits: int
    total_visits: int


def project_branch_score(signal: BranchSelectionSignal) -> BranchScore:
    """Project internal ranking inputs into the public dual-score contract."""

    exploration_priority = round(_exploration_priority(signal), 4)
    result_quality = round(_result_quality(signal.avg_value), 4)
    return BranchScore(
        exploration_priority=exploration_priority,
        result_quality=result_quality,
        rationale=_rationale(exploration_priority, result_quality),
    )


def selection_potential(branch: BranchSnapshot, recovery: RecoveryAssessment) -> float:
    """Combine branch score and recovery readiness into adapter input."""

    disposition_bonus = {
        RecoveryDisposition.REUSE: 0.3,
        RecoveryDisposition.REPLAY: 0.15,
        RecoveryDisposition.REVIEW: 0.05,
        RecoveryDisposition.REBUILD: -1.0,
    }[recovery.recovery_assessment]
    return branch.score.exploration_priority + branch.score.result_quality + disposition_bonus


def build_selection_rationale(
    branch: BranchSnapshot,
    recovery: RecoveryAssessment,
    projected_score: BranchScore,
) -> str:
    """Explain the selection outcome in V3 adapter terms."""

    disposition_text = {
        RecoveryDisposition.REUSE: "reusable now",
        RecoveryDisposition.REPLAY: "available after replay",
        RecoveryDisposition.REVIEW: "pending review",
        RecoveryDisposition.REBUILD: "blocked for rebuild",
    }[recovery.recovery_assessment]
    return (
        f"Selected via the V3 PUCT adapter because {branch.label} is {disposition_text}, "
        f"retains exploration priority {projected_score.exploration_priority:.4f}, "
        f"and has result quality {projected_score.result_quality:.4f}."
    )


def _exploration_priority(signal: BranchSelectionSignal) -> float:
    if signal.total_visits <= 0:
        return 1.0

    prior = _softmax_prior(signal.branch_potential, signal.sibling_potentials)
    visit_penalty = 1 + max(signal.visits, 0)
    return min(1.0, prior * math.sqrt(signal.total_visits) / visit_penalty)


def _softmax_prior(branch_potential: float, sibling_potentials: tuple[float, ...]) -> float:
    potentials = sibling_potentials or (branch_potential,)
    max_potential = max(potentials)
    numerator = math.exp(branch_potential - max_potential)
    denominator = sum(math.exp(potential - max_potential) for potential in potentials)
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _result_quality(avg_value: float) -> float:
    return min(1.0, max(0.0, (avg_value + 1.0) / 2.0))


def _rationale(exploration_priority: float, result_quality: float) -> str:
    if exploration_priority >= 0.5 and result_quality >= 0.7:
        return "High exploration potential with strong observed results."
    if exploration_priority >= 0.5:
        return "High exploration potential despite limited confirmed results."
    if result_quality >= 0.7:
        return "Strong observed results with moderate remaining exploration upside."
    return "Moderate exploration value with limited confirmed results so far."


def compute_generalization_signals(
    *,
    validation_score: float,
    training_score: float | None = None,
    cross_fold_variance: float | None = None,
    score_trend: float | None = None,
) -> tuple[float, float]:
    """Compute generalization gap and overfitting risk from stage results."""

    if training_score is None:
        return (0.0, 0.0)

    gap = max(0.0, training_score - validation_score)
    risk_components: list[float] = [min(1.0, gap * 2.0)]
    if cross_fold_variance is not None:
        risk_components.append(min(1.0, cross_fold_variance * 5.0))
    if score_trend is not None and score_trend < 0.0:
        risk_components.append(min(1.0, abs(score_trend) * 3.0))

    overfitting_risk = min(1.0, sum(risk_components) / len(risk_components))
    return (round(gap, 4), round(overfitting_risk, 4))


__all__ = [
    "BranchSelectionSignal",
    "build_selection_rationale",
    "compute_generalization_signals",
    "project_branch_score",
    "selection_potential",
]
