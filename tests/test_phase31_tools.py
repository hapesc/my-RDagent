"""Phase 31 CLI tool tests for finalization readiness and early finalization."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from rd_agent.contracts.exploration import FinalSubmissionSnapshot
from rd_agent.contracts.tool_io import (
    FinalizeEarlyRequest,
    FinalizeEarlyResult,
    ShouldFinalizeRequest,
    ShouldFinalizeResult,
)


def _submission() -> FinalSubmissionSnapshot:
    return FinalSubmissionSnapshot.model_validate(
        {
            "submission_id": "submission-1",
            "run_id": "run-1",
            "winner_node_id": "node-1",
            "winner_branch_id": "branch-1",
            "holdout_mean": 0.9,
            "holdout_std": 0.01,
            "ranked_candidates": [],
        }
    )


def test_list_cli_tools_includes_rd_should_finalize():
    from rd_agent.entry.tool_catalog import list_cli_tools

    names = {tool["name"] for tool in list_cli_tools()}

    assert "rd_should_finalize" in names



def test_list_cli_tools_includes_rd_finalize_early():
    from rd_agent.entry.tool_catalog import list_cli_tools

    names = {tool["name"] for tool in list_cli_tools()}

    assert "rd_finalize_early" in names



def test_get_cli_tool_rd_should_finalize_is_inspection():
    from rd_agent.entry.tool_catalog import get_cli_tool

    tool = get_cli_tool("rd_should_finalize")

    assert tool["category"] == "inspection"



def test_get_cli_tool_rd_finalize_early_is_primitives():
    from rd_agent.entry.tool_catalog import get_cli_tool

    tool = get_cli_tool("rd_finalize_early")

    assert tool["category"] == "primitives"



def test_should_finalize_request_validates_run_id():
    request = ShouldFinalizeRequest.model_validate({"run_id": "run-1"})

    assert request.run_id == "run-1"



def test_should_finalize_result_validates_payload():
    result = ShouldFinalizeResult.model_validate(
        {
            "should_finalize": True,
            "current_round": 5,
            "max_rounds": 5,
            "holdout_available": True,
        }
    )

    assert result.should_finalize is True
    assert result.current_round == 5
    assert result.max_rounds == 5
    assert result.holdout_available is True



def test_finalize_early_request_validates_run_id():
    request = FinalizeEarlyRequest.model_validate({"run_id": "run-1"})

    assert request.run_id == "run-1"



def test_finalize_early_result_validates_payload():
    result = FinalizeEarlyResult.model_validate(
        {
            "finalized": True,
            "run_id": "run-1",
            "exploration_mode": "finalized",
            "submission": _submission().model_dump(mode="json"),
        }
    )

    assert result.finalized is True
    assert result.run_id == "run-1"
    assert result.exploration_mode == "finalized"
    assert result.submission.winner_node_id == "node-1"



def test_rd_finalize_early_calls_multi_branch_service_and_returns_submission():
    from rd_agent.tools.finalization_tools import rd_finalize_early

    multi_branch_service = MagicMock()
    multi_branch_service.finalize_early.return_value = _submission()

    response = rd_finalize_early(
        FinalizeEarlyRequest(run_id="run-1"),
        multi_branch_service=multi_branch_service,
    )

    multi_branch_service.finalize_early.assert_called_once_with(run_id="run-1")
    validated = FinalizeEarlyResult.model_validate(response["structuredContent"])
    assert validated.finalized is True
    assert validated.run_id == "run-1"
    assert validated.exploration_mode == "finalized"
    assert validated.submission.winner_node_id == "node-1"



def test_rd_should_finalize_calls_multi_branch_service_and_returns_result():
    from rd_agent.tools.finalization_tools import rd_should_finalize

    multi_branch_service = MagicMock()
    multi_branch_service.should_finalize.return_value = True
    multi_branch_service.has_holdout_finalization.return_value = True
    state_store = MagicMock()
    state_store.load_run_snapshot.return_value = SimpleNamespace(current_round=5, max_rounds=5)

    response = rd_should_finalize(
        ShouldFinalizeRequest(run_id="run-1"),
        multi_branch_service=multi_branch_service,
        state_store=state_store,
    )

    multi_branch_service.should_finalize.assert_called_once_with("run-1")
    multi_branch_service.has_holdout_finalization.assert_called_once_with()
    state_store.load_run_snapshot.assert_called_once_with("run-1")
    assert response["structuredContent"] == {
        "should_finalize": True,
        "current_round": 5,
        "max_rounds": 5,
        "holdout_available": True,
    }


def test_rd_should_finalize_reports_holdout_availability_even_when_not_ready():
    from rd_agent.tools.finalization_tools import rd_should_finalize

    multi_branch_service = MagicMock()
    multi_branch_service.should_finalize.return_value = False
    multi_branch_service.has_holdout_finalization.return_value = True
    state_store = MagicMock()
    state_store.load_run_snapshot.return_value = SimpleNamespace(current_round=1, max_rounds=5)

    response = rd_should_finalize(
        ShouldFinalizeRequest(run_id="run-1"),
        multi_branch_service=multi_branch_service,
        state_store=state_store,
    )

    assert response["structuredContent"] == {
        "should_finalize": False,
        "current_round": 1,
        "max_rounds": 5,
        "holdout_available": True,
    }
