from __future__ import annotations

from pathlib import Path

import pytest

from v3.contracts.exploration import EdgeType
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.dag_service import DAGService


def test_shared_edge_create_typed_edge_persists_shared_edge(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    source = service.create_node(run_id="run-001", branch_id="branch-source")
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    edge = service.create_typed_edge(
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        edge_type=EdgeType.SHARED,
        weight=0.42,
    )

    assert edge.edge_type is EdgeType.SHARED
    assert edge.weight == pytest.approx(0.42)
    assert state_store.list_dag_edges("run-001") == [edge]


def test_shared_edge_create_typed_edge_persists_merged_edge(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    source = service.create_node(run_id="run-001", branch_id="branch-source")
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    edge = service.create_typed_edge(
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        edge_type=EdgeType.MERGED,
    )

    assert edge.edge_type is EdgeType.MERGED
    assert state_store.list_dag_edges("run-001") == [edge]


def test_shared_edge_create_typed_edge_rejects_missing_source_node(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    with pytest.raises(KeyError, match="source node not found: missing-source"):
        service.create_typed_edge(
            source_node_id="missing-source",
            target_node_id=target.node_id,
            edge_type=EdgeType.SHARED,
        )


def test_shared_edge_create_shared_edge_rejects_missing_source_node(tmp_path: Path) -> None:
    state_store = ArtifactStateStore(tmp_path / "state")
    service = DAGService(state_store)
    target = service.create_node(run_id="run-001", branch_id="branch-target")

    with pytest.raises(KeyError, match="source node not found: missing-source"):
        service.create_shared_edge(
            source_node_id="missing-source",
            target_node_id=target.node_id,
        )
