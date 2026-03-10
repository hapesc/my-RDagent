"""Service scaffold for the Exploration Manager module."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from data_models import BranchState, ExplorationGraph, GraphEdge, NodeRecord, Plan
from exploration_manager.merging import TraceMerger
from exploration_manager.pruning import BranchPruner
from exploration_manager.scheduler import MCTSScheduler
from llm.adapter import LLMAdapter


@dataclass
class ExplorationManagerConfig:
    """Configuration for exploration scheduling and selection."""

    max_branches: int = 4
    selection_policy: str = "placeholder-policy"
    mcts_exploration_weight: float = 1.41
    prune_relative_threshold: float = 0.5
    merge_enabled: bool = True


@runtime_checkable
class SupportsDiverseRoots(Protocol):
    def generate_diverse_roots(
        self,
        graph: ExplorationGraph,
        task_summary: str,
        scenario_name: str,
        n_candidates: int = 5,
        k_forward: int = 2,
    ) -> ExplorationGraph: ...


@runtime_checkable
class SupportsTraceMerge(Protocol):
    def merge_traces(self, graph: ExplorationGraph, task_summary: str, scenario_name: str) -> Any: ...


@runtime_checkable
class VirtualEvaluatorLike(Protocol):
    def evaluate(
        self,
        task_summary: str,
        scenario_name: str,
        iteration: int,
        previous_results: list[str],
        current_scores: list[float],
        evaluation_criteria: str = "feasibility, novelty, expected performance gain",
        model_config: Any | None = None,
        n_candidates: int | None = None,
        k_forward: int | None = None,
    ) -> list[Any]: ...


def supports_diverse_roots(manager: object) -> bool:

    return callable(getattr(type(manager), "generate_diverse_roots", None))


def supports_trace_merge(manager: object) -> bool:

    return callable(getattr(type(manager), "merge_traces", None))


class ExplorationManager:
    """Maintains the exploration graph and manages branch scheduling."""

    def __init__(
        self,
        config: ExplorationManagerConfig,
        scheduler: MCTSScheduler | None = None,
        pruner: BranchPruner | None = None,
        merger: TraceMerger | None = None,
        llm_adapter: LLMAdapter | None = None,
        virtual_evaluator: VirtualEvaluatorLike | None = None,
    ) -> None:
        """Initialize exploration manager with selection settings."""

        self._config = config
        self._scheduler = scheduler
        self._pruner = pruner
        self._merger = merger
        self._llm_adapter = llm_adapter
        self._virtual_evaluator = virtual_evaluator

    def select_parents(self, graph: ExplorationGraph, plan: Plan) -> list[str]:
        """Select parent node identifiers for the next expansion.

        Responsibility:
            Choose parent nodes based on the plan and current graph.
        Input semantics:
            - graph: Current ExplorationGraph
            - plan: Plan for the current loop
        Output semantics:
            List of parent node IDs.
        Architecture mapping:
            Exploration Manager -> select_parents
        """

        _ = plan
        if self._scheduler is None:
            return []
        selected = self._scheduler.select_node(graph)
        if selected is None:
            return []
        return [selected]

    def register_node(self, graph: ExplorationGraph, node: NodeRecord) -> ExplorationGraph:
        """Register a new node in the exploration graph.

        Responsibility:
            Append a new node record and maintain edges for each parent.
        Input semantics:
            - graph: Current ExplorationGraph
            - node: NodeRecord metadata
        Output semantics:
            Updated ExplorationGraph with the new node and edges.
        Architecture mapping:
            Exploration Manager -> register_node
        """

        graph.nodes.append(node)
        for parent_id in node.parent_ids:
            graph.edges.append(GraphEdge(parent_id=parent_id, child_id=node.node_id))
        return graph

    def get_frontier(self, graph: ExplorationGraph, criteria: dict[str, str]) -> list[str]:
        """Return frontier nodes matching criteria.

        Responsibility:
            Provide candidate nodes for exploration.
        Input semantics:
            - graph: Current ExplorationGraph
            - criteria: Selection criteria
        Output semantics:
            List of node IDs matching the criteria.
        Architecture mapping:
            Exploration Manager -> get_frontier
        """

        _ = criteria
        return [node.node_id for node in graph.nodes if node.branch_state == BranchState.ACTIVE]

    def get_node_depth(self, graph: ExplorationGraph, node_id: str) -> int:
        node_map = {n.node_id: n for n in graph.nodes}
        if node_id not in node_map:
            return -1
        depth = 0
        current = node_map[node_id]
        while current.parent_ids:
            parent_id = current.parent_ids[0]
            parent = node_map.get(parent_id)
            if parent is None:
                break
            depth += 1
            current = parent
        return depth

    def get_children(self, graph: ExplorationGraph, node_id: str) -> list[str]:
        return [e.child_id for e in graph.edges if e.parent_id == node_id]

    def get_path_to_root(self, graph: ExplorationGraph, node_id: str) -> list[str]:
        node_map = {n.node_id: n for n in graph.nodes}
        if node_id not in node_map:
            return []
        path: list[str] = [node_id]
        current = node_map[node_id]
        while current.parent_ids:
            parent_id = current.parent_ids[0]
            parent = node_map.get(parent_id)
            if parent is None:
                break
            path.append(parent_id)
            current = parent
        return path

    def observe_feedback(
        self,
        graph: ExplorationGraph,
        node_id: str,
        score: float | None,
        decision: bool | None,
    ) -> None:
        if self._scheduler is None:
            return
        self._scheduler.observe_feedback(graph, node_id, score, decision)

    def generate_diverse_roots(
        self,
        graph: ExplorationGraph,
        task_summary: str,
        scenario_name: str,
        n_candidates: int = 5,
        k_forward: int = 2,
    ) -> ExplorationGraph:
        if self._virtual_evaluator is None:
            return self.register_node(graph, NodeRecord(node_id="root"))

        designs = self._virtual_evaluator.evaluate(
            task_summary=task_summary,
            scenario_name=scenario_name,
            iteration=0,
            previous_results=[],
            current_scores=[],
            n_candidates=n_candidates,
            k_forward=k_forward,
        )
        if not designs:
            return self.register_node(graph, NodeRecord(node_id="root"))

        for design in designs:
            node_id = f"root-{uuid.uuid4().hex[:8]}"
            proposal_hash = hashlib.sha256(design.summary.encode()).hexdigest()[:12]
            node = NodeRecord(
                node_id=node_id,
                parent_ids=[],
                proposal_id=f"layer0-{proposal_hash}",
                score=design.virtual_score if design.virtual_score > 0 else None,
            )
            graph = self.register_node(graph, node)
        return graph

    def prune_branches(self, graph: ExplorationGraph) -> ExplorationGraph:
        if self._pruner is None:
            return graph
        return self._pruner.prune(graph)

    def merge_traces(self, graph: ExplorationGraph, task_summary: str, scenario_name: str):
        if self._merger is None:
            return None
        traces = [node for node in graph.nodes if node.branch_state in (BranchState.ACTIVE,)]
        if len(traces) < 2:
            return None
        trace_dicts = []
        for node in traces:
            trace_dicts.append(
                {
                    "node_id": node.node_id,
                    "score": node.score,
                    "proposal_id": node.proposal_id,
                }
            )
        return self._merger.merge(trace_dicts, task_summary, scenario_name)
