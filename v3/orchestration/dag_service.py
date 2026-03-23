"""DAG topology service over the persisted exploration graph."""

from __future__ import annotations

from uuid import uuid4

from v3.algorithms.dag import get_ancestors, get_depth, get_descendants, get_frontier
from v3.contracts.exploration import DAGEdgeSnapshot, DAGNodeSnapshot, EdgeType, NodeMetrics
from v3.ports.state_store import StateStorePort


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

    def update_node_metrics(self, node_id: str, metrics: NodeMetrics) -> DAGNodeSnapshot:
        node = self._state_store.load_dag_node(node_id)
        if node is None:
            raise KeyError(f"node not found: {node_id}")
        updated = node.model_copy(update={"node_metrics": metrics})
        self._state_store.write_dag_node(updated)
        return updated

    def _build_parent_map(self, run_id: str) -> dict[str, list[str]]:
        return {
            node.node_id: list(node.parent_node_ids)
            for node in self._state_store.list_dag_nodes(run_id)
        }

    def _build_child_map(self, run_id: str) -> dict[str, list[str]]:
        nodes = self._state_store.list_dag_nodes(run_id)
        child_map: dict[str, list[str]] = {node.node_id: [] for node in nodes}
        for node in nodes:
            for parent_id in node.parent_node_ids:
                child_map.setdefault(parent_id, []).append(node.node_id)
        return child_map


__all__ = ["DAGService"]
