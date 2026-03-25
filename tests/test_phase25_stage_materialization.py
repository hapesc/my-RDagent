from __future__ import annotations

from pathlib import Path

from rd_agent.contracts.branch import BranchLineage, BranchScore, BranchSnapshot, BranchStatus
from rd_agent.contracts.stage import StageKey, StageSnapshot, StageStatus
from rd_agent.orchestration.artifact_state_store import ArtifactStateStore
from rd_agent.orchestration.stage_transition_service import StageTransitionService


def _seed_branch(
    tmp_path: Path,
    *,
    stage_key: StageKey,
    next_stage_key: StageKey | None,
) -> tuple[ArtifactStateStore, StageTransitionService, StageSnapshot]:
    state_store = ArtifactStateStore(tmp_path / "state")
    stage = StageSnapshot(
        stage_key=stage_key,
        stage_iteration=1,
        status=StageStatus.READY,
        summary=f"{stage_key.value} summary",
        artifact_ids=[f"{stage_key.value}-artifact-001"],
        next_stage_key=next_stage_key,
    )
    branch = BranchSnapshot(
        branch_id="branch-001",
        run_id="run-001",
        label="Primary branch",
        status=BranchStatus.ACTIVE,
        current_stage_key=stage_key,
        stages=[stage],
        score=BranchScore(
            exploration_priority=0.8,
            result_quality=0.5,
            rationale="Primary branch remains active.",
        ),
        lineage=BranchLineage(source_summary="Created in test state."),
        artifact_ids=list(stage.artifact_ids),
    )
    state_store.write_branch_snapshot(branch)
    state_store.write_stage_snapshot(branch.branch_id, stage)
    return state_store, StageTransitionService(state_store), stage


def test_publish_stage_complete_materializes_not_started_next_stage(tmp_path: Path) -> None:
    _, service, stage = _seed_branch(
        tmp_path,
        stage_key=StageKey.FRAMING,
        next_stage_key=StageKey.BUILD,
    )

    branch = service.publish_stage_complete("branch-001", stage)

    assert branch.current_stage_key is StageKey.BUILD
    build_stage = next(item for item in branch.stages if item.stage_key is StageKey.BUILD)
    assert build_stage.status is StageStatus.NOT_STARTED
    assert build_stage.summary == "Prepared and requires preflight before execution."
    assert build_stage.stage_iteration == 1
    assert build_stage.artifact_ids == []


def test_publish_stage_complete_keeps_final_stage_current_when_no_next_stage(tmp_path: Path) -> None:
    _, service, stage = _seed_branch(
        tmp_path,
        stage_key=StageKey.SYNTHESIZE,
        next_stage_key=None,
    )

    branch = service.publish_stage_complete("branch-001", stage)

    assert branch.current_stage_key is StageKey.SYNTHESIZE
    assert [item.stage_key for item in branch.stages] == [StageKey.SYNTHESIZE]


def test_publish_stage_complete_deduplicates_not_started_next_stage(tmp_path: Path) -> None:
    _, service, stage = _seed_branch(
        tmp_path,
        stage_key=StageKey.FRAMING,
        next_stage_key=StageKey.BUILD,
    )

    service.publish_stage_complete("branch-001", stage)
    branch = service.publish_stage_complete("branch-001", stage)

    build_stages = [item for item in branch.stages if item.stage_key is StageKey.BUILD]
    assert len(build_stages) == 1
    assert build_stages[0].status is StageStatus.NOT_STARTED
