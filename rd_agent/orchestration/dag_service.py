"""DAG topology service over the persisted exploration graph."""

from __future__ import annotations

from uuid import uuid4

from rd_agent.algorithms.dag import get_ancestors, get_depth, get_descendants, get_frontier
from rd_agent.contracts.exploration import ComponentClass, DAGEdgeSnapshot, DAGNodeSnapshot, EdgeType, NodeMetrics
from rd_agent.ports.state_store import StateStorePort


class DAGService:
    """Graph topology layer over the branch lifecycle model."""

    def __init__(self, state_store: StateStorePort) -> None:
        self._state_store = state_store

    def create_node(
        self,
        *,
        run_id: str,
        branch_id: str,
        parent_node_ids: list[str] | None = None,
        node_metrics: NodeMetrics | None = None,
    ) -> DAGNodeSnapshot:
        parent_ids = list(parent_node_ids or [])
        node_id = f"dag-node-{uuid4().hex[:12]}"
        if node_id in parent_ids:
            raise ValueError(f"cycle detected: {node_id} is its own ancestor")

        for parent_id in parent_ids:
            parent = self._state_store.load_dag_node(parent_id)
            if parent is None:
                raise KeyError(f"parent node not found: {parent_id}")
            if parent.run_id != run_id:
                raise ValueError(f"parent node belongs to different run: {parent_id}")

        parent_map = self._build_parent_map(run_id)
        parent_map[node_id] = parent_ids
        ancestors = get_ancestors(node_id, parent_map)
        if node_id in ancestors:
            raise ValueError(f"cycle detected: {node_id} is its own ancestor")

        node = DAGNodeSnapshot(
            node_id=node_id,
            run_id=run_id,
            branch_id=branch_id,
            parent_node_ids=parent_ids,
            depth=get_depth(node_id, parent_map),
            node_metrics=node_metrics or NodeMetrics(),
        )
        self._state_store.write_dag_node(node)

        for parent_id in parent_ids:
            self._state_store.write_dag_edge(
                DAGEdgeSnapshot(
                    source_node_id=parent_id,
                    target_node_id=node_id,
                    edge_type=EdgeType.PARENT,
                    weight=1.0,
                )
            )
        return node

    def get_node(self, node_id: str) -> DAGNodeSnapshot | None:
        return self._state_store.load_dag_node(node_id)

    def list_nodes(self, run_id: str) -> list[DAGNodeSnapshot]:
        return self._state_store.list_dag_nodes(run_id)

    def get_ancestors(self, node_id: str, run_id: str) -> set[str]:
        return get_ancestors(node_id, self._build_parent_map(run_id))

    def get_descendants(self, node_id: str, run_id: str) -> set[str]:
        return get_descendants(node_id, self._build_child_map(run_id))

    def get_frontier(self, run_id: str) -> set[str]:
        parent_map = self._build_parent_map(run_id)
        return get_frontier(parent_map, set(parent_map.keys()))

    def create_typed_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
    ) -> DAGEdgeSnapshot:
        """Create a non-parent DAG edge for sharing/merge topology traceability."""

        source = self._state_store.load_dag_node(source_node_id)
        if source is None:
            raise KeyError(f"source node not found: {source_node_id}")
        target = self._state_store.load_dag_node(target_node_id)
        if target is None:
            raise KeyError(f"target node not found: {target_node_id}")

        edge = DAGEdgeSnapshot(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            weight=weight,
        )
        self._state_store.write_dag_edge(edge)
        return edge

    def create_shared_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        weight: float = 1.0,
    ) -> DAGEdgeSnapshot:
        return self.create_typed_edge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=EdgeType.SHARED,
            weight=weight,
        )

    def create_merged_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        weight: float = 1.0,
    ) -> DAGEdgeSnapshot:
        return self.create_typed_edge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=EdgeType.MERGED,
            weight=weight,
        )

    def update_node_metrics(self, node_id: str, metrics: NodeMetrics) -> DAGNodeSnapshot:
        node = self._state_store.load_dag_node(node_id)
        if node is None:
            raise KeyError(f"node not found: {node_id}")
        updated = node.model_copy(update={"node_metrics": metrics})
        self._state_store.write_dag_node(updated)
        return updated

    def collect_branch_component_scores(
        self,
        run_id: str,
        state_store: StateStorePort,
    ) -> tuple[dict[str, dict[str, float]], dict[str, set[str]]]:
        """Collect per-branch component score views for convergence consumers."""

        branch_scores: dict[str, dict[str, float]] = {}
        branch_classes: dict[str, set[str]] = {}
        branch_to_nodes: dict[str, list[DAGNodeSnapshot]] = {}
        for node in self.list_nodes(run_id):
            branch_to_nodes.setdefault(node.branch_id, []).append(node)

        for branch_id, branch_nodes in branch_to_nodes.items():
            hypothesis = state_store.load_hypothesis_spec(branch_id)
            if hypothesis is None or not hypothesis.component_classes:
                continue
            classes = {
                component_class.value if isinstance(component_class, ComponentClass) else str(component_class)
                for component_class in hypothesis.component_classes
            }
            latest = max(branch_nodes, key=lambda node: node.depth)
            branch_classes[branch_id] = classes
            branch_scores[branch_id] = {
                component_class: latest.node_metrics.validation_score for component_class in classes
            }
        return branch_scores, branch_classes

    def _build_parent_map(self, run_id: str) -> dict[str, list[str]]:
        return {node.node_id: list(node.parent_node_ids) for node in self._state_store.list_dag_nodes(run_id)}

    def _build_child_map(self, run_id: str) -> dict[str, list[str]]:
        nodes = self._state_store.list_dag_nodes(run_id)
        child_map: dict[str, list[str]] = {node.node_id: [] for node in nodes}
        for node in nodes:
            for parent_id in node.parent_node_ids:
                child_map.setdefault(parent_id, []).append(node.node_id)
        return child_map


__all__ = ["DAGService"]
