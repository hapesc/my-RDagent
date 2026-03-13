from __future__ import annotations

import pytest

from v2.models import BranchState, ExperimentNode, NodeRecord, RunStatus, StepState


def test_run_status_matches_v1_values() -> None:
    assert [member.value for member in RunStatus] == [
        "CREATED",
        "RUNNING",
        "PAUSED",
        "STOPPED",
        "COMPLETED",
        "FAILED",
    ]


def test_step_state_matches_v1_values() -> None:
    assert [member.value for member in StepState] == [
        "CREATED",
        "PROPOSING",
        "EXPERIMENT_READY",
        "CODING",
        "RUNNING",
        "FEEDBACK",
        "RECORDED",
        "FAILED",
        "PAUSED",
        "COMPLETED",
        "STOPPED",
    ]


def test_branch_state_matches_v1_values() -> None:
    assert [member.value for member in BranchState] == ["ACTIVE", "PRUNED", "MERGED"]


def test_node_record_supports_dag_parent_ids() -> None:
    node = NodeRecord(id="n1", parent_ids=["p1", "p2"])
    assert node.id == "n1"
    assert node.parent_ids == ["p1", "p2"]


def test_experiment_node_supports_dag_parent_node_ids() -> None:
    node = ExperimentNode(id="e1", parent_node_ids=["p1", "p2"])
    assert node.id == "e1"
    assert node.parent_node_ids == ["p1", "p2"]


def test_experiment_node_requires_parent_node_ids_field() -> None:
    with pytest.raises(ValueError):
        ExperimentNode.model_validate({"id": "e1"})
