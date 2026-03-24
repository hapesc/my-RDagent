"""RED phase tests for Task 1: Verify rd_agent wiring before implementation."""

from __future__ import annotations

import pytest

from v3.contracts.exploration import ApproachCategory, HypothesisSpec
from v3.contracts.run import ExecutionMode
from v3.contracts.stage import StageKey
from v3.orchestration.artifact_state_store import ArtifactStateStore
from v3.orchestration.recovery_service import RecoveryService
from v3.orchestration.run_board_service import RunBoardService
from v3.orchestration.stage_transition_service import StageTransitionService
from v3.ports.holdout_port import StubEvaluationPort, StubHoldoutSplitPort


def _make_execution_port():
    """Reuse Phase 16 deterministic execution port."""
    from tests.test_phase16_rd_agent import _DeterministicExecutionPort

    return _DeterministicExecutionPort()


def _base_kwargs(tmp_path, *, hypothesis_specs=None, branch_hypotheses=None):
    state_store = ArtifactStateStore(tmp_path / "state")
    run_service = RunBoardService(state_store=state_store, execution_port=_make_execution_port())
    kwargs = {
        "title": "Phase 29 test",
        "task_summary": "Test entry wiring.",
        "scenario_label": "research",
        "initial_branch_label": "primary",
        "dispatcher": lambda payload: payload,
        "execution_mode": ExecutionMode.UNATTENDED,
        "max_stage_iterations": 1,
        "stage_inputs": {
            StageKey.FRAMING: {"summary": "Framing.", "artifact_ids": ["a1"]},
            StageKey.BUILD: {"summary": "Build.", "artifact_ids": ["a2"]},
            StageKey.VERIFY: {"summary": "Verify.", "artifact_ids": ["a3"]},
            StageKey.SYNTHESIZE: {"summary": "Synth.", "artifact_ids": ["a4"], "recommendation": "stop"},
        },
        "state_store": state_store,
        "run_service": run_service,
        "recovery_service": RecoveryService(state_store),
        "transition_service": StageTransitionService(state_store),
    }
    if hypothesis_specs is not None:
        kwargs["hypothesis_specs"] = hypothesis_specs
        kwargs["holdout_evaluation_port"] = StubEvaluationPort()
        kwargs["holdout_split_port"] = StubHoldoutSplitPort()
    if branch_hypotheses is not None:
        kwargs["branch_hypotheses"] = branch_hypotheses
    return kwargs


def _hypothesis_specs():
    return [
        HypothesisSpec(
            label="primary",
            approach_category=ApproachCategory.FEATURE_ENGINEERING,
            target_challenge="test",
            rationale="primary hypothesis",
        ),
        HypothesisSpec(
            label="alt-a",
            approach_category=ApproachCategory.MODEL_ARCHITECTURE,
            target_challenge="test",
            rationale="alt-a hypothesis",
        ),
    ]


def test_rd_agent_accepts_holdout_evaluation_port_param(tmp_path):
    """rd_agent() must accept holdout_evaluation_port keyword."""
    from v3.entry.rd_agent import rd_agent

    kwargs = _base_kwargs(tmp_path, hypothesis_specs=_hypothesis_specs())
    result = rd_agent(**kwargs)
    assert "structuredContent" in result


def test_rd_agent_accepts_memory_store_param(tmp_path):
    """rd_agent() must accept memory_store keyword."""
    from v3.entry.rd_agent import rd_agent

    from v3.orchestration.memory_state_store import MemoryStateStore

    kwargs = _base_kwargs(tmp_path, hypothesis_specs=_hypothesis_specs())
    kwargs["memory_store"] = MemoryStateStore(tmp_path / "memory")
    result = rd_agent(**kwargs)
    assert "structuredContent" in result


def test_rd_agent_response_contains_finalization_keys(tmp_path):
    """Multi-branch response must include finalization_guidance and finalization_submission keys."""
    from v3.entry.rd_agent import rd_agent

    kwargs = _base_kwargs(tmp_path, hypothesis_specs=_hypothesis_specs())
    result = rd_agent(**kwargs)
    assert "finalization_guidance" in result["structuredContent"]
    assert "finalization_submission" in result["structuredContent"]


def test_rd_agent_raises_without_evaluation_port(tmp_path):
    """rd_agent must raise ValueError when hypothesis_specs provided without holdout_evaluation_port."""
    from v3.entry.rd_agent import rd_agent

    kwargs = _base_kwargs(tmp_path, hypothesis_specs=_hypothesis_specs())
    # Remove the evaluation port to trigger the guard
    kwargs.pop("holdout_evaluation_port", None)
    with pytest.raises(ValueError, match="holdout_evaluation_port"):
        rd_agent(**kwargs)
