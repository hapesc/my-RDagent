from __future__ import annotations

from memory_service.interaction_kernel import InteractionKernel
from memory_service.service import MemoryServiceConfig


def test_default_config_has_no_kernel_weights():
    config = MemoryServiceConfig()
    assert config.kernel_weights is None


def test_kernel_weights_applied_to_kernel():
    weights = {"alpha": 0.5, "beta": 0.2, "gamma": 0.3}
    kernel = InteractionKernel(**weights)
    assert kernel._alpha == 0.5
    assert kernel._beta == 0.2
    assert kernel._gamma == 0.3


def test_quant_weights_emphasize_score():
    quant_weights = {"alpha": 0.3, "beta": 0.5, "gamma": 0.2}
    kernel = InteractionKernel(**quant_weights)
    assert kernel._beta > kernel._alpha


def test_default_kernel_weights_are_balanced():
    kernel = InteractionKernel()
    assert kernel._alpha == 0.4
    assert kernel._beta == 0.3
    assert kernel._gamma == 0.3


def test_config_kernel_weights_round_trip():
    weights = {"alpha": 0.6, "beta": 0.1, "gamma": 0.3}
    config = MemoryServiceConfig(kernel_weights=weights)
    kernel = InteractionKernel(**(config.kernel_weights or {}))
    assert kernel._alpha == 0.6
    assert kernel._beta == 0.1
    assert kernel._gamma == 0.3
