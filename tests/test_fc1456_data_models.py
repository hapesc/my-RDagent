"""Tests for FC-1/4/5/6 dataclass extensions (TDD: RED phase)."""

from data_models import (
    ArtifactVerificationStatus,
    BudgetLedger,
    ContextPack,
    ExecutionResult,
    ProcessExecutionStatus,
    UsefulnessEligibilityStatus,
)


class TestBudgetLedger:
    """Test BudgetLedger with new fields."""

    def test_budget_ledger_default_construction(self):
        """Test backward compatibility: BudgetLedger with minimal args."""
        budget = BudgetLedger(total_time_budget=100.0)
        assert budget.total_time_budget == 100.0
        assert budget.elapsed_time == 0.0
        assert budget.iteration_durations == []
        assert budget.estimated_remaining == 0.0

    def test_budget_ledger_with_new_fields(self):
        """Test BudgetLedger with iteration_durations and estimated_remaining."""
        budget = BudgetLedger(total_time_budget=100, iteration_durations=[10.0, 12.0], estimated_remaining=78.0)
        assert budget.total_time_budget == 100
        assert budget.iteration_durations == [10.0, 12.0]
        assert budget.estimated_remaining == 78.0


class TestContextPack:
    """Test ContextPack with new fields."""

    def test_context_pack_default_construction(self):
        """Test backward compatibility: ContextPack() with no args."""
        pack = ContextPack()
        assert pack.items == []
        assert pack.highlights == []
        assert pack.scored_items == []

    def test_context_pack_with_scored_items(self):
        """Test ContextPack with scored_items field."""
        scored = [("hyp1", 0.8), ("hyp2", 0.6)]
        pack = ContextPack(scored_items=scored)
        assert len(pack.scored_items) == 2
        assert pack.scored_items == scored


class TestExecutionResult:
    """Test ExecutionResult with new fields."""

    def test_execution_result_default_construction(self):
        """Test backward compatibility: ExecutionResult minimal args."""
        result = ExecutionResult(run_id="r1", exit_code=0, logs_ref="l", artifacts_ref="a")
        assert result.run_id == "r1"
        assert result.exit_code == 0
        assert result.logs_ref == "l"
        assert result.artifacts_ref == "a"
        assert result.duration_sec == 0.0
        assert result.timed_out is False

    def test_execution_result_with_new_fields(self):
        """Test ExecutionResult with duration_sec and timed_out."""
        result = ExecutionResult(
            run_id="r1", exit_code=0, logs_ref="l", artifacts_ref="a", duration_sec=12.5, timed_out=True
        )
        assert result.duration_sec == 12.5
        assert result.timed_out is True

    def test_execution_result_contract_rejects_false_success(self):
        result = ExecutionResult(
            run_id="r-false-success",
            exit_code=0,
            logs_ref="ok",
            artifacts_ref="[]",
        )
        outcome = result.resolve_outcome()
        assert outcome.process_status == ProcessExecutionStatus.SUCCESS
        assert outcome.artifact_status == ArtifactVerificationStatus.MISSING_REQUIRED
        assert outcome.usefulness_status == UsefulnessEligibilityStatus.INELIGIBLE

    def test_execution_result_contract_accepts_real_success(self):
        result = ExecutionResult(
            run_id="r-real-success",
            exit_code=0,
            logs_ref="ok",
            artifacts_ref='["metrics.json"]',
        )
        outcome = result.resolve_outcome()
        assert outcome.process_status == ProcessExecutionStatus.SUCCESS
        assert outcome.artifact_status == ArtifactVerificationStatus.VERIFIED
        assert outcome.usefulness_status == UsefulnessEligibilityStatus.ELIGIBLE

    def test_execution_result_contract_rejects_malformed_manifest(self):
        result = ExecutionResult(
            run_id="r-malformed",
            exit_code=0,
            logs_ref="ok",
            artifacts_ref="not-json",
        )
        outcome = result.resolve_outcome()
        assert outcome.process_status == ProcessExecutionStatus.SUCCESS
        assert outcome.artifact_status == ArtifactVerificationStatus.MALFORMED_REQUIRED
        assert outcome.usefulness_status == UsefulnessEligibilityStatus.INELIGIBLE
