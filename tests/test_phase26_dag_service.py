from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from v3.contracts.exploration import EdgeType, NodeMetrics
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.dag_service import DAGService


def test_dag_service_creates_root_and_child_nodes(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)

    root = service.create_node(run_id="r1", branch_id="b1")
    child = service.create_node(run_id="r1", branch_id="b2", parent_node_ids=[root.node_id])

    edges = state_store.list_dag_edges("r1")

    assert root.depth == 0
    assert child.depth == 1
    assert edges == [
        state_store.list_dag_edges("r1")[0].model_copy(
            update={
                "source_node_id": root.node_id,
                "target_node_id": child.node_id,
                "edge_type": EdgeType.PARENT,
                "weight": 1.0,
            }
        )
    ]


def test_dag_service_rejects_missing_and_self_referencing_parents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)

    with pytest.raises(KeyError):
        service.create_node(run_id="r1", branch_id="b1", parent_node_ids=["missing"])

    monkeypatch.setattr("v3.orchestration.dag_service.uuid4", lambda: SimpleNamespace(hex="abcdefabcdef1234"))
    with pytest.raises(ValueError):
        service.create_node(run_id="r1", branch_id="b1", parent_node_ids=["dag-node-abcdefabcdef"])


def test_dag_service_reads_and_traverses_graph(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)

    n1 = service.create_node(run_id="r1", branch_id="b1")
    n2 = service.create_node(run_id="r1", branch_id="b1", parent_node_ids=[n1.node_id])
    n3 = service.create_node(run_id="r1", branch_id="b1", parent_node_ids=[n2.node_id])
    n4 = service.create_node(run_id="r1", branch_id="b2", parent_node_ids=[n1.node_id])

    assert service.get_node(n1.node_id) == n1
    assert service.get_node("missing") is None
    assert {node.node_id for node in service.list_nodes("r1")} == {
        n1.node_id,
        n2.node_id,
        n3.node_id,
        n4.node_id,
    }
    assert service.get_ancestors(n3.node_id, "r1") == {n1.node_id, n2.node_id}
    assert service.get_descendants(n1.node_id, "r1") == {n2.node_id, n3.node_id, n4.node_id}
    assert service.get_frontier("r1") == {n3.node_id, n4.node_id}


def test_dag_service_updates_metrics(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    node = service.create_node(run_id="r1", branch_id="b1")

    updated = service.update_node_metrics(node.node_id, NodeMetrics(validation_score=0.8))

    assert updated.node_metrics.validation_score == 0.8
    assert service.get_node(node.node_id) == updated
