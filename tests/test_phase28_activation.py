from __future__ import annotations

from pathlib import Path

import pytest

from v3.contracts.tool_io import BranchMergeRequest
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.branch_board_service import BranchBoardService
from v3.orchestration.branch_merge_service import BranchMergeService
from v3.orchestration.convergence_service import ConvergenceService
from v3.orchestration.dag_service import DAGService
from tests.test_phase27_merge_synthesis import _CapturingMerger, _seed_run


def _build_merge_service(tmp_path: Path, *, holdout_score: float) -> BranchMergeService:
    state_store = ArtifactStateStore(tmp_path / "state")
    dag_service = DAGService(state_store)
    _seed_run(state_store, dag_service)
    board_service = BranchBoardService(state_store)
    convergence_service = ConvergenceService(state_store=state_store, board_service=board_service)
    return BranchMergeService(
        state_store=state_store,
        convergence_service=convergence_service,
        board_service=board_service,
        merger=_CapturingMerger(holdout_score=holdout_score),
        dag_service=dag_service,
    )


def test_validate_merge_holdout_removed() -> None:
    with pytest.raises(ImportError):
        exec("from v3.algorithms.merge import validate_merge_holdout", {})


def test_merge_still_works_with_inline_comparison(tmp_path: Path) -> None:
    accepting_service = _build_merge_service(tmp_path / "accept", holdout_score=0.95)
    accepted = accepting_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9},
            "branch-b": {"ensemble": 0.9},
        },
    )

    rejecting_service = _build_merge_service(tmp_path / "reject", holdout_score=0.70)
    rejected = rejecting_service.merge_with_complementarity(
        BranchMergeRequest(run_id="run-merge", minimum_quality=0.7),
        {
            "branch-a": {"model": 0.9},
            "branch-b": {"ensemble": 0.9},
        },
    )

    assert accepted.outcome.failure_reason is None
    assert accepted.outcome.merged_branch_id == "branch-a"
    assert rejected.outcome.failure_reason == "holdout_validation_failed"
