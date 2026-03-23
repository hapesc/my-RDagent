"""Phase 16 selective cross-branch knowledge sharing."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from v3.algorithms.complementarity import cosine_similarity
from v3.algorithms.interaction_kernel import (
    compute_interaction_potential,
    dynamic_sample_count,
    sample_branches,
)
from v3.contracts.exploration import BranchDecisionKind, BranchDecisionSnapshot, ExplorationMode
from v3.contracts.tool_io import (
    BranchShareApplyRequest,
    BranchShareApplyResult,
    BranchShareAssessRequest,
    BranchShareAssessResult,
    MemoryListRequest,
    MemoryPromoteRequest,
)
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.dag_service import DAGService
from v3.orchestration.memory_service import MemoryService
from v3.ports.embedding_port import EmbeddingPort
from v3.ports.state_store import StateStorePort


@dataclass(frozen=True)
class InteractionKernel:
    """Compact similarity signal between two branches."""

    source_branch_id: str
    target_branch_id: str
    similarity: float


class BranchShareService:
    """Assesses and applies Phase 16 branch sharing via Phase 15 memory."""

    def __init__(
        self,
        state_store: StateStorePort,
        memory_service: MemoryService,
        board_service: BranchBoardService | None = None,
        embedding_port: EmbeddingPort | None = None,
        dag_service: DAGService | None = None,
    ) -> None:
        self._state_store = state_store
        self._memory_service = memory_service
        self._board_service = board_service or BranchBoardService(state_store)
        self._embedding_port = embedding_port
        self._dag_service = dag_service

    def assess_share(self, request: BranchShareAssessRequest) -> BranchShareAssessResult:
        source_branch = self._load_branch(request.run_id, request.source_branch_id)
        self._load_branch(request.run_id, request.target_branch_id)
        kernel = InteractionKernel(
            source_branch_id=request.source_branch_id,
            target_branch_id=request.target_branch_id,
            similarity=request.similarity,
        )
        latest_memory = self._memory_service.list_memory(
            MemoryListRequest(
                run_id=request.run_id,
                branch_id=request.source_branch_id,
                stage_key=source_branch.current_stage_key,
                task_query=source_branch.label,
                limit=1,
            )
        )
        has_record = bool(latest_memory.items)
        eligible = (
            source_branch.score.result_quality >= 0.7
            and kernel.similarity >= 0.6
            and request.judge_allows_share
            and has_record
        )
        granularity = self._granularity(source_branch.score.result_quality, kernel.similarity)
        rationale = (
            f"score={source_branch.score.result_quality:.2f}, "
            f"similarity={kernel.similarity:.2f}, "
            f"judge={'allow' if request.judge_allows_share else 'deny'}."
        )
        decision = BranchDecisionSnapshot(
            decision_id=f"decision-share-{uuid4().hex[:12]}",
            run_id=request.run_id,
            branch_id=request.target_branch_id,
            kind=BranchDecisionKind.SHARE,
            mode=ExplorationMode.EXPLORATION,
            summary=(
                f"{'Allowed' if eligible else 'Denied'} share from {request.source_branch_id} "
                f"to {request.target_branch_id} at {granularity} granularity."
            ),
            rationale=rationale,
            source_branch_id=request.source_branch_id,
            affected_branch_ids=[request.source_branch_id, request.target_branch_id],
        )
        self._state_store.write_branch_decision(decision)
        return BranchShareAssessResult(
            eligible=eligible,
            granularity=granularity,
            rationale=rationale,
            decision=decision,
        )

    def apply_share(self, request: BranchShareApplyRequest) -> BranchShareApplyResult:
        assessment = self.assess_share(
            BranchShareAssessRequest(
                run_id=request.run_id,
                source_branch_id=request.source_branch_id,
                target_branch_id=request.target_branch_id,
                similarity=request.similarity,
                judge_allows_share=request.judge_allows_share,
            )
        )
        if not assessment.eligible:
            raise ValueError("share request is not eligible")

        promoted = self._memory_service.promote_memory(
            MemoryPromoteRequest(
                memory_id=request.memory_id,
                run_id=request.run_id,
                owner_branch_id=request.source_branch_id,
                promoted_by="phase16-share",
                promotion_reason=assessment.rationale,
            )
        )
        board = self._board_service.get_board(request.run_id)
        run = self._state_store.load_run_snapshot(request.run_id)
        if run is not None:
            self._state_store.write_run_snapshot(
                run.model_copy(
                    update={
                        "exploration_mode": ExplorationMode.EXPLORATION,
                        "latest_branch_decision_id": assessment.decision.decision_id,
                        "latest_branch_board_id": board.board_id,
                    }
                )
            )
        return BranchShareApplyResult(
            memory_id=request.memory_id,
            granularity=assessment.granularity,
            decision=assessment.decision,
            board=board,
            owner_branch_id=promoted.owner_branch_id,
            shared_namespace=promoted.shared_namespace.value if promoted.shared_namespace is not None else None,
        )

    def identify_global_best(self, run_id: str) -> str | None:
        """Find the highest-scoring frontier branch from the DAG."""

        if self._dag_service is None:
            return None
        frontier_node_ids = self._dag_service.get_frontier(run_id)
        if not frontier_node_ids:
            return None

        best_score = -1.0
        best_branch_id: str | None = None
        for node_id in frontier_node_ids:
            node = self._dag_service.get_node(node_id)
            if node is not None and node.node_metrics.validation_score > best_score:
                best_score = node.node_metrics.validation_score
                best_branch_id = node.branch_id
        return best_branch_id

    def compute_sharing_candidates(
        self,
        *,
        run_id: str,
        target_branch_id: str,
        current_round: int,
        budget_ratio: float,
    ) -> list[str]:
        """Sample peer branches for sharing via the interaction kernel."""

        if current_round == 0 or self._embedding_port is None or self._dag_service is None:
            return []

        run = self._state_store.load_run_snapshot(run_id)
        target_branch = self._state_store.load_branch_snapshot(target_branch_id)
        if run is None or target_branch is None:
            return []

        peer_ids: list[str] = []
        peer_labels: list[str] = []
        peer_scores: list[float] = []
        for branch_id in run.branch_ids:
            if branch_id == target_branch_id:
                continue
            branch = self._state_store.load_branch_snapshot(branch_id)
            if branch is None:
                continue
            peer_ids.append(branch_id)
            peer_labels.append(branch.label)
            peer_scores.append(branch.score.result_quality)
        if not peer_ids:
            return []

        try:
            embeddings = self._embedding_port.embed([target_branch.label, *peer_labels])
        except Exception:
            return []

        if len(embeddings) != len(peer_ids) + 1:
            return []

        target_embedding = embeddings[0]
        peer_embeddings = embeddings[1:]
        target_nodes = [node for node in self._dag_service.list_nodes(run_id) if node.branch_id == target_branch_id]
        target_depth = max((node.depth for node in target_nodes), default=0)
        target_score = target_branch.score.result_quality

        potentials: list[float] = []
        for peer_embedding, peer_score in zip(peer_embeddings, peer_scores, strict=True):
            similarity = cosine_similarity(target_embedding, peer_embedding)
            score_delta = peer_score - target_score
            potentials.append(
                compute_interaction_potential(
                    similarity=similarity,
                    score_delta=score_delta,
                    depth=target_depth,
                )
            )

        return sample_branches(potentials, peer_ids, dynamic_sample_count(budget_ratio))

    def _load_branch(self, run_id: str, branch_id: str):
        branch = self._state_store.load_branch_snapshot(branch_id)
        if branch is None or branch.run_id != run_id:
            raise KeyError(f"branch not found: {branch_id}")
        return branch

    @staticmethod
    def _granularity(score: float, similarity: float) -> str:
        if score >= 0.85 and similarity >= 0.75:
            return "record"
        if score >= 0.75 and similarity >= 0.65:
            return "stage_summary"
        return "summary_only"


__all__ = ["BranchShareService", "InteractionKernel"]
