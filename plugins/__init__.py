"""Plugin contracts and registry."""

from __future__ import annotations

from typing import Optional

from .contracts import (
    Coder,
    ExperimentGenerator,
    FeedbackAnalyzer,
    PluginBundle,
    ProposalEngine,
    Runner,
    ScenarioContext,
    ScenarioPlugin,
)
from .examples import build_minimal_data_science_bundle
from .registry import PluginRegistry
from scenarios import DataScienceV1Config, build_data_science_v1_bundle


def build_default_registry(data_science_config: Optional[DataScienceV1Config] = None) -> PluginRegistry:
    """Create registry with built-in minimal plugins."""

    registry = PluginRegistry()
    registry.register(
        "data_science",
        lambda: build_data_science_v1_bundle(data_science_config),
    )
    registry.register("data_science_minimal", build_minimal_data_science_bundle)
    return registry


__all__ = [
    "Coder",
    "ExperimentGenerator",
    "FeedbackAnalyzer",
    "PluginBundle",
    "PluginRegistry",
    "ProposalEngine",
    "Runner",
    "ScenarioContext",
    "ScenarioPlugin",
    "build_default_registry",
]
