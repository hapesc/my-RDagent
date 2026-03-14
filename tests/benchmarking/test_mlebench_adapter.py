from __future__ import annotations

import unittest

from benchmarking.adapters.mlebench_adapter import MLEBenchAdapter, MLEBenchAdapterError
from benchmarking.result_schema import BenchmarkCaseResult, FailureBucket


class FakeMLEBenchGrader:
    def __init__(self, score: float = 0.83) -> None:
        self.score = score
        self.calls: list[dict] = []

    def grade_submission(self, *, competition_id: str, submission_path: str) -> dict:
        payload = {
            "competition_id": competition_id,
            "submission_path": submission_path,
            "score": self.score,
            "public_score": self.score - 0.02,
        }
        self.calls.append(payload)
        return payload


class MalformedMLEBenchGrader:
    def grade_submission(self, *, competition_id: str, submission_path: str) -> dict:
        _ = (competition_id, submission_path)
        return {"public_score": 0.1}


class ExplodingMLEBenchGrader:
    def grade_submission(self, *, competition_id: str, submission_path: str) -> dict:
        _ = (competition_id, submission_path)
        raise RuntimeError("grader boom")


class FailedMLEBenchGrader:
    def grade_submission(self, *, competition_id: str, submission_path: str) -> dict:
        _ = (competition_id, submission_path)
        return {"status": "FAILED", "error": "grader failed"}


class MLEBenchAdapterTests(unittest.TestCase):
    def test_adapter_maps_graded_case_into_benchmark_case_result(self) -> None:
        grader = FakeMLEBenchGrader(score=0.91)
        adapter = MLEBenchAdapter(grader=grader)

        result = adapter.evaluate_case(
            profile="smoke",
            task={
                "scenario": "data_science",
                "task_id": "mle-case-1",
                "reference_outputs": {"competition_id": "kaggle-playground"},
            },
            runtime_output={
                "status": "COMPLETED",
                "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                "artifacts": {"submission_path": "/tmp/submission.csv"},
            },
        )

        self.assertIsInstance(result, BenchmarkCaseResult)
        self.assertEqual(result.scenario, "data_science")
        self.assertEqual(result.task_id, "mle-case-1")
        self.assertEqual(result.failure_bucket, FailureBucket.SUCCESS)
        self.assertEqual(result.scenario_score, 0.91)
        self.assertEqual(result.scenario_metrics["public_score"], 0.89)
        self.assertEqual(result.artifact_refs["submission_path"], "/tmp/submission.csv")

    def test_adapter_raises_clear_error_when_required_assets_are_missing(self) -> None:
        adapter = MLEBenchAdapter(grader=FakeMLEBenchGrader())

        with self.assertRaisesRegex(MLEBenchAdapterError, "competition_id"):
            adapter.evaluate_case(
                profile="smoke",
                task={"scenario": "data_science", "task_id": "missing-assets", "reference_outputs": {}},
                runtime_output={
                    "status": "COMPLETED",
                    "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                    "artifacts": {"submission_path": "/tmp/submission.csv"},
                },
            )

        with self.assertRaisesRegex(MLEBenchAdapterError, "submission_path"):
            adapter.evaluate_case(
                profile="smoke",
                task={
                    "scenario": "data_science",
                    "task_id": "missing-submission",
                    "reference_outputs": {"competition_id": "kaggle-playground"},
                },
                runtime_output={
                    "status": "COMPLETED",
                    "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                    "artifacts": {},
                },
            )

    def test_adapter_wraps_grader_failures_and_malformed_results(self) -> None:
        exploding = MLEBenchAdapter(grader=ExplodingMLEBenchGrader())
        malformed = MLEBenchAdapter(grader=MalformedMLEBenchGrader())

        with self.assertRaisesRegex(MLEBenchAdapterError, "grading failed"):
            exploding.evaluate_case(
                profile="smoke",
                task={
                    "scenario": "data_science",
                    "task_id": "grader-failure",
                    "reference_outputs": {"competition_id": "kaggle-playground"},
                },
                runtime_output={
                    "status": "COMPLETED",
                    "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                    "artifacts": {"submission_path": "/tmp/submission.csv"},
                },
            )

        with self.assertRaisesRegex(MLEBenchAdapterError, "missing valid score"):
            malformed.evaluate_case(
                profile="smoke",
                task={
                    "scenario": "data_science",
                    "task_id": "malformed-grade",
                    "reference_outputs": {"competition_id": "kaggle-playground"},
                },
                runtime_output={
                    "status": "COMPLETED",
                    "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                    "artifacts": {"submission_path": "/tmp/submission.csv"},
                },
            )

        failed = MLEBenchAdapter(grader=FailedMLEBenchGrader())
        result = failed.evaluate_case(
            profile="smoke",
            task={
                "scenario": "data_science",
                "task_id": "failed-grade",
                "reference_outputs": {"competition_id": "kaggle-playground"},
            },
            runtime_output={
                "status": "COMPLETED",
                "runtime": {"llm_provider": "litellm", "llm_model": "gpt-4.1-mini", "judge_model": None},
                "artifacts": {"submission_path": "/tmp/submission.csv"},
            },
        )
        self.assertEqual(result.failure_bucket, FailureBucket.SCENARIO_EVAL_FAILURE)
        self.assertEqual(result.agent_status, "COMPLETED")


if __name__ == "__main__":
    unittest.main()
