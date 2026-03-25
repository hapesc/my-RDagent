from __future__ import annotations

import inspect
import math

import pytest

from rd_agent.algorithms.interaction_kernel import (
    compute_interaction_potential,
    dynamic_sample_count,
    sample_branches,
    softmax_weights,
)
from rd_agent.contracts import exploration as exploration_module
from rd_agent.contracts.exploration import ComponentClass, NodeMetrics
from rd_agent.ports.embedding_port import EmbeddingPort, StubEmbeddingPort
from rd_agent.ports.state_store import StateStorePort


def test_component_class_members_and_exports() -> None:
    expected = {
        "data_load",
        "feature_eng",
        "model",
        "ensemble",
        "workflow",
    }

    assert {member.value for member in ComponentClass} == expected
    assert "ComponentClass" in exploration_module.__all__


def test_node_metrics_remains_backward_compatible() -> None:
    metrics = NodeMetrics(
        validation_score=0.7,
        generalization_gap=0.2,
        overfitting_risk=0.1,
        diversity_score=1.2,
    )

    assert metrics.validation_score == 0.7
    assert metrics.generalization_gap == 0.2
    assert metrics.overfitting_risk == 0.1
    assert metrics.diversity_score == 1.2
    assert metrics.complementarity_score == 0.0


def test_node_metrics_accepts_explicit_complementarity_score() -> None:
    metrics = NodeMetrics(complementarity_score=0.5)

    assert metrics.complementarity_score == 0.5


def test_embedding_port_signature_and_stub_vectors() -> None:
    signature = inspect.signature(EmbeddingPort.embed)
    annotations = EmbeddingPort.embed.__annotations__

    assert list(signature.parameters) == ["self", "texts"]
    assert annotations["texts"] == "list[str]"
    assert annotations["return"] == "list[list[float]]"

    stub = StubEmbeddingPort()
    assert stub.embed(["a", "b"]) == [[0.0] * 256, [0.0] * 256]


def test_state_store_port_exposes_load_hypothesis_spec() -> None:
    signature = inspect.signature(StateStorePort.load_hypothesis_spec)
    annotations = StateStorePort.load_hypothesis_spec.__annotations__

    assert list(signature.parameters) == ["self", "branch_id"]
    assert annotations["branch_id"] == "str"
    assert annotations["return"] == "HypothesisSpec | None"


def test_compute_interaction_potential_uses_default_weights() -> None:
    actual = compute_interaction_potential(similarity=0.8, score_delta=0.5, depth=2)
    expected = 0.5 * 0.8 * math.exp(-0.1 * 2) + 0.3 * math.tanh(0.5)

    assert actual == pytest.approx(expected)


def test_compute_interaction_potential_accepts_custom_weights() -> None:
    actual = compute_interaction_potential(
        similarity=0.8,
        score_delta=0.5,
        depth=2,
        alpha=1.0,
        beta=0.0,
        gamma=0.0,
    )

    assert actual == pytest.approx(0.8)


def test_softmax_weights_handles_empty_equal_large_and_single_inputs() -> None:
    assert softmax_weights([]) == []
    assert softmax_weights([1.0, 1.0]) == pytest.approx([0.5, 0.5])
    assert softmax_weights([100.0, 0.0]) == pytest.approx([1.0, 0.0])
    assert softmax_weights([0.0]) == [1.0]


def test_sample_branches_deduplicates_preserving_order(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    def fake_choices(
        population: list[str],
        *,
        weights: list[float] | None = None,
        k: int,
    ) -> list[str]:
        observed["population"] = population
        observed["weights"] = weights
        observed["k"] = k
        return ["a", "a"]

    monkeypatch.setattr("rd_agent.algorithms.interaction_kernel.random.choices", fake_choices)

    assert sample_branches([0.9, 0.1], ["a", "b"], k=2) == ["a"]
    assert observed["population"] == ["a", "b"]
    assert observed["k"] == 2
    assert observed["weights"] == pytest.approx(softmax_weights([0.9, 0.1]))


@pytest.mark.parametrize(
    ("budget_ratio", "expected"),
    [
        (0.1, 3),
        (0.5, 1),
        (0.9, 2),
    ],
)
def test_dynamic_sample_count_follows_budget_stage(budget_ratio: float, expected: int) -> None:
    assert dynamic_sample_count(budget_ratio) == expected
