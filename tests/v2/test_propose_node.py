from __future__ import annotations

from v2.graph.nodes import experiment_setup_node, propose_node


class _MockProposerPlugin:
    def propose(self, state: dict) -> dict:
        assert state["run_id"] == "test-run"
        return {"hypothesis": "test"}


class _FailingProposerPlugin:
    def propose(self, state: dict) -> dict:
        _ = state
        raise RuntimeError("plugin boom")


def test_propose_node_generates_proposal_and_updates_step_state() -> None:
    result = propose_node(
        {
            "run_id": "test-run",
            "step_state": "PROPOSING",
        },
        proposer_plugin=_MockProposerPlugin(),
    )

    assert result["proposal"] == {"hypothesis": "test"}
    assert result["step_state"] == "EXPERIMENT_READY"
    assert result["error"] is None
    assert "tokens_used" in result
    assert isinstance(result["tokens_used"], int)
    assert result["tokens_used"] > 0


def test_propose_node_returns_error_when_plugin_fails() -> None:
    result = propose_node(
        {
            "run_id": "test-run",
            "step_state": "PROPOSING",
        },
        proposer_plugin=_FailingProposerPlugin(),
    )

    assert result["error"] == "plugin boom"
    assert result["tokens_used"] == 0


def test_propose_node_uses_default_mock_when_no_plugin() -> None:
    result = propose_node(
        {
            "run_id": "test-run",
            "step_state": "PROPOSING",
        },
    )

    assert result["proposal"] is not None
    assert result["step_state"] == "EXPERIMENT_READY"
    assert result["error"] is None
    assert "tokens_used" in result
    assert isinstance(result["tokens_used"], int)
    assert result["tokens_used"] > 0


def test_propose_node_returns_tokens_used_estimate() -> None:
    state = {"run_id": "test-run", "loop_iteration": 0, "max_loops": 1, "step_state": "PROPOSING"}
    result = propose_node(state, proposer_plugin=_MockProposerPlugin())
    assert "tokens_used" in result
    assert isinstance(result["tokens_used"], int)
    assert result["tokens_used"] > 0


def test_experiment_setup_node_converts_proposal_to_experiment_and_updates_step_state() -> None:
    result = experiment_setup_node(
        {
            "proposal": {"hypothesis": "test", "constraints": {"budget": "low"}},
            "step_state": "EXPERIMENT_READY",
        }
    )

    assert result == {
        "experiment": {"proposal": {"hypothesis": "test", "constraints": {"budget": "low"}}},
        "step_state": "CODING",
        "error": None,
        "tokens_used": 0,
    }
