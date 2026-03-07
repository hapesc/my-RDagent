"""Service scaffold for the Exploration Manager module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from data_models import BranchState, ExplorationGraph, NodeRecord, Plan
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


class ExplorationManager:
    """Maintains the exploration graph and manages branch scheduling."""

    def __init__(
        self,
        config: ExplorationManagerConfig,
        scheduler: Optional[MCTSScheduler] = None,
        pruner: Optional[BranchPruner] = None,
        merger: Optional[TraceMerger] = None,
        llm_adapter: Optional[LLMAdapter] = None,
    ) -> None:
        """Initialize exploration manager with selection settings."""

        self._config = config
        self._scheduler = scheduler
        self._pruner = pruner
        self._merger = merger
        self._llm_adapter = llm_adapter

    def select_parents(self, graph: ExplorationGraph, plan: Plan) -> List[str]:
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
            Append a new node record to the exploration graph.
        Input semantics:
            - graph: Current ExplorationGraph
            - node: NodeRecord metadata
        Output semantics:
            Updated ExplorationGraph with the new node.
        Architecture mapping:
            Exploration Manager -> register_node
        """

        graph.nodes.append(node)
        return graph

    def get_frontier(self, graph: ExplorationGraph, criteria: Dict[str, str]) -> List[str]:
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
