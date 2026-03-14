"""MLE-bench scoring adapter for data_science benchmark cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from benchmarking.result_schema import BenchmarkCaseResult, FailureBucket


class MLEBenchGrader(Protocol):
    def grade_submission(self, *, competition_id: str, submission_path: str) -> dict[str, Any]: ...


class MLEBenchAdapterError(ValueError):
    """Raised when a benchmark case cannot be evaluated by the MLE-bench adapter."""


@dataclass
class MLEBenchAdapter:
    grader: MLEBenchGrader

    def evaluate_case(
        self,
        *,
        profile: str,
        task: dict[str, Any],
        runtime_output: dict[str, Any],
    ) -> BenchmarkCaseResult:
        reference_outputs = dict(task.get("reference_outputs", {}))
        artifacts = dict(runtime_output.get("artifacts", {}))
        runtime_meta = dict(runtime_output.get("runtime", {}))

        competition_id = reference_outputs.get("competition_id")
        if not competition_id:
            raise MLEBenchAdapterError("missing required MLE-bench asset: competition_id")

        submission_path = artifacts.get("submission_path")
        if not submission_path:
            raise MLEBenchAdapterError("missing required MLE-bench asset: submission_path")

        try:
            graded = self.grader.grade_submission(
                competition_id=str(competition_id),
                submission_path=str(submission_path),
            )
        except Exception as exc:
            raise MLEBenchAdapterError(f"MLE-bench grading failed: {exc}") from exc

        try:
            score = float(graded["score"])
        except (KeyError, TypeError, ValueError) as exc:
            status = str(graded.get("status", "")).upper()
            if status and status not in {"SUCCESS", "COMPLETED"}:
                return BenchmarkCaseResult(
                    scenario=str(task.get("scenario", "data_science")),
                    task_id=str(task["task_id"]),
                    profile=profile,
                    agent_status=str(runtime_output.get("status", "UNKNOWN")),
                    llm_provider=str(runtime_meta.get("llm_provider", "")),
                    llm_model=str(runtime_meta.get("llm_model", "")),
                    judge_model=runtime_meta.get("judge_model"),
                    failure_bucket=FailureBucket.SCENARIO_EVAL_FAILURE,
                    scenario_score=None,
                    scenario_metrics={k: v for k, v in graded.items() if k != "score"},
                    artifact_refs={"submission_path": str(submission_path)},
                )
            raise MLEBenchAdapterError("MLE-bench grading result missing valid score") from exc

        return BenchmarkCaseResult(
            scenario=str(task.get("scenario", "data_science")),
            task_id=str(task["task_id"]),
            profile=profile,
            agent_status=str(runtime_output.get("status", "UNKNOWN")),
            llm_provider=str(runtime_meta.get("llm_provider", "")),
            llm_model=str(runtime_meta.get("llm_model", "")),
            judge_model=runtime_meta.get("judge_model"),
            failure_bucket=FailureBucket.SUCCESS,
            scenario_score=score,
            scenario_metrics={key: value for key, value in graded.items() if key not in {"score"}},
            artifact_refs={"submission_path": str(submission_path)},
        )
