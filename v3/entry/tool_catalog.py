"""CLI-oriented V3 tool catalog.

This module owns the schema-described V3 tool surface used by skill entrypoints
and CLI-facing tooling. It intentionally avoids any MCP transport/server
semantics; the catalog is an in-process dispatch layer over V3-owned handlers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

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


ToolCategory = Literal["orchestration", "inspection", "primitives"]
ToolSubcategory = Literal["branch_lifecycle", "branch_knowledge", "branch_selection", "memory"] | None
RecommendedEntrypoint = Literal["rd-agent", "rd-tool-catalog"]


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
    category: ToolCategory
    subcategory: ToolSubcategory
    recommended_entrypoint: RecommendedEntrypoint
    examples: tuple[dict[str, Any], ...]
    when_to_use: str
    when_not_to_use: str
    follow_up: dict[str, str]
    handler: Callable[..., dict[str, Any]]
    request_model: type[BaseModel]
    response_model: type[BaseModel]
    dependency_names: tuple[str, ...]


_ORCHESTRATION_WHEN_TO_USE = (
    "Use this direct tool only when you intentionally need to issue a bounded orchestration call "
    "with an explicit V3 payload."
)
_ORCHESTRATION_WHEN_NOT_TO_USE = (
    "Do not use this as the default path for starting or continuing work; stay in rd-agent unless "
    "you deliberately need a direct orchestration primitive."
)
_INSPECTION_WHEN_TO_USE = (
    "Use this direct tool after a run, branch, stage, artifact, recovery, memory, or path identifier "
    "is already known and you need a precise read-only lookup."
)
_INSPECTION_WHEN_NOT_TO_USE = (
    "Do not use this to advance the workflow or to discover the next high-level skill; use rd-agent "
    "for default orchestration and rd-tool-catalog only after narrowing to a concrete inspection need."
)
_PRIMITIVE_WHEN_TO_USE = (
    "Use this direct tool after you have already decided the high-level skill boundary is insufficient "
    "and you need a targeted state mutation or branch-selection action."
)
_PRIMITIVE_WHEN_NOT_TO_USE = (
    "Do not use this when rd-agent can still own the end-to-end flow or when the request has not yet "
    "been narrowed to a concrete primitive action."
)
_CATEGORY_NOTES = {
    "orchestration": "Run one bounded orchestration step with an explicit public payload.",
    "inspection": "Inspect the current V3 state after a prior skill or primitive call returned identifiers.",
    "primitives": "Apply one targeted direct-tool action after narrowing through rd-tool-catalog.",
}


def _example(arguments: dict[str, Any], *, category: ToolCategory) -> dict[str, Any]:
    return {
        "label": "common_path",
        "arguments": arguments,
        "note": _CATEGORY_NOTES[category],
    }


def _when_to_use(category: ToolCategory) -> str:
    return {
        "orchestration": _ORCHESTRATION_WHEN_TO_USE,
        "inspection": _INSPECTION_WHEN_TO_USE,
        "primitives": _PRIMITIVE_WHEN_TO_USE,
    }[category]


def _when_not_to_use(category: ToolCategory) -> str:
    return {
        "orchestration": _ORCHESTRATION_WHEN_NOT_TO_USE,
        "inspection": _INSPECTION_WHEN_NOT_TO_USE,
        "primitives": _PRIMITIVE_WHEN_NOT_TO_USE,
    }[category]


def _follow_up(when_successful: str, next_entrypoint: RecommendedEntrypoint, next_action: str) -> dict[str, str]:
    return {
        "when_successful": when_successful,
        "next_entrypoint": next_entrypoint,
        "next_action": next_action,
    }


_TOOL_SPECS: tuple[_ToolSpec, ...] = (
    _ToolSpec(
        name="rd_run_start",
        title="Start V3 Run",
        description="Start a V3 run and publish the initial run, branch, stage, and artifact truth.",
        category="orchestration",
        subcategory=None,
        recommended_entrypoint="rd-agent",
        examples=(
            _example(
                {
                    "title": "Phase 19 tool guidance hardening",
                    "task_summary": "Add tool-catalog examples, routing guidance, and follow-up semantics to the direct V3 CLI surface.",
                    "scenario_label": "data_science",
                    "initial_branch_label": "primary",
                    "execution_mode": "gated",
                    "max_stage_iterations": 1,
                },
                category="orchestration",
            ),
        ),
        when_to_use=_when_to_use("orchestration"),
        when_not_to_use=_when_not_to_use("orchestration"),
        follow_up=_follow_up(
            "A new run, primary branch, and initial stage have been published.",
            "rd-agent",
            "Continue the run with rd-agent using the returned run_id, or inspect the returned branch_id and stage_key before handing off to a stage skill.",
        ),
        handler=rd_run_start,
        request_model=RunStartRequest,
        response_model=RunStartToolResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_run_get",
        title="Get V3 Run",
        description="Load the canonical V3 run-board snapshot.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(_example({"run_id": "run-001"}, category="inspection"),),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The canonical run-board snapshot has been loaded.",
            "rd-agent",
            "Inspect the returned status, primary_branch_id, and stop_reason, then continue with rd-agent or inspect a specific branch if you need a narrower direct-tool read.",
        ),
        handler=rd_run_get,
        request_model=RunGetRequest,
        response_model=RunGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_fork",
        title="Fork V3 Branch",
        description="Create a labeled Phase 16 branch fork with isolated workspace allocation.",
        category="primitives",
        subcategory="branch_lifecycle",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "label": "branch-002",
                    "source_branch_id": "branch-001",
                    "rationale": "Investigate a competing implementation path",
                },
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "A new branch and fork decision have been published.",
            "rd-tool-catalog",
            "Inspect the new branch with rd_branch_get or rd_stage_get, then continue work on that branch through the next valid skill or primitive.",
        ),
        handler=rd_branch_fork,
        request_model=BranchForkRequest,
        response_model=BranchForkResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_board_get",
        title="Get V3 Branch Board",
        description="Load the Phase 16 active/history branch board read model.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(_example({"run_id": "run-001"}, category="inspection"),),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The active and historical branch board has been loaded.",
            "rd-tool-catalog",
            "Use the returned board to decide whether to shortlist, prune, merge, fallback, or select the next branch.",
        ),
        handler=rd_branch_board_get,
        request_model=BranchBoardGetRequest,
        response_model=BranchBoardGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_prune",
        title="Prune V3 Branches",
        description="Prune low-quality Phase 16 branches while preserving at least one active branch.",
        category="primitives",
        subcategory="branch_lifecycle",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "relative_threshold": 0.15},
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "Low-quality branches have been pruned and the board state has advanced.",
            "rd-tool-catalog",
            "Inspect the updated board with rd_branch_board_get before the next shortlist or convergence action.",
        ),
        handler=rd_branch_prune,
        request_model=BranchPruneRequest,
        response_model=BranchPruneResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_share_assess",
        title="Assess V3 Branch Share",
        description="Assess whether one Phase 16 branch should share knowledge with another.",
        category="primitives",
        subcategory="branch_knowledge",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "source_branch_id": "branch-002",
                    "target_branch_id": "branch-001",
                    "similarity": 0.82,
                    "judge_allows_share": True,
                },
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "The share decision for the source and target branches has been evaluated.",
            "rd-tool-catalog",
            "If the returned decision allows sharing, apply it with rd_branch_share_apply; otherwise continue without promoting that memory.",
        ),
        handler=rd_branch_share_assess,
        request_model=BranchShareAssessRequest,
        response_model=BranchShareAssessResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_share_apply",
        title="Apply V3 Branch Share",
        description="Promote eligible branch knowledge through the Phase 15 memory contract.",
        category="primitives",
        subcategory="branch_knowledge",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "source_branch_id": "branch-002",
                    "target_branch_id": "branch-001",
                    "memory_id": "memory-001",
                    "similarity": 0.82,
                    "judge_allows_share": True,
                },
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "Eligible branch knowledge has been applied and the board context has been refreshed.",
            "rd-tool-catalog",
            "Inspect the resulting memory or branch board, then continue the affected branch with the next valid stage action.",
        ),
        handler=rd_branch_share_apply,
        request_model=BranchShareApplyRequest,
        response_model=BranchShareApplyResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_shortlist",
        title="Build V3 Branch Shortlist",
        description="Build the candidate summary and quality-ordered shortlist for convergence.",
        category="primitives",
        subcategory="branch_selection",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "minimum_quality": 0.7},
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "A quality-ordered shortlist has been built for convergence.",
            "rd-agent",
            "Return to rd-agent as the default continuation path, or explicitly downshift to rd_converge_round if you intentionally need a direct convergence call after inspecting the shortlist.",
        ),
        handler=rd_branch_shortlist,
        request_model=BranchShortlistRequest,
        response_model=BranchShortlistResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_merge",
        title="Merge V3 Branches",
        description="Attempt a convergence merge over the Phase 16 shortlist.",
        category="primitives",
        subcategory="branch_lifecycle",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "minimum_quality": 0.75},
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "A convergence merge attempt has completed.",
            "rd-agent",
            "Inspect the merge outcome and shortlist; if the merge did not hold, use rd_branch_fallback or rd_branch_select_next before continuing.",
        ),
        handler=rd_branch_merge,
        request_model=BranchMergeRequest,
        response_model=BranchMergeResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_fallback",
        title="Fallback to Top V3 Branch",
        description="Choose the top-ranked branch when merge quality degrades.",
        category="primitives",
        subcategory="branch_lifecycle",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "minimum_quality": 0.75},
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "The top-ranked fallback branch has been selected.",
            "rd-tool-catalog",
            "Inspect the selected branch with rd_branch_get or rd_stage_get, then continue work on that branch.",
        ),
        handler=rd_branch_fallback,
        request_model=BranchFallbackRequest,
        response_model=BranchFallbackResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_get",
        title="Get V3 Branch",
        description="Load a canonical V3 branch snapshot.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(_example({"branch_id": "branch-001"}, category="inspection"),),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The canonical branch snapshot has been loaded.",
            "rd-tool-catalog",
            "Inspect the branch's current stage or artifacts to decide the next direct-tool read or the next high-level skill handoff.",
        ),
        handler=rd_branch_get,
        request_model=BranchGetRequest,
        response_model=BranchGetResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_branch_list",
        title="List V3 Branches",
        description="List canonical V3 branches for a run.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "include_completed": True},
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The run's branch list has been loaded.",
            "rd-tool-catalog",
            "Choose a branch to inspect with rd_branch_get or let rd_branch_select_next recommend the next branch to advance.",
        ),
        handler=rd_branch_list,
        request_model=BranchListRequest,
        response_model=BranchListResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_stage_get",
        title="Get V3 Stage",
        description="Load branch-stage state and published artifacts in V3 terms.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"branch_id": "branch-001", "stage_key": "build"},
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The branch-stage snapshot and its published artifacts have been loaded.",
            "rd-tool-catalog",
            "Inspect artifacts with rd_artifact_list or hand the branch back to the next valid stage skill for continued work.",
        ),
        handler=rd_stage_get,
        request_model=StageGetRequest,
        response_model=StageGetResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_artifact_list",
        title="List V3 Artifacts",
        description="List canonical V3 artifacts for a run, branch, or stage.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "branch_id": "branch-001",
                    "stage_key": "build",
                    "kind": "code",
                },
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The requested artifact list has been loaded.",
            "rd-tool-catalog",
            "Use the returned artifact ids and branch/stage context to inspect the underlying evidence or continue the branch from that stage.",
        ),
        handler=rd_artifact_list,
        request_model=ArtifactListRequest,
        response_model=ArtifactListResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_recovery_assess",
        title="Assess V3 Recovery",
        description="Assess V3 branch-stage recovery readiness without legacy checkpoint leakage.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "branch_id": "branch-001", "stage_key": "verify"},
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "Recovery readiness for the requested branch stage has been evaluated.",
            "rd-tool-catalog",
            "If recovery is ready, inspect the relevant artifacts or continue the branch's next valid stage; if it is blocked, fix the missing evidence before retrying.",
        ),
        handler=rd_recovery_assess,
        request_model=RecoveryAssessRequest,
        response_model=RecoveryAssessResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_select_next",
        title="Select Next V3 Branch",
        description="Recommend the next V3 branch to advance from public branch and recovery state.",
        category="primitives",
        subcategory="branch_selection",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "include_completed": False},
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "A recommendation for the next branch to advance has been produced.",
            "rd-tool-catalog",
            "Inspect the recommended branch with rd_branch_get or rd_stage_get, then continue work on that branch.",
        ),
        handler=rd_branch_select_next,
        request_model=BranchSelectNextRequest,
        response_model=BranchSelectNextResult,
        dependency_names=("state_store",),
    ),
    _ToolSpec(
        name="rd_memory_create",
        title="Create V3 Memory",
        description="Create a branch-owned V3 memory record for the current run and stage.",
        category="primitives",
        subcategory="memory",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "branch_id": "branch-001",
                    "stage_key": "build",
                    "hypothesis": "The simplified retry policy will stabilize the verification loop.",
                    "score": 0.78,
                    "reason": "Build-stage evidence suggests the current branch is converging on a reusable fix.",
                    "kind": "atomic",
                    "memory_id": "memory-001",
                    "evidence": ["artifact-build-001"],
                    "outcome": "Carry the retry-policy insight into later branches.",
                    "tags": ["build", "retry-policy"],
                },
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "A branch-owned memory record has been created.",
            "rd-tool-catalog",
            "Inspect the new memory with rd_memory_get or promote it with rd_memory_promote if it should become shared.",
        ),
        handler=rd_memory_create,
        request_model=MemoryCreateRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_get",
        title="Get V3 Memory",
        description="Load a V3 memory record with branch-local and shared promotion context.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"memory_id": "memory-001", "run_id": "run-001", "owner_branch_id": "branch-001"},
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The requested memory record has been loaded.",
            "rd-tool-catalog",
            "Use the memory in branch work, or promote it with rd_memory_promote if it is ready for the shared namespace.",
        ),
        handler=rd_memory_get,
        request_model=MemoryGetRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_list",
        title="List V3 Memory",
        description="List branch-local and shared V3 memory matches for a branch-stage query.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "branch_id": "branch-001",
                    "stage_key": "build",
                    "task_query": "retry policy stabilization",
                    "limit": 5,
                },
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "Matching memory records have been listed.",
            "rd-tool-catalog",
            "Inspect a specific memory with rd_memory_get or promote a reusable one with rd_memory_promote.",
        ),
        handler=rd_memory_list,
        request_model=MemoryListRequest,
        response_model=MemoryListResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_memory_promote",
        title="Promote V3 Memory",
        description="Promote eligible V3 memory into the shared namespace without leaking legacy checkpoints.",
        category="primitives",
        subcategory="memory",
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {
                    "memory_id": "memory-001",
                    "run_id": "run-001",
                    "owner_branch_id": "branch-001",
                    "promoted_by": "branch-001",
                    "promotion_reason": "Promote reusable build insight for later branches",
                },
                category="primitives",
            ),
        ),
        when_to_use=_when_to_use("primitives"),
        when_not_to_use=_when_not_to_use("primitives"),
        follow_up=_follow_up(
            "The selected memory has been promoted into the shared namespace.",
            "rd-tool-catalog",
            "Inspect the promoted memory to confirm the shared overlay, then use it from later branches as needed.",
        ),
        handler=rd_memory_promote,
        request_model=MemoryPromoteRequest,
        response_model=MemoryGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_branch_paths_get",
        title="Get V3 Branch Paths",
        description="Expose canonical branch-local and shared Phase 15 storage roots for a run branch.",
        category="inspection",
        subcategory=None,
        recommended_entrypoint="rd-tool-catalog",
        examples=(
            _example(
                {"run_id": "run-001", "branch_id": "branch-001"},
                category="inspection",
            ),
        ),
        when_to_use=_when_to_use("inspection"),
        when_not_to_use=_when_not_to_use("inspection"),
        follow_up=_follow_up(
            "The canonical branch-local and shared storage roots have been loaded.",
            "rd-tool-catalog",
            "Open the returned paths or continue branch work using the branch_id that those paths belong to.",
        ),
        handler=rd_branch_paths_get,
        request_model=BranchPathsGetRequest,
        response_model=BranchPathsGetResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_explore_round",
        title="Run V3 Explore Round",
        description="Run a high-level Phase 16 exploration round over the active branch frontier.",
        category="orchestration",
        subcategory=None,
        recommended_entrypoint="rd-agent",
        examples=(
            _example(
                {
                    "run_id": "run-001",
                    "hypotheses": [
                        "Tighten tool metadata around examples and routing semantics",
                        "Add follow-up guidance for gated and selection-sensitive tools",
                    ],
                },
                category="orchestration",
            ),
        ),
        when_to_use=_when_to_use("orchestration"),
        when_not_to_use=_when_not_to_use("orchestration"),
        follow_up=_follow_up(
            "The exploration frontier has advanced and the branch board has been updated.",
            "rd-agent",
            "Inspect the updated board with rd_branch_board_get if you need to see the frontier, or continue orchestration with rd-agent.",
        ),
        handler=rd_explore_round,
        request_model=ExploreRoundRequest,
        response_model=ExploreRoundResult,
        dependency_names=("service",),
    ),
    _ToolSpec(
        name="rd_converge_round",
        title="Run V3 Converge Round",
        description="Run a high-level Phase 16 convergence round over the current shortlist.",
        category="orchestration",
        subcategory=None,
        recommended_entrypoint="rd-agent",
        examples=(
            _example(
                {"run_id": "run-001", "minimum_quality": 0.75},
                category="orchestration",
            ),
        ),
        when_to_use=_when_to_use("orchestration"),
        when_not_to_use=_when_not_to_use("orchestration"),
        follow_up=_follow_up(
            "The current shortlist has been evaluated for convergence.",
            "rd-agent",
            "Inspect the returned merge and shortlist state, then continue with rd-agent or use fallback/selection tools if convergence did not finish the run.",
        ),
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
        "category": spec.category,
        "subcategory": spec.subcategory,
        "recommended_entrypoint": spec.recommended_entrypoint,
        "examples": list(spec.examples),
        "when_to_use": spec.when_to_use,
        "when_not_to_use": spec.when_not_to_use,
        "follow_up": spec.follow_up,
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
