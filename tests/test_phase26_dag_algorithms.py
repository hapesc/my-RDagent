from __future__ import annotations

from pathlib import Path

from v3.algorithms.dag import get_ancestors, get_depth, get_descendants, get_frontier
from v3.contracts.exploration import DAGEdgeSnapshot, DAGNodeSnapshot
from v3.orchestration.artifact_state_store import ArtifactStateStore


def test_get_ancestors_returns_all_upstream_nodes() -> None:
    parent_map = {"n3": ["n2"], "n2": ["n1"], "n1": []}

    assert get_ancestors("n3", parent_map) == {"n1", "n2"}
    assert get_ancestors("n1", {"n1": []}) == set()


def test_get_descendants_returns_all_downstream_nodes() -> None:
    child_map = {"n1": ["n2", "n3"], "n2": ["n4"], "n3": [], "n4": []}

    assert get_descendants("n1", child_map) == {"n2", "n3", "n4"}


def test_get_frontier_returns_leaf_nodes() -> None:
    parent_map = {"n1": [], "n2": ["n1"], "n3": ["n1"], "n4": ["n2"]}

    assert get_frontier(parent_map, {"n1", "n2", "n3", "n4"}) == {"n3", "n4"}


def test_get_depth_returns_longest_path_from_root() -> None:
    parent_map = {"n4": ["n2"], "n2": ["n1"], "n1": []}

    assert get_depth("n4", parent_map) == 2
    assert get_depth("n1", {"n1": []}) == 0


def test_artifact_state_store_persists_dag_nodes_and_edges(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    node_a = DAGNodeSnapshot(node_id="n1", run_id="run-dag", branch_id="b1")
    node_b = DAGNodeSnapshot(node_id="n2", run_id="run-dag", branch_id="b2", parent_node_ids=["n1"], depth=1)
    edge = DAGEdgeSnapshot(source_node_id="n1", target_node_id="n2")

    node_record = state_store.write_dag_node(node_a)
    state_store.write_dag_node(node_b)
    edge_record = state_store.write_dag_edge(edge)

    assert Path(node_record.storage_uri).exists()
    assert Path(edge_record.storage_uri).exists()
    assert state_store.load_dag_node("n1") == node_a
    assert state_store.load_dag_node("missing") is None
    assert state_store.list_dag_nodes("run-dag") == [node_a, node_b]
    assert state_store.list_dag_edges("run-dag") == [edge]
