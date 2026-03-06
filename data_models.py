"""Unified data model layer for the R&D Agent MVP."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _to_iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _from_iso_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def model_to_dict(value: Any) -> Any:
    """Serialize dataclass objects to JSON-compatible dictionaries."""

    if isinstance(value, datetime):
        return _to_iso_utc(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field_info.name: model_to_dict(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, dict):
        return {key: model_to_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [model_to_dict(item) for item in value]
    return value


class ValueEnum(str, Enum):
    """String enum that renders as its value."""

    def __str__(self) -> str:  # pragma: no cover - tiny helper
        return self.value


class RunStatus(ValueEnum):
    """Lifecycle state for a run session."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepState(ValueEnum):
    """Loop step state used by experiment nodes."""

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


class EventType(ValueEnum):
    """Canonical event types for MVP trace payloads."""

    RUN_CREATED = "run.created"
    HYPOTHESIS_GENERATED = "hypothesis.generated"
    EXPERIMENT_GENERATED = "experiment.generated"
    CODING_ROUND = "coding.round"
    EXECUTION_FINISHED = "execution.finished"
    FEEDBACK_GENERATED = "feedback.generated"
    TRACE_RECORDED = "trace.recorded"
    RUN_PAUSED = "run.paused"
    RUN_RESUMED = "run.resumed"
    RUN_STOPPED = "run.stopped"


CANONICAL_TRACE_EVENT_TYPES = (
    EventType.RUN_CREATED,
    EventType.HYPOTHESIS_GENERATED,
    EventType.EXPERIMENT_GENERATED,
    EventType.CODING_ROUND,
    EventType.EXECUTION_FINISHED,
    EventType.FEEDBACK_GENERATED,
    EventType.TRACE_RECORDED,
)


@dataclass
class StopConditions:
    """Stop conditions applied to a run session."""

    max_loops: int = 20
    max_steps: Optional[int] = None
    max_duration_sec: int = 14400


@dataclass
class RunSession:
    """Top-level run context and lifecycle metadata."""

    run_id: str
    scenario: str
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    stop_conditions: StopConditions = field(default_factory=StopConditions)
    entry_input: Dict[str, Any] = field(default_factory=dict)
    active_branch_ids: List[str] = field(default_factory=lambda: ["main"])
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    def update_status(self, status: RunStatus) -> None:
        self.status = status
        self.updated_at = utc_now()

    def to_dict(self) -> Dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunSession":
        stop_conditions = data.get("stop_conditions", {})
        return cls(
            run_id=str(data["run_id"]),
            scenario=str(data["scenario"]),
            status=RunStatus(str(data["status"])),
            created_at=_from_iso_utc(str(data["created_at"])),
            updated_at=_from_iso_utc(str(data["updated_at"])),
            stop_conditions=StopConditions(
                max_loops=int(stop_conditions.get("max_loops", 20)),
                max_steps=(
                    int(stop_conditions["max_steps"])
                    if stop_conditions.get("max_steps") is not None
                    else None
                ),
                max_duration_sec=int(stop_conditions.get("max_duration_sec", 14400)),
            ),
            entry_input=dict(data.get("entry_input", {})),
            active_branch_ids=list(data.get("active_branch_ids", ["main"])),
            config_snapshot=dict(data.get("config_snapshot", {})),
        )


@dataclass
class ExperimentNode:
    """DAG node for a single experiment step."""

    node_id: str
    run_id: str
    branch_id: str
    parent_node_id: Optional[str] = None
    loop_index: int = 0
    step_state: StepState = StepState.RECORDED
    hypothesis: Dict[str, Any] = field(default_factory=dict)
    workspace_ref: str = ""
    result_ref: str = ""
    feedback_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentNode":
        return cls(
            node_id=str(data["node_id"]),
            run_id=str(data["run_id"]),
            branch_id=str(data["branch_id"]),
            parent_node_id=(
                str(data["parent_node_id"]) if data.get("parent_node_id") is not None else None
            ),
            loop_index=int(data.get("loop_index", 0)),
            step_state=StepState(str(data.get("step_state", StepState.RECORDED.value))),
            hypothesis=dict(data.get("hypothesis", {})),
            workspace_ref=str(data.get("workspace_ref", "")),
            result_ref=str(data.get("result_ref", "")),
            feedback_ref=str(data.get("feedback_ref", "")),
        )


@dataclass
class FileManifestEntry:
    """File digest for a workspace snapshot."""

    path: str
    sha256: str


