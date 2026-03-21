from __future__ import annotations

from v3.entry.tool_catalog import list_cli_tools
from v3.contracts.exploration import (
    BranchBoardSnapshot,
    BranchCardSnapshot,
    BranchDecisionKind,
    BranchDecisionSnapshot,
    BranchResolution,
    ExplorationMode,
    MergeOutcomeSnapshot,
    ShortlistEntrySnapshot,
)
from v3.contracts.tool_io import (
    BranchBoardGetRequest,
    BranchBoardGetResult,
    BranchFallbackRequest,
    BranchFallbackResult,
    BranchForkRequest,
    BranchForkResult,
    BranchMergeRequest,
    BranchMergeResult,
    BranchPruneRequest,
    BranchPruneResult,
    BranchSelectNextRequest,
    BranchSelectNextResult,
    BranchShareApplyRequest,
    BranchShareApplyResult,
    BranchShareAssessRequest,
    BranchShareAssessResult,
    BranchShortlistRequest,
    BranchShortlistResult,
    ConvergeRoundRequest,
    ConvergeRoundResult,
    ExploreRoundRequest,
    ExploreRoundResult,
)


def test_phase16_registry_lists_full_rd_tool_surface() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}
    assert set(tools) == {
        "rd_run_start",
        "rd_run_get",
        "rd_branch_fork",
        "rd_branch_board_get",
        "rd_branch_prune",
        "rd_branch_share_assess",
        "rd_branch_share_apply",
        "rd_branch_shortlist",
        "rd_branch_merge",
        "rd_branch_fallback",
        "rd_branch_get",
        "rd_branch_list",
        "rd_stage_get",
        "rd_artifact_list",
        "rd_recovery_assess",
        "rd_branch_select_next",
        "rd_memory_create",
        "rd_memory_get",
        "rd_memory_list",
        "rd_memory_promote",
        "rd_branch_paths_get",
        "rd_explore_round",
        "rd_converge_round",
    }


def test_phase16_tool_schemas_cover_full_rd_tool_surface() -> None:
    tools = {tool["name"]: tool for tool in list_cli_tools()}
    fork_request = BranchForkRequest.model_json_schema()
    fork_result = BranchForkResult.model_json_schema()
    board_request = BranchBoardGetRequest.model_json_schema()
    board_result = BranchBoardGetResult.model_json_schema()
    share_assess_request = BranchShareAssessRequest.model_json_schema()
    share_assess_result = BranchShareAssessResult.model_json_schema()
    share_apply_request = BranchShareApplyRequest.model_json_schema()
    share_apply_result = BranchShareApplyResult.model_json_schema()
    shortlist_request = BranchShortlistRequest.model_json_schema()
    shortlist_result = BranchShortlistResult.model_json_schema()
    merge_request = BranchMergeRequest.model_json_schema()
    merge_result = BranchMergeResult.model_json_schema()
    fallback_request = BranchFallbackRequest.model_json_schema()
    fallback_result = BranchFallbackResult.model_json_schema()
    prune_request = BranchPruneRequest.model_json_schema()
    prune_result = BranchPruneResult.model_json_schema()
    select_request = BranchSelectNextRequest.model_json_schema()
    select_result = BranchSelectNextResult.model_json_schema()
    explore_request = ExploreRoundRequest.model_json_schema()
    explore_result = ExploreRoundResult.model_json_schema()
    converge_request = ConvergeRoundRequest.model_json_schema()
    converge_result = ConvergeRoundResult.model_json_schema()
    decision_schema = BranchDecisionSnapshot.model_json_schema()
    board_schema = BranchBoardSnapshot.model_json_schema()
    merge_schema = MergeOutcomeSnapshot.model_json_schema()

    assert fork_request["properties"]["run_id"]["minLength"] == 1
    assert fork_request["properties"]["label"]["minLength"] == 1
    assert "source_branch_id" in fork_request["properties"]
    assert "branch" in fork_result["properties"]
    assert "decision" in fork_result["properties"]
    assert "workspace_root" in fork_result["properties"]

    assert board_request["properties"]["run_id"]["minLength"] == 1
    assert board_result["properties"]["board"]["$ref"].endswith("BranchBoardSnapshot")
    assert share_assess_request["properties"]["source_branch_id"]["minLength"] == 1
    assert share_assess_result["properties"]["decision"]["$ref"].endswith("BranchDecisionSnapshot")
    assert share_apply_request["properties"]["memory_id"]["minLength"] == 1
    assert share_apply_result["properties"]["board"]["$ref"].endswith("BranchBoardSnapshot")
    assert shortlist_request["properties"]["run_id"]["minLength"] == 1
    assert shortlist_result["properties"]["candidate_summary"]["$ref"].endswith("CandidateSummarySnapshot")
    assert merge_request["properties"]["run_id"]["minLength"] == 1
    assert merge_result["properties"]["outcome"]["$ref"].endswith("MergeOutcomeSnapshot")
    assert fallback_request["properties"]["run_id"]["minLength"] == 1
    assert "selected_branch_id" in fallback_result["properties"]
    assert prune_request["properties"]["run_id"]["minLength"] == 1
    assert "pruned_branch_ids" in prune_result["properties"]
    assert select_request["properties"]["run_id"]["minLength"] == 1
    assert select_result["properties"]["recommendation"]["$ref"].endswith("BranchSelectNextRecommendation")
    assert explore_request["properties"]["run_id"]["minLength"] == 1
    assert explore_result["properties"]["board"]["$ref"].endswith("BranchBoardSnapshot")
    assert converge_request["properties"]["run_id"]["minLength"] == 1
    assert converge_result["properties"]["board"]["$ref"].endswith("BranchBoardSnapshot")

    decision_kind = decision_schema["$defs"]["BranchDecisionKind"]["enum"]
    resolution = decision_schema["$defs"]["BranchResolution"]["enum"]
    mode = board_schema["$defs"]["ExplorationMode"]["enum"]

    assert BranchDecisionKind.FORK.value in decision_kind
    assert BranchDecisionKind.PRUNE.value in decision_kind
    assert BranchResolution.PRUNED.value in resolution
    assert ExplorationMode.EXPLORATION.value in mode
    assert "active_cards" in board_schema["properties"]
    assert "history_cards" in board_schema["properties"]
    assert "shortlist" in merge_schema["properties"]
    assert tools["rd_explore_round"]["inputSchema"] == explore_request
    assert tools["rd_converge_round"]["outputSchema"] == converge_result

    assert ShortlistEntrySnapshot.model_json_schema()["properties"]["rank"]["minimum"] == 1
    assert BranchCardSnapshot.model_json_schema()["properties"]["explanation"]["minLength"] == 1
