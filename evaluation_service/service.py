"""Service scaffold for the Evaluation Service module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
        self._leaderboard: dict[str, dict[str, dict[str, Any]]] = {}

    def evaluate_run(self, execution_result: ExecutionResult) -> EvalResult:
        """Evaluate an execution result against standardized metrics.

        Responsibility:
            Produce a multi-stage score per FC-5 paper.
        Input semantics:
            - execution_result: Output of execution service
        Output semantics:
            EvalResult containing Score and report reference.
        Architecture mapping:
            Evaluation Service -> evaluate_run
        """

        stages: dict[str, float] = {}

        execution_score = 1.0 if execution_result.exit_code == 0 else 0.0
        stages["execution"] = execution_score

        alignment_score = 1.0 if execution_result.artifacts_ref else 0.0
        stages["alignment"] = alignment_score

        debug_score = 0.0 if execution_result.timed_out else 1.0
        stages["debug_compliance"] = debug_score

        authenticity_score = 1.0 if execution_result.logs_ref else 0.5
        stages["authenticity"] = authenticity_score

        total = 0.4 * execution_score + 0.2 * alignment_score + 0.2 * debug_score + 0.2 * authenticity_score
        task_id = self._resolve_task_id(execution_result)
        self._leaderboard.setdefault(task_id, {})[execution_result.run_id] = {
            "score": total,
            "metrics": {**stages, "total": total, "metric_name": self._config.metric_name},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        score = Score(
            score_id=f"score-{execution_result.run_id}",
            value=total,
            metric_name=self._config.metric_name,
            details={
                "stages": (
                    "execution="
                    f"{execution_score},alignment={alignment_score},"
                    f"debug_compliance={debug_score},authenticity={authenticity_score}"
                )
            },
        )
        return EvalResult(score=score, report_ref=f"report-{execution_result.run_id}")

    def _resolve_task_id(self, execution_result: ExecutionResult) -> str:
        artifact_manifest = execution_result.artifact_manifest
        if isinstance(artifact_manifest, dict):
            task_id = artifact_manifest.get("task_id")
            if isinstance(task_id, str) and task_id.strip():
                return task_id.strip()
        return "default"

    def aggregate_branch_scores(self, scores: list[Score]) -> Score:
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

        if not scores:
            return Score(
                score_id="aggregate-score",
                value=0.0,
                metric_name=self._config.metric_name,
            )

        avg = sum(score.value for score in scores) / len(scores)
        return Score(
            score_id="aggregate-score",
            value=avg,
            metric_name=self._config.metric_name,
        )

    def get_leaderboard(self, task_id: str) -> dict[str, dict[str, Any]]:
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

        return {key: dict(value) for key, value in self._leaderboard.get(task_id, {}).items()}
