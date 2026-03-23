"""High-level Phase 16 coordinator above the single-branch skill loop."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from v3.algorithms.decay import category_entropy
from v3.contracts.exploration import (
    BranchDecisionKind,
    BranchDecisionSnapshot,
    EdgeType,
    ExplorationMode,
    NodeMetrics,
)
from v3.contracts.tool_io import (
    BranchMergeRequest,
    BranchForkRequest,
    BranchPruneRequest,
    ConvergeRoundRequest,
    ConvergeRoundResult,
    ExploreRoundRequest,
    ExploreRoundResult,
)
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_lifecycle_service import BranchLifecycleService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.branch_prune_service import BranchPruneService
from v3.orchestration.branch_share_service import BranchShareService
from v3.orchestration.branch_workspace_manager import BranchWorkspaceManager
from v3.orchestration.dag_service import DAGService
from v3.orchestration.select_parents_service import SelectParentsService
from v3.orchestration.selection_service import SelectionService
from v3.ports.state_store import StateStorePort

DispatchFn = Callable[[dict[str, Any]], dict[str, Any]]


class MultiBranchService:
    """Coordinates multi-branch exploration rounds without teaching SkillLoopService frontier state."""

    def __init__(
        self,
        *,
        state_store: StateStorePort,
        workspace_manager: BranchWorkspaceManager,
        branch_lifecycle_service: BranchLifecycleService,
        branch_board_service: BranchBoardService,
        selection_service: SelectionService,
        branch_merge_service: BranchMergeService,
        dispatcher: DispatchFn | None = None,
        dag_service: DAGService | None = None,
        prune_service: BranchPruneService | None = None,
        select_parents_service: SelectParentsService | None = None,
        branch_share_service: BranchShareService | None = None,
    ) -> None:
        self._state_store = state_store
        self._workspace_manager = workspace_manager
        self._branch_lifecycle_service = branch_lifecycle_service
        self._branch_board_service = branch_board_service
        self._selection_service = selection_service
        self._branch_merge_service = branch_merge_service
        self._dispatcher = dispatcher or (lambda payload: {"status": "queued", **payload})
        self._dag_service = dag_service
        self._prune_service = prune_service
        self._select_parents_service = select_parents_service
        self._branch_share_service = branch_share_service

    def run_exploration_round(self, request: ExploreRoundRequest) -> ExploreRoundResult:
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")
        primary_branch = (
            self._state_store.load_branch_snapshot(run.primary_branch_id) if run.primary_branch_id else None
        )
        if primary_branch is None:
            raise KeyError("primary branch missing for exploration round")

        if request.hypothesis_specs is not None and run.current_round == 0:
            seen_categories = set()
            for spec in request.hypothesis_specs:
                if spec.approach_category in seen_categories:
                    raise ValueError(f"Duplicate approach_category in first layer: {spec.approach_category}")
                seen_categories.add(spec.approach_category)

        hypothesis_labels = (
            [spec.label for spec in request.hypothesis_specs]
            if request.hypothesis_specs is not None
            else request.hypotheses
        )
        if not hypothesis_labels:
            raise ValueError("exploration round requires at least one hypothesis")
        by_label = {
            branch.label: branch
            for branch_id in run.branch_ids
            if (branch := self._state_store.load_branch_snapshot(branch_id)) is not None
        }
        by_label.setdefault(primary_branch.label, primary_branch)
        spec_by_label = {spec.label: spec for spec in (request.hypothesis_specs or [])}
        dispatched_branch_ids: list[str] = []
        dispatch_targets: list[tuple[str, str, str]] = []
        for hypothesis in hypothesis_labels:
            branch = by_label.get(hypothesis)
            if branch is None:
                publication = self._branch_lifecycle_service.fork_branch(
                    BranchForkRequest(
                        run_id=request.run_id,
                        source_branch_id=primary_branch.branch_id,
                        label=hypothesis,
                        rationale=f"Fork branch for hypothesis {hypothesis}.",
                    )
                )
                branch = publication.branch
                by_label[hypothesis] = branch
            if request.hypothesis_specs is not None:
                spec = spec_by_label.get(branch.label)
                if spec is not None:
                    self._state_store.write_hypothesis_spec(branch.branch_id, spec)
            workspace_root = self._workspace_manager.workspace_root(run_id=request.run_id, branch_id=branch.branch_id)
            if not Path(workspace_root).exists():
                workspace_root = self._workspace_manager.allocate_branch_workspace(
                    run_id=request.run_id,
                    branch_id=branch.branch_id,
                )
            dispatch_targets.append((branch.branch_id, branch.label, workspace_root))
            dispatched_branch_ids.append(branch.branch_id)

        sharing_candidate_ids: list[str] = []
        sharing_by_target: dict[str, list[str]] = {}
        global_best_branch_id: str | None = None
        if self._branch_share_service is not None and run.current_round > 0:
            budget_ratio = run.current_round / max(run.max_rounds, 1)
            global_best_branch_id = self._branch_share_service.identify_global_best(request.run_id)
            for branch_id in dispatched_branch_ids:
                candidates: list[str] = []
                if global_best_branch_id is not None and global_best_branch_id != branch_id:
                    candidates.append(global_best_branch_id)
                candidates.extend(
                    self._branch_share_service.compute_sharing_candidates(
                        run_id=request.run_id,
                        target_branch_id=branch_id,
                        current_round=run.current_round,
                        budget_ratio=budget_ratio,
                    )
                )
                deduped = list(dict.fromkeys(candidate for candidate in candidates if candidate != branch_id))
                if deduped:
                    sharing_by_target[branch_id] = deduped
                    sharing_candidate_ids.extend(deduped)
        sharing_candidate_ids = list(dict.fromkeys(sharing_candidate_ids))

        for branch_id, label, workspace_root in dispatch_targets:
            payload: dict[str, Any] = {
                "run_id": request.run_id,
                "branch_id": branch_id,
                "label": label,
                "workspace_root": workspace_root,
            }
            if global_best_branch_id is not None and global_best_branch_id != branch_id:
                payload["global_best_branch_id"] = global_best_branch_id
            if branch_id in sharing_by_target:
                payload["sharing_candidate_ids"] = sharing_by_target[branch_id]
            self._dispatcher(payload)

        dag_node_ids: list[str] = []
        round_diversity_score: float | None = None
        if self._dag_service is not None:
            category_counts: Counter[str] | None = None
            created_nodes_by_branch: dict[str, Any] = {}
            if request.hypothesis_specs is not None:
                category_counts = Counter(spec.approach_category.value for spec in request.hypothesis_specs)
                round_diversity_score = category_entropy(dict(category_counts))
            for branch_id in dispatched_branch_ids:
                parent_node_ids: list[str] = []
                if (
                    run.current_round > 0
                    and request.hypothesis_specs is not None
                    and self._select_parents_service is not None
                ):
                    try:
                        parent_node_ids = self._select_parents_service.select_parents(
                            run_id=request.run_id,
                            branch_id=branch_id,
                        ).parent_node_ids
                    except KeyError:
                        parent_node_ids = []
                node_diversity_score = 0.0
                branch = self._state_store.load_branch_snapshot(branch_id)
                if branch is not None and category_counts is not None:
                    spec = spec_by_label.get(branch.label)
                    if spec is not None:
                        category_count = category_counts[spec.approach_category.value]
                        total_specs = len(request.hypothesis_specs or [])
                        if category_count > 0 and total_specs > 0:
                            node_diversity_score = -math.log2(category_count / total_specs)
                node = self._dag_service.create_node(
                    run_id=request.run_id,
                    branch_id=branch_id,
                    parent_node_ids=parent_node_ids,
                    node_metrics=NodeMetrics(diversity_score=node_diversity_score),
                )
                dag_node_ids.append(node.node_id)
                created_nodes_by_branch[branch_id] = node

            if sharing_by_target:
                all_nodes = self._dag_service.list_nodes(request.run_id)
                for target_branch_id, candidate_ids in sharing_by_target.items():
                    target_node = created_nodes_by_branch.get(target_branch_id)
                    if target_node is None:
                        target_candidates = [node for node in all_nodes if node.branch_id == target_branch_id]
                        if not target_candidates:
                            continue
                        target_node = max(target_candidates, key=lambda node: node.depth)
                    for source_branch_id in candidate_ids:
                        source_candidates = [node for node in all_nodes if node.branch_id == source_branch_id]
                        if not source_candidates:
                            continue
                        source_node = max(source_candidates, key=lambda node: node.depth)
                        self._dag_service.create_typed_edge(
                            source_node_id=source_node.node_id,
                            target_node_id=target_node.node_id,
                            edge_type=EdgeType.SHARED,
                        )
                        self._state_store.write_branch_decision(
                            BranchDecisionSnapshot(
                                decision_id=f"decision-share-{uuid4().hex[:12]}",
                                run_id=request.run_id,
                                branch_id=target_branch_id,
                                kind=BranchDecisionKind.SHARE,
                                mode=ExplorationMode.EXPLORATION,
                                summary=f"Injected {source_branch_id} into {target_branch_id} for cross-branch sharing.",
                                rationale=(
                                    "Injected the global-best branch into the target candidate pool."
                                    if source_branch_id == global_best_branch_id
                                    else "Injected an interaction-kernel peer into the target candidate pool."
                                ),
                                source_branch_id=source_branch_id,
                                affected_branch_ids=[source_branch_id, target_branch_id],
                            )
                        )

        board = self._branch_board_service.get_board(request.run_id)
        try:
            recommendation = self._selection_service.select_next_branch(run_id=request.run_id, include_completed=True)
            selected_branch_id = recommendation.branch_id
            recommended_next_step = recommendation.recommended_next_step
            rationale = recommendation.rationale
        except Exception:
            selected_branch_id = board.active_cards[0].branch_id
            recommended_next_step = "continue explore round"
            rationale = "No recovery-backed recommendation yet; continue exploring active branches."

        pruned_branch_ids: list[str] = []
        if self._prune_service is not None and request.auto_prune:
            prune_result = self._prune_service.prune(BranchPruneRequest(run_id=request.run_id))
            pruned_branch_ids = prune_result.pruned_branch_ids
            board = prune_result.board

        run = self._state_store.load_run_snapshot(request.run_id)
        if run is not None:
            self._state_store.write_run_snapshot(run.model_copy(update={"current_round": run.current_round + 1}))
        return ExploreRoundResult(
            selected_branch_id=selected_branch_id,
            recommended_next_step=recommended_next_step,
            rationale=rationale,
            board=board,
            dispatched_branch_ids=dispatched_branch_ids,
            sharing_candidate_ids=sharing_candidate_ids,
            pruned_branch_ids=pruned_branch_ids,
            dag_node_ids=dag_node_ids,
            round_diversity_score=round_diversity_score,
        )

    def run_convergence_round(self, request: ConvergeRoundRequest) -> ConvergeRoundResult:
        merge_request = BranchMergeRequest(
            run_id=request.run_id,
            minimum_quality=request.minimum_quality,
        )
        if (
            self._branch_share_service is not None
            and self._dag_service is not None
            and hasattr(self._branch_merge_service, "merge_with_complementarity")
        ):
            branch_component_scores, _component_classes = self._dag_service.collect_branch_component_scores(
                request.run_id,
                self._state_store,
            )
            if branch_component_scores:
                merge_result = self._branch_merge_service.merge_with_complementarity(
                    merge_request,
                    branch_component_scores,
                )
            else:
                merge_result = self._branch_merge_service.merge(merge_request)
        else:
            merge_result = self._branch_merge_service.merge(merge_request)
        if merge_result.outcome.failure_reason is None and merge_result.outcome.merged_branch_id is not None:
            return ConvergeRoundResult(
                selected_branch_id=merge_result.outcome.merged_branch_id,
                recommended_next_step="review merged synthesis",
                rationale="Convergence merged the leading shortlist entries.",
                board=merge_result.board,
                merge_summary=merge_result.outcome.summary,
            )
        try:
            fallback = self._branch_merge_service.fallback(
                __import__("v3.contracts.tool_io", fromlist=["BranchFallbackRequest"]).BranchFallbackRequest(
                    run_id=request.run_id,
                    minimum_quality=request.minimum_quality,
                )
            )
            selected_branch_id = fallback.selected_branch_id
            rationale = fallback.rationale
        except ValueError:
            board = self._branch_board_service.get_board(request.run_id)
            if not board.active_cards:
                raise
            selected_branch_id = board.active_cards[0].branch_id
            rationale = "No shortlist met the convergence threshold; continue with the top active branch."
        return ConvergeRoundResult(
            selected_branch_id=selected_branch_id,
            recommended_next_step="continue with top-ranked branch",
            rationale=rationale,
            board=merge_result.board,
            merge_summary=merge_result.outcome.summary,
        )


__all__ = ["MultiBranchService"]
