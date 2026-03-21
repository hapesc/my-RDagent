"""CLI-oriented V3 tool catalog.

This module owns the schema-described V3 tool surface used by skill entrypoints
and CLI-facing tooling. It intentionally avoids any MCP transport/server
semantics; the catalog is an in-process dispatch layer over V3-owned handlers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from v3.contracts.artifact import ArtifactSnapshot
from v3.contracts.branch import BranchSnapshot
from v3.contracts.run import RunBoardSnapshot
from v3.contracts.stage import StageSnapshot
from v3.contracts.tool_io import (
    ArtifactListRequest,
    ArtifactListResult,
    BranchBoardGetRequest,
    BranchBoardGetResult,
    BranchFallbackRequest,
    BranchFallbackResult,
    BranchForkRequest,
    BranchForkResult,
    BranchGetRequest,
    BranchGetResult,
    BranchListRequest,
    BranchListResult,
    BranchPathsGetRequest,
    BranchPathsGetResult,
    BranchPruneRequest,
    BranchPruneResult,
    BranchShortlistRequest,
    BranchShortlistResult,
    BranchMergeRequest,
    BranchMergeResult,
    BranchShareApplyRequest,
    BranchShareApplyResult,
    BranchShareAssessRequest,
    BranchShareAssessResult,
    BranchSelectNextRequest,
    BranchSelectNextResult,
    ConvergeRoundRequest,
    ConvergeRoundResult,
    ExploreRoundRequest,
    ExploreRoundResult,
    MemoryCreateRequest,
    MemoryGetRequest,
    MemoryGetResult,
    MemoryListRequest,
    MemoryListResult,
    MemoryPromoteRequest,
    RecoveryAssessRequest,
    RecoveryAssessResult,
    RunGetRequest,
    RunGetResult,
    RunStartRequest,
    StageGetRequest,
    StageGetResult,
)
from v3.tools.artifact_tools import rd_artifact_list
from v3.tools.branch_tools import rd_branch_get, rd_branch_list
from v3.tools.exploration_tools import (
    rd_branch_board_get,
    rd_branch_fallback,
    rd_branch_fork,
    rd_branch_merge,
    rd_branch_prune,
    rd_branch_share_apply,
    rd_branch_share_assess,
    rd_branch_shortlist,
)
from v3.tools.isolation_tools import rd_branch_paths_get
from v3.tools.memory_tools import rd_memory_create, rd_memory_get, rd_memory_list, rd_memory_promote
from v3.tools.orchestration_tools import rd_converge_round, rd_explore_round
from v3.tools.recovery_tools import rd_recovery_assess
from v3.tools.run_tools import rd_run_get, rd_run_start
from v3.tools.selection_tools import rd_branch_select_next
from v3.tools.stage_tools import rd_stage_get


class RunStartToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run: RunBoardSnapshot
    branch: BranchSnapshot
    stage: StageSnapshot
    artifacts: list[ArtifactSnapshot]


@dataclass(frozen=True)
class _ToolSpec:
    name: str
    title: str
    description: str
    handler: Callable[..., dict[str, Any]]
    request_model: type[BaseModel]
    response_model: type[BaseModel]
    dependency_names: tuple[str, ...]


_TOOL_SPECS: tuple[_ToolSpec, ...] = (
    _ToolSpec(
        name="rd_run_start",
        title="Start V3 Run",
        description="Start a V3 run and publish the initial run, branch, stage, and artifact truth.",
        handler=rd_run_start,
        request_model=RunStartRequest,
        response_model=RunStartToolResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_run_get",
        title="Get V3 Run",
        description="Load the canonical V3 run-board snapshot.",
        handler=rd_run_get,
        request_model=RunGetRequest,
        response_model=RunGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_fork",
        title="Fork V3 Branch",
        description="Create a labeled Phase 16 branch fork with isolated workspace allocation.",
        handler=rd_branch_fork,
        request_model=BranchForkRequest,
        response_model=BranchForkResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_board_get",
        title="Get V3 Branch Board",
        description="Load the Phase 16 active/history branch board read model.",
        handler=rd_branch_board_get,
        request_model=BranchBoardGetRequest,
        response_model=BranchBoardGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_prune",
        title="Prune V3 Branches",
        description="Prune low-quality Phase 16 branches while preserving at least one active branch.",
        handler=rd_branch_prune,
        request_model=BranchPruneRequest,
        response_model=BranchPruneResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_share_assess",
        title="Assess V3 Branch Share",
        description="Assess whether one Phase 16 branch should share knowledge with another.",
        handler=rd_branch_share_assess,
        request_model=BranchShareAssessRequest,
        response_model=BranchShareAssessResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_share_apply",
        title="Apply V3 Branch Share",
        description="Promote eligible branch knowledge through the Phase 15 memory contract.",
        handler=rd_branch_share_apply,
        request_model=BranchShareApplyRequest,
        response_model=BranchShareApplyResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_shortlist",
        title="Build V3 Branch Shortlist",
        description="Build the candidate summary and quality-ordered shortlist for convergence.",
        handler=rd_branch_shortlist,
        request_model=BranchShortlistRequest,
        response_model=BranchShortlistResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_merge",
        title="Merge V3 Branches",
        description="Attempt a convergence merge over the Phase 16 shortlist.",
        handler=rd_branch_merge,
        request_model=BranchMergeRequest,
        response_model=BranchMergeResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_fallback",
        title="Fallback to Top V3 Branch",
        description="Choose the top-ranked branch when merge quality degrades.",
        handler=rd_branch_fallback,
        request_model=BranchFallbackRequest,
        response_model=BranchFallbackResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_get",
        title="Get V3 Branch",
        description="Load a canonical V3 branch snapshot.",
        handler=rd_branch_get,
        request_model=BranchGetRequest,
        response_model=BranchGetResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_branch_list",
        title="List V3 Branches",
        description="List canonical V3 branches for a run.",
        handler=rd_branch_list,
        request_model=BranchListRequest,
        response_model=BranchListResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_stage_get",
        title="Get V3 Stage",
        description="Load branch-stage state and published artifacts in V3 terms.",
        handler=rd_stage_get,
        request_model=StageGetRequest,
        response_model=StageGetResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_artifact_list",
        title="List V3 Artifacts",
        description="List canonical V3 artifacts for a run, branch, or stage.",
        handler=rd_artifact_list,
        request_model=ArtifactListRequest,
        response_model=ArtifactListResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_recovery_assess",
        title="Assess V3 Recovery",
        description="Assess V3 branch-stage recovery readiness without legacy checkpoint leakage.",
        handler=rd_recovery_assess,
        request_model=RecoveryAssessRequest,
        response_model=RecoveryAssessResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_select_next",
        title="Select Next V3 Branch",
        description="Recommend the next V3 branch to advance from public branch and recovery state.",
        handler=rd_branch_select_next,
        request_model=BranchSelectNextRequest,
        response_model=BranchSelectNextResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_memory_create",
        title="Create V3 Memory",
        description="Create a branch-owned V3 memory record for the current run and stage.",
        handler=rd_memory_create,
        request_model=MemoryCreateRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_get",
        title="Get V3 Memory",
        description="Load a V3 memory record with branch-local and shared promotion context.",
        handler=rd_memory_get,
        request_model=MemoryGetRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_list",
        title="List V3 Memory",
        description="List branch-local and shared V3 memory matches for a branch-stage query.",
        handler=rd_memory_list,
        request_model=MemoryListRequest,
        response_model=MemoryListResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_promote",
        title="Promote V3 Memory",
        description="Promote eligible V3 memory into the shared namespace without leaking legacy checkpoints.",
        handler=rd_memory_promote,
        request_model=MemoryPromoteRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_paths_get",
        title="Get V3 Branch Paths",
        description="Expose canonical branch-local and shared Phase 15 storage roots for a run branch.",
        handler=rd_branch_paths_get,
        request_model=BranchPathsGetRequest,
        response_model=BranchPathsGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_explore_round",
        title="Run V3 Explore Round",
        description="Run a high-level Phase 16 exploration round over the active branch frontier.",
        handler=rd_explore_round,
        request_model=ExploreRoundRequest,
        response_model=ExploreRoundResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_converge_round",
        title="Run V3 Converge Round",
        description="Run a high-level Phase 16 convergence round over the current shortlist.",
        handler=rd_converge_round,
        request_model=ConvergeRoundRequest,
        response_model=ConvergeRoundResult,
        dependency_names=("service",),
    ),
)


def _catalog_entry(spec: _ToolSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "title": spec.title,
        "description": spec.description,
        "surface": "cli_tool",
        "command": f"rdagent-v3-tool describe {spec.name}",
        "inputSchema": spec.request_model.model_json_schema(),
        "outputSchema": spec.response_model.model_json_schema(),
    }


def list_cli_tools() -> list[dict[str, Any]]:
    return [_catalog_entry(spec) for spec in _TOOL_SPECS]


def get_cli_tool(name: str) -> dict[str, Any]:
    spec = next((item for item in _TOOL_SPECS if item.name == name), None)
    if spec is None:
        raise KeyError(f"tool not found: {name}")
    return _catalog_entry(spec)


def call_cli_tool(name: str, arguments: dict[str, Any], **dependencies: Any) -> dict[str, Any]:
    spec = next((item for item in _TOOL_SPECS if item.name == name), None)
    if spec is None:
        raise KeyError(f"tool not found: {name}")

    request = spec.request_model.model_validate(arguments)
    handler_kwargs = {dependency: dependencies[dependency] for dependency in spec.dependency_names}
    return spec.handler(request, **handler_kwargs)


__all__ = [
    "RunStartToolResult",
    "call_cli_tool",
    "get_cli_tool",
    "list_cli_tools",
]
