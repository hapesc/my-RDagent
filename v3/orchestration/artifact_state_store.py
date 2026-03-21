"""Canonical JSON persistence for V3 public state artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from v3.contracts.artifact import ArtifactSnapshot
from v3.contracts.branch import BranchSnapshot
from v3.contracts.exploration import BranchBoardSnapshot, BranchDecisionSnapshot
from v3.contracts.recovery import RecoveryAssessment
from v3.contracts.run import RunBoardSnapshot
from v3.contracts.stage import StageKey, StageSnapshot
from v3.orchestration.branch_isolation_service import BranchIsolationService
from v3.ports.state_store import ArtifactRecord, StateStorePort

ModelT = TypeVar("ModelT", bound=BaseModel)


class ArtifactStateStore(StateStorePort):
    """Filesystem-backed persistence for V3-owned public truth."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._isolation = BranchIsolationService(self._root)

    def write_run_snapshot(self, run_snapshot: RunBoardSnapshot) -> ArtifactRecord:
        path = self._root / "runs" / run_snapshot.run_id / "run-board.json"
        self._write_model(path, run_snapshot)
        return ArtifactRecord(
            artifact_id=f"run-board:{run_snapshot.run_id}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_branch_snapshot(self, branch_snapshot: BranchSnapshot) -> ArtifactRecord:
        path = self._isolation.branch_root(branch_snapshot.branch_id) / "branch.json"
        self._write_model(path, branch_snapshot)
        return ArtifactRecord(
            artifact_id=f"branch:{branch_snapshot.branch_id}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_stage_snapshot(self, branch_id: str, stage_snapshot: StageSnapshot) -> ArtifactRecord:
        path = self._root / "branches" / branch_id / "stages" / f"{stage_snapshot.stage_key}.json"
        history_path = (
            self._root
            / "branches"
            / branch_id
            / "stages"
            / str(stage_snapshot.stage_key)
            / f"iteration-{stage_snapshot.stage_iteration:04d}.json"
        )
        self._write_model(path, stage_snapshot)
        self._write_model(history_path, stage_snapshot)
        return ArtifactRecord(
            artifact_id=f"stage:{branch_id}:{stage_snapshot.stage_key}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_artifact_snapshot(self, artifact_snapshot: ArtifactSnapshot) -> ArtifactRecord:
        run_id = self._run_id_for_branch(artifact_snapshot.branch_id) or "run-unassigned"
        path = self._isolation.artifact_root(run_id, artifact_snapshot.branch_id) / str(artifact_snapshot.stage_key)
        path = path / f"{artifact_snapshot.artifact_id}.json"
        self._write_model(path, artifact_snapshot)
        return ArtifactRecord(
            artifact_id=artifact_snapshot.artifact_id,
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_recovery_assessment(self, assessment: RecoveryAssessment) -> ArtifactRecord:
        path = (
            self._root
            / "recovery"
            / assessment.run_id
            / assessment.branch_id
            / f"{assessment.stage_key}.json"
        )
        self._write_model(path, assessment)
        return ArtifactRecord(
            artifact_id=f"recovery:{assessment.branch_id}:{assessment.stage_key}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_branch_decision(self, decision: BranchDecisionSnapshot) -> ArtifactRecord:
        path = self._root / "runs" / decision.run_id / "exploration" / "decisions" / f"{decision.decision_id}.json"
        self._write_model(path, decision)
        return ArtifactRecord(
            artifact_id=decision.decision_id,
            storage_uri=str(path),
            media_type="application/json",
        )

    def write_branch_board_snapshot(self, board_snapshot: BranchBoardSnapshot) -> ArtifactRecord:
        path = self._root / "runs" / board_snapshot.run_id / "exploration" / "branch-board.json"
        self._write_model(path, board_snapshot)
        return ArtifactRecord(
            artifact_id=f"branch-board:{board_snapshot.run_id}",
            storage_uri=str(path),
            media_type="application/json",
        )

    def load_run_snapshot(self, run_id: str) -> RunBoardSnapshot | None:
        return self._read_model(self._root / "runs" / run_id / "run-board.json", RunBoardSnapshot)

    def load_branch_snapshot(self, branch_id: str) -> BranchSnapshot | None:
        return self._read_model(self._isolation.branch_root(branch_id) / "branch.json", BranchSnapshot)

    def load_stage_snapshot(
        self,
        branch_id: str,
        stage_key: StageKey,
        stage_iteration: int | None = None,
    ) -> StageSnapshot | None:
        if stage_iteration is not None:
            return self._read_model(
                self._root
                / "branches"
                / branch_id
                / "stages"
                / str(stage_key)
                / f"iteration-{stage_iteration:04d}.json",
                StageSnapshot,
            )
        return self._read_model(self._root / "branches" / branch_id / "stages" / f"{stage_key}.json", StageSnapshot)

    def list_stage_snapshots(self, branch_id: str, stage_key: StageKey) -> list[StageSnapshot]:
        history_root = self._root / "branches" / branch_id / "stages" / str(stage_key)
        if not history_root.exists():
            latest = self.load_stage_snapshot(branch_id, stage_key)
            return [] if latest is None else [latest]
        snapshots = [
            StageSnapshot.model_validate(json.loads(path.read_text()))
            for path in sorted(history_root.glob("iteration-*.json"))
        ]
        return sorted(snapshots, key=lambda snapshot: snapshot.stage_iteration)

    def list_artifact_snapshots(
        self,
        run_id: str,
        *,
        branch_id: str | None = None,
        stage_key: StageKey | None = None,
    ) -> list[ArtifactSnapshot]:
        base = self._root / "artifacts" / run_id
        if branch_id is not None:
            base = self._isolation.artifact_root(run_id, branch_id)
        if stage_key is not None:
            if branch_id is None:
                return []
            base = base / str(stage_key)
        if not base.exists():
            return []
        snapshots: list[ArtifactSnapshot] = []
        for path in sorted(base.rglob("*.json")):
            snapshot = ArtifactSnapshot.model_validate(json.loads(path.read_text()))
            if branch_id is not None and snapshot.branch_id != branch_id:
                continue
            if stage_key is not None and snapshot.stage_key != stage_key:
                continue
            snapshots.append(snapshot)
        return snapshots

    def load_recovery_assessment(self, branch_id: str, stage_key: StageKey) -> RecoveryAssessment | None:
        recovery_root = self._root / "recovery"
        if not recovery_root.exists():
            return None
        matches = sorted(recovery_root.glob(f"*/{branch_id}/{stage_key}.json"))
        if not matches:
            return None
        return self._read_model(matches[-1], RecoveryAssessment)

    def load_branch_board_snapshot(self, run_id: str) -> BranchBoardSnapshot | None:
        return self._read_model(
            self._root / "runs" / run_id / "exploration" / "branch-board.json",
            BranchBoardSnapshot,
        )

    def list_branch_decisions(
        self,
        run_id: str,
        *,
        branch_id: str | None = None,
    ) -> list[BranchDecisionSnapshot]:
        decisions_root = self._root / "runs" / run_id / "exploration" / "decisions"
        if not decisions_root.exists():
            return []
        decisions = [
            BranchDecisionSnapshot.model_validate(json.loads(path.read_text()))
            for path in sorted(decisions_root.glob("*.json"))
        ]
        if branch_id is None:
            return decisions
        return [decision for decision in decisions if decision.branch_id == branch_id]

    def _run_id_for_branch(self, branch_id: str) -> str | None:
        branch = self.load_branch_snapshot(branch_id)
        if branch is None:
            return None
        return branch.run_id

    def _write_model(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2) + "\n")

    def _read_model(self, path: Path, model_type: type[ModelT]) -> ModelT | None:
        if not path.exists():
            return None
        return model_type.model_validate(json.loads(path.read_text()))


__all__ = ["ArtifactStateStore"]
