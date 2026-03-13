from __future__ import annotations

import time

from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.interaction_kernel import HypothesisRecord, InteractionKernel
from memory_service.service import MemoryService, MemoryServiceConfig


def test_default_config_enables_hypothesis_storage():
    config = MemoryServiceConfig()
    assert config.enable_hypothesis_storage is True


def test_default_config_max_context_items_unchanged():
    config = MemoryServiceConfig()
    assert config.max_context_items == 10


def test_memory_service_with_default_config_has_kernel_and_selector():
    config = MemoryServiceConfig()
    kernel = InteractionKernel()
    selector = HypothesisSelector(kernel, llm_adapter=None)
    service = MemoryService(config, hypothesis_selector=selector, interaction_kernel=kernel)
    service.write_hypothesis(text="test hypothesis", score=0.8, branch_id="main")
    results = service.query_hypotheses(branch_id="main")
    assert len(results) == 1
    assert results[0].text == "test hypothesis"


def test_selector_degrades_gracefully_without_llm():
    kernel = InteractionKernel()
    selector = HypothesisSelector(kernel, llm_adapter=None)
    candidates = [
        HypothesisRecord(text="a", score=0.9, timestamp=time.time(), branch_id="b1"),
        HypothesisRecord(text="b", score=0.5, timestamp=time.time(), branch_id="b2"),
    ]
    best = selector.select_hypothesis(candidates, "")
    assert best is not None
    assert best.score == 0.9
