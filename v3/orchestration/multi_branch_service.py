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
    FinalSubmissionSnapshot,
    NodeMetrics,
)
from v3.contracts.tool_io import (
    BranchFallbackRequest,
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
from v3.orchestration.holdout_validation_service import HoldoutValidationService
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
        holdout_validation_service: HoldoutValidationService | None = None,
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
        self._holdout_validation_service = holdout_validation_service

    # ------------------------------------------------------------------
    # Exploration round (decomposed into helper methods)
    # ------------------------------------------------------------------

    def run_exploration_round(self, request: ExploreRoundRequest) -> ExploreRoundResult:
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")
        primary_branch = (
            self._state_store.load_branch_snapshot(run.primary_branch_id) if run.primary_branch_id else None
        )
        if primary_branch is None:
            raise KeyError("primary branch missing for exploration round")

        self._validate_first_layer_categories(request, run.current_round)

        dispatched_branch_ids, dispatch_targets, spec_by_label = self._prepare_branches(
            request, run, primary_branch,
        )

        sharing_candidate_ids, sharing_by_target, global_best_branch_id = self._compute_sharing(
            request.run_id,
            run,
            dispatched_branch_ids,
            agent_branch_list=request.branch_list or None,
        )

        self._dispatch_branches(
            request.run_id, dispatch_targets, sharing_by_target, global_best_branch_id,
        )

        dag_node_ids, round_diversity_score = self._build_dag_nodes(
            request, run, dispatched_branch_ids, spec_by_label, sharing_by_target, global_best_branch_id,
        )

        board, selected_branch_id, recommended_next_step, rationale = self._select_and_prune(
            request,
        )

        pruned_branch_ids: list[str] = []
        if self._prune_service is not None and request.auto_prune:
            prune_result = self._prune_service.prune(BranchPruneRequest(run_id=request.run_id))
            pruned_branch_ids = prune_result.pruned_branch_ids
            board = prune_result.board

        finalization_submission = self._try_finalize(request.run_id)

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
            finalization_submission=finalization_submission,
        )

    def _validate_first_layer_categories(
        self,
        request: ExploreRoundRequest,
        current_round: int,
    ) -> None:
        """Reject duplicate approach categories in the first exploration layer."""
        if request.hypothesis_specs is not None and current_round == 0:
            seen_categories: set[Any] = set()
            for spec in request.hypothesis_specs:
                if spec.approach_category in seen_categories:
                    raise ValueError(f"Duplicate approach_category in first layer: {spec.approach_category}")
                seen_categories.add(spec.approach_category)

    def _prepare_branches(
        self,
        request: ExploreRoundRequest,
        run: Any,
        primary_branch: Any,
    ) -> tuple[list[str], list[tuple[str, str, str]], dict[str, Any]]:
        """Fork or resolve branches for each hypothesis and allocate workspaces."""
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
            workspace_root = self._workspace_manager.workspace_root(
                run_id=request.run_id, branch_id=branch.branch_id,
            )
            if not Path(workspace_root).exists():
                workspace_root = self._workspace_manager.allocate_branch_workspace(
                    run_id=request.run_id,
                    branch_id=branch.branch_id,
                )
            dispatch_targets.append((branch.branch_id, branch.label, workspace_root))
            dispatched_branch_ids.append(branch.branch_id)

        return dispatched_branch_ids, dispatch_targets, spec_by_label

    def _compute_sharing(
        self,
        run_id: str,
        run: Any,
        dispatched_branch_ids: list[str],
        agent_branch_list: list[str] | None = None,
    ) -> tuple[list[str], dict[str, list[str]], str | None]:
        """Compute cross-branch sharing candidates from the share service."""
        sharing_candidate_ids: list[str] = []
        sharing_by_target: dict[str, list[str]] = {}
        global_best_branch_id: str | None = None

        if self._branch_share_service is not None and run.current_round > 0:
            budget_ratio = run.current_round / max(run.max_rounds, 1)
            global_best_branch_id = self._branch_share_service.identify_global_best(run_id)
            for branch_id in dispatched_branch_ids:
                candidates: list[str] = []
                if global_best_branch_id is not None and global_best_branch_id != branch_id:
                    candidates.append(global_best_branch_id)
                candidates.extend(
                    self._branch_share_service.compute_sharing_candidates(
                        run_id=run_id,
                        target_branch_id=branch_id,
                        current_round=run.current_round,
                        budget_ratio=budget_ratio,
                        agent_branch_list=agent_branch_list,
                    )
                )
                deduped = list(dict.fromkeys(candidate for candidate in candidates if candidate != branch_id))
                if deduped:
                    sharing_by_target[branch_id] = deduped
                    sharing_candidate_ids.extend(deduped)
        sharing_candidate_ids = list(dict.fromkeys(sharing_candidate_ids))

        return sharing_candidate_ids, sharing_by_target, global_best_branch_id

    def _dispatch_branches(
        self,
        run_id: str,
        dispatch_targets: list[tuple[str, str, str]],
        sharing_by_target: dict[str, list[str]],
        global_best_branch_id: str | None,
    ) -> None:
        """Send each branch to the dispatcher with sharing metadata."""
        for branch_id, label, workspace_root in dispatch_targets:
            payload: dict[str, Any] = {
                "run_id": run_id,
                "branch_id": branch_id,
                "label": label,
                "workspace_root": workspace_root,
            }
            if global_best_branch_id is not None and global_best_branch_id != branch_id:
                payload["global_best_branch_id"] = global_best_branch_id
            if branch_id in sharing_by_target:
                payload["sharing_candidate_ids"] = sharing_by_target[branch_id]
            self._dispatcher(payload)

    def _build_dag_nodes(
        self,
        request: ExploreRoundRequest,
        run: Any,
        dispatched_branch_ids: list[str],
        spec_by_label: dict[str, Any],
        sharing_by_target: dict[str, list[str]],
        global_best_branch_id: str | None,
    ) -> tuple[list[str], float | None]:
        """Create DAG nodes for dispatched branches and shared edges."""
        dag_node_ids: list[str] = []
        round_diversity_score: float | None = None

        if self._dag_service is None:
            return dag_node_ids, round_diversity_score

        category_counts: Counter[str] | None = None
        created_nodes_by_branch: dict[str, Any] = {}
        if request.hypothesis_specs is not None:
            category_counts = Counter(spec.approach_category.value for spec in request.hypothesis_specs)
            round_diversity_score = category_entropy(dict(category_counts))

        for branch_id in dispatched_branch_ids:
            parent_node_ids = self._resolve_parent_nodes(request, run, branch_id)
            node_diversity_score = self._compute_node_diversity(
                branch_id, category_counts, spec_by_label, request,
            )
            node = self._dag_service.create_node(
                run_id=request.run_id,
                branch_id=branch_id,
                parent_node_ids=parent_node_ids,
                node_metrics=NodeMetrics(diversity_score=node_diversity_score),
            )
            dag_node_ids.append(node.node_id)
            created_nodes_by_branch[branch_id] = node

        self._create_sharing_edges(
            request.run_id, sharing_by_target, created_nodes_by_branch, global_best_branch_id,
        )

        return dag_node_ids, round_diversity_score

    def _resolve_parent_nodes(
        self,
        request: ExploreRoundRequest,
        run: Any,
        branch_id: str,
    ) -> list[str]:
        """Select parent DAG nodes for a branch in later rounds."""
        if (
            run.current_round > 0
            and request.hypothesis_specs is not None
            and self._select_parents_service is not None
        ):
            try:
                return self._select_parents_service.select_parents(
                    run_id=request.run_id,
                    branch_id=branch_id,
                ).parent_node_ids
            except KeyError:
                return []
        return []

    def _compute_node_diversity(
        self,
        branch_id: str,
        category_counts: Counter[str] | None,
        spec_by_label: dict[str, Any],
        request: ExploreRoundRequest,
    ) -> float:
        """Compute the information-theoretic diversity score for a DAG node."""
        branch = self._state_store.load_branch_snapshot(branch_id)
        if branch is not None and category_counts is not None:
            spec = spec_by_label.get(branch.label)
            if spec is not None:
                category_count = category_counts[spec.approach_category.value]
                total_specs = len(request.hypothesis_specs or [])
                if category_count > 0 and total_specs > 0:
                    return -math.log2(category_count / total_specs)
        return 0.0

    def _create_sharing_edges(
        self,
        run_id: str,
        sharing_by_target: dict[str, list[str]],
        created_nodes_by_branch: dict[str, Any],
        global_best_branch_id: str | None,
    ) -> None:
        """Record DAG edges and branch decisions for cross-branch sharing."""
        if not sharing_by_target or self._dag_service is None:
            return

        all_nodes = self._dag_service.list_nodes(run_id)
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
                        run_id=run_id,
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

    def _select_and_prune(
        self,
        request: ExploreRoundRequest,
    ) -> tuple[Any, str, str, str]:
        """Select the next branch and return the board state."""
        board = self._branch_board_service.get_board(request.run_id)
        try:
            recommendation = self._selection_service.select_next_branch(
                run_id=request.run_id, include_completed=True,
            )
            selected_branch_id = recommendation.branch_id
            recommended_next_step = recommendation.recommended_next_step
            rationale = recommendation.rationale
        except (KeyError, ValueError):
            selected_branch_id = board.active_cards[0].branch_id
            recommended_next_step = "continue explore round"
            rationale = "No recovery-backed recommendation yet; continue exploring active branches."
        return board, selected_branch_id, recommended_next_step, rationale

    def _try_finalize(self, run_id: str) -> FinalSubmissionSnapshot | None:
        """Attempt holdout finalization if the budget is exhausted."""
        run = self._state_store.load_run_snapshot(run_id)
        if run is not None:
            new_round = run.current_round + 1
            self._state_store.write_run_snapshot(run.model_copy(update={"current_round": new_round}))
            if new_round >= run.max_rounds and self._holdout_validation_service is not None:
                try:
                    submission = self._holdout_validation_service.finalize(run_id=run_id)
                    updated_run = self._state_store.load_run_snapshot(run_id)
                    if updated_run is not None:
                        self._state_store.write_run_snapshot(
                            updated_run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})
                        )
                    return submission
                except (ValueError, KeyError):
                    return None
        return None

    def should_finalize(self, run_id: str) -> bool:
        """Query whether the run is ready for finalization."""
        run = self._state_store.load_run_snapshot(run_id)
        if run is None:
            return False
        return run.current_round >= run.max_rounds and self._holdout_validation_service is not None

    # ------------------------------------------------------------------
    # Early finalization
    # ------------------------------------------------------------------

    def finalize_early(self, *, run_id: str) -> FinalSubmissionSnapshot:
        """Operator-triggered early finalization before budget exhaustion."""

        if self._holdout_validation_service is None:
            raise ValueError("Cannot finalize: no HoldoutValidationService configured")
        submission = self._holdout_validation_service.finalize(run_id=run_id)
        run = self._state_store.load_run_snapshot(run_id)
        if run is not None:
            self._state_store.write_run_snapshot(
                run.model_copy(update={"exploration_mode": ExplorationMode.FINALIZED})
            )
        return submission

    # ------------------------------------------------------------------
    # Convergence round
    # ------------------------------------------------------------------

    def run_convergence_round(self, request: ConvergeRoundRequest) -> ConvergeRoundResult:
        merge_request = BranchMergeRequest(
            run_id=request.run_id,
            minimum_quality=request.minimum_quality,
        )
        if self._branch_share_service is not None and self._dag_service is not None:
            branch_component_scores, _component_classes = self._dag_service.collect_branch_component_scores(
                request.run_id,
                self._state_store,
            )
            has_complementarity = hasattr(self._branch_merge_service, "merge_with_complementarity")
            if branch_component_scores and has_complementarity:
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
                BranchFallbackRequest(
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