@dataclass
class WorkspaceSnapshot:
    """Workspace checkpoint descriptor."""

    workspace_id: str
    run_id: str
    file_manifest: List[FileManifestEntry] = field(default_factory=list)
    checkpoint_type: str = "zip"
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return model_to_dict(self)


@dataclass
class FeedbackRecord:
    """Feedback decision and diagnostics for a node."""

    feedback_id: str
    decision: bool
    acceptable: bool
    reason: str
    observations: str = ""
    code_change_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return model_to_dict(self)


@dataclass
class Event:
    """Canonical trace event model."""

    event_id: str
    run_id: str
    branch_id: str
    loop_index: int
    step_name: str
    event_type: EventType
    timestamp: datetime = field(default_factory=utc_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=str(data["event_id"]),
            run_id=str(data["run_id"]),
            branch_id=str(data["branch_id"]),
            loop_index=int(data["loop_index"]),
            step_name=str(data["step_name"]),
            event_type=EventType(str(data["event_type"])),
            timestamp=_from_iso_utc(str(data["timestamp"])),
            payload=dict(data.get("payload", {})),
        )


@dataclass
class TaskSpec:
    """Normalized task description and constraints."""

    task_id: str
    description: str
    constraints: Dict[str, str] = field(default_factory=dict)


@dataclass
class DataSplitManifest:
    """Fixed train/val/test split indices for deterministic evaluation."""

    train_ids: List[str] = field(default_factory=list)
    val_ids: List[str] = field(default_factory=list)
    test_ids: List[str] = field(default_factory=list)
    seed: int = 0


@dataclass
class DataSummaryReport:
    """Dataset summary statistics and schema notes."""

    row_count: int = 0
    field_types: Dict[str, str] = field(default_factory=dict)
    missing_rates: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskArtifacts:
    """Artifacts produced by the task intake and data splitter module."""

    task_spec: TaskSpec
    split_manifest: DataSplitManifest
    summary_report: DataSummaryReport


@dataclass
class ExplorationGraph:
    """Exploration graph for tracking proposals, artifacts, and scores."""

    nodes: List["NodeRecord"] = field(default_factory=list)
    edges: List["GraphEdge"] = field(default_factory=list)


@dataclass
class GraphEdge:
    """Directed edge between two exploration nodes."""

    parent_id: str
    child_id: str


@dataclass
class NodeRecord:
    """Metadata for a single node in the exploration graph."""

    node_id: str
    parent_ids: List[str] = field(default_factory=list)
    proposal_id: Optional[str] = None
    artifact_id: Optional[str] = None
    score_id: Optional[str] = None


@dataclass
class Plan:
    """Plan for allocating exploration and exploitation within a loop."""

    plan_id: str
    exploration_strength: float = 0.0
    budget_allocation: Dict[str, float] = field(default_factory=dict)
    guidance: List[str] = field(default_factory=list)


@dataclass
class Proposal:
    """Structured proposal produced by the reasoning service."""

    proposal_id: str
    summary: str
    constraints: List[str] = field(default_factory=list)
    virtual_score: float = 0.0


@dataclass
class CodeArtifact:
    """Runnable code artifact generated by the development service."""

    artifact_id: str
    description: str
    location: str


@dataclass
class Score:
    """Evaluation score with metric metadata."""

    score_id: str
    value: float
    metric_name: str
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoopState:
    """State for the R&D loop execution."""

    loop_id: str
    iteration: int = 0
    status: RunStatus = RunStatus.CREATED


@dataclass
class LoopContext:
    """Bundled context for loop state and budget tracking."""

    loop_state: LoopState
    budget: "BudgetLedger"
    run_session: Optional[RunSession] = None


@dataclass
class BudgetLedger:
    """Tracks time and resource usage for the loop."""

    total_time_budget: float
    elapsed_time: float = 0.0


@dataclass
class PlanningContext:
    """Input context for plan generation."""

    loop_state: LoopState
    budget: BudgetLedger
    history_summary: Dict[str, str] = field(default_factory=dict)


@dataclass
class ContextPack:
    """Context bundle from memory service for reasoning."""

    items: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Execution output and runtime metadata."""

    run_id: str
    exit_code: int
    logs_ref: str
    artifacts_ref: str


@dataclass
class EvalResult:
    """Evaluation result with score reference."""

    score: Score
    report_ref: str


@dataclass
class PhaseResultMeta:
    """Minimal metadata for a completed loop phase."""

    proposal_id: Optional[str] = None
    artifact_id: Optional[str] = None
    score_id: Optional[str] = None
    notes: str = ""
