from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RunStatus(str, Enum):  # noqa: UP042
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepState(str, Enum):  # noqa: UP042
    CREATED = "CREATED"
    PROPOSING = "PROPOSING"
    EXPERIMENT_READY = "EXPERIMENT_READY"
    CODING = "CODING"
    RUNNING = "RUNNING"
    FEEDBACK = "FEEDBACK"
    RECORDED = "RECORDED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"


class BranchState(str, Enum):  # noqa: UP042
    ACTIVE = "ACTIVE"
    PRUNED = "PRUNED"
    MERGED = "MERGED"


class NodeRecord(BaseModel):
    id: str
    parent_ids: list[str]


class ExperimentNode(BaseModel):
    id: str
    parent_node_ids: list[str]


__all__ = ["RunStatus", "StepState", "BranchState", "NodeRecord", "ExperimentNode"]
