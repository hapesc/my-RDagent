"""Persistence boundary for V3-owned public truth artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from v3.contracts.artifact import ArtifactSnapshot
from v3.contracts.branch import BranchSnapshot
from v3.contracts.exploration import BranchBoardSnapshot, BranchDecisionSnapshot
from v3.contracts.recovery import RecoveryAssessment
from v3.contracts.run import RunBoardSnapshot
from v3.contracts.stage import StageKey, StageSnapshot

if TYPE_CHECKING:
    from v3.contracts.exploration import DAGEdgeSnapshot, DAGNodeSnapshot, HypothesisSpec


@dataclass(frozen=True)
class ArtifactRecord:
    """Opaque persistence receipt returned by state-store implementations."""

    artifact_id: str
    storage_uri: str
    media_type: str


class StateStorePort(Protocol):
    """Port for writing and reading canonical V3 state snapshots."""

    def write_run_snapshot(self, run_snapshot: RunBoardSnapshot) -> ArtifactRecord: ...

    def write_branch_snapshot(self, branch_snapshot: BranchSnapshot) -> ArtifactRecord: ...

    def write_stage_snapshot(self, branch_id: str, stage_snapshot: StageSnapshot) -> ArtifactRecord: ...

    def write_artifact_snapshot(self, artifact_snapshot: ArtifactSnapshot) -> ArtifactRecord: ...

    def write_recovery_assessment(self, assessment: RecoveryAssessment) -> ArtifactRecord: ...

    def write_branch_decision(self, decision: BranchDecisionSnapshot) -> ArtifactRecord: ...

    def write_branch_board_snapshot(self, board_snapshot: BranchBoardSnapshot) -> ArtifactRecord: ...

    def write_hypothesis_spec(self, branch_id: str, hypothesis_spec: HypothesisSpec) -> ArtifactRecord: ...

    def load_run_snapshot(self, run_id: str) -> RunBoardSnapshot | None: ...

    def load_branch_snapshot(self, branch_id: str) -> BranchSnapshot | None: ...

    def load_hypothesis_spec(self, branch_id: str) -> HypothesisSpec | None: ...

    def load_stage_snapshot(
        self,
        branch_id: str,
        stage_key: StageKey,
        stage_iteration: int | None = None,
    ) -> StageSnapshot | None: ...

    def list_stage_snapshots(self, branch_id: str, stage_key: StageKey) -> list[StageSnapshot]: ...

    def list_artifact_snapshots(
        self,
        run_id: str,
        *,
        branch_id: str | None = None,
        stage_key: StageKey | None = None,
    ) -> list[ArtifactSnapshot]: ...

    def load_recovery_assessment(self, branch_id: str, stage_key: StageKey) -> RecoveryAssessment | None: ...

    def load_branch_board_snapshot(self, run_id: str) -> BranchBoardSnapshot | None: ...

    def list_branch_decisions(
        self,
        run_id: str,
        *,
        branch_id: str | None = None,
    ) -> list[BranchDecisionSnapshot]: ...

    def write_dag_node(self, node: DAGNodeSnapshot) -> ArtifactRecord: ...

    def load_dag_node(self, node_id: str) -> DAGNodeSnapshot | None: ...

    def list_dag_nodes(self, run_id: str) -> list[DAGNodeSnapshot]: ...

    def write_dag_edge(self, edge: DAGEdgeSnapshot) -> ArtifactRecord: ...

    def list_dag_edges(self, run_id: str) -> list[DAGEdgeSnapshot]: ...
