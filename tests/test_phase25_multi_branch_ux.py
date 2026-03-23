from __future__ import annotations

from v3.contracts.exploration import ExplorationMode
from v3.contracts.tool_io import RunStartRequest
from v3.entry.tool_catalog import get_cli_tool
from v3.orchestration.operator_guidance import (
    _generate_branch_hypotheses,
    build_start_new_run_guidance,
)


def test_run_start_request_accepts_exploration_fields() -> None:
    request = RunStartRequest(
        title="t",
        task_summary="s",
        scenario_label="r",
        exploration_mode=ExplorationMode.EXPLORATION,
        branch_hypotheses=["h1", "h2"],
    )

    assert request.exploration_mode is ExplorationMode.EXPLORATION
    assert request.branch_hypotheses == ["h1", "h2"]


def test_run_start_request_defaults() -> None:
    request = RunStartRequest(title="t", task_summary="s", scenario_label="r")

    assert request.exploration_mode is ExplorationMode.EXPLORATION
    assert request.branch_hypotheses is None


def test_start_new_run_guidance_includes_hypotheses() -> None:
    guidance = build_start_new_run_guidance(user_intent="Build an image classifier for aerial cactus identification")

    assert "I suggest exploring these directions" in guidance.routing_reason
    assert "Approach A:" in guidance.routing_reason
    assert "Approach B:" in guidance.routing_reason
    assert "Approach C:" in guidance.routing_reason
    assert 'exploration_mode="exploration"' in guidance.next_step_detail
    assert "branch_hypotheses=" in guidance.next_step_detail
    assert "exploration mode" in guidance.exact_next_action
    assert "Multi-branch exploration is recommended" in guidance.current_state


def test_generate_branch_hypotheses() -> None:
    hypotheses = _generate_branch_hypotheses("Build an image classifier for aerial cactus identification")

    assert len(hypotheses) == 3
    assert all("Approach" in hypothesis for hypothesis in hypotheses)

    long_intent = ("A" * 50) + ("B" * 50)
    truncated = long_intent[:50]
    long_hypotheses = _generate_branch_hypotheses(long_intent)
    assert len(long_hypotheses) == 3
    assert all(truncated in hypothesis for hypothesis in long_hypotheses)
    assert all(long_intent[50:] not in hypothesis for hypothesis in long_hypotheses)


def test_tool_catalog_rd_run_start_shows_exploration() -> None:
    payload = get_cli_tool("rd_run_start")
    example = payload["examples"][0]["arguments"]

    assert example["exploration_mode"] == "exploration"
    assert len(example["branch_hypotheses"]) == 3
