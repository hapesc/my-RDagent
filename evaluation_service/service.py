"""Service scaffold for the Evaluation Service module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from data_models import EvalResult, ExecutionResult, Score


@dataclass
class EvaluationServiceConfig:
    """Configuration for evaluation metrics and split enforcement."""

    metric_name: str = "placeholder_metric"
    split_policy_id: str = "fixed_split"


class EvaluationService:
    """Computes standardized evaluation scores and rankings."""

    def __init__(self, config: EvaluationServiceConfig) -> None:
        """Initialize evaluation service with metric settings."""

        self._config = config

    def evaluate_run(self, execution_result: ExecutionResult) -> EvalResult:
        """Evaluate an execution result against standardized metrics.

        Responsibility:
            Produce a placeholder score and report reference.
        Input semantics:
            - execution_result: Output of execution service
        Output semantics:
            EvalResult containing Score and report reference.
        Architecture mapping:
            Evaluation Service -> evaluate_run
        """

        _ = execution_result
        score = Score(score_id="score-placeholder", value=0.0, metric_name=self._config.metric_name)
        return EvalResult(score=score, report_ref="report-placeholder")

    def aggregate_branch_scores(self, scores: List[Score]) -> Score:
        """Aggregate scores from multiple branches.

        Responsibility:
            Combine branch scores into a placeholder aggregate score.
        Input semantics:
            - scores: List of Score objects
        Output semantics:
            Aggregate Score.
        Architecture mapping:
            Evaluation Service -> aggregate_branch_scores
        """

        _ = scores
        return Score(score_id="aggregate-score", value=0.0, metric_name=self._config.metric_name)

    def get_leaderboard(self, task_id: str) -> Dict[str, float]:
        """Return leaderboard entries for a task.

        Responsibility:
            Provide a placeholder leaderboard mapping.
        Input semantics:
            - task_id: Identifier for the task
        Output semantics:
            Mapping of solution IDs to scores.
        Architecture mapping:
            Evaluation Service -> get_leaderboard
        """

        _ = task_id
        return {}
