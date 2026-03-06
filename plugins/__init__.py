"""Plugin contracts and registry."""

from __future__ import annotations

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
from scenarios import build_data_science_v1_bundle


def build_default_registry() -> PluginRegistry:
    """Create registry with built-in minimal plugins."""

    registry = PluginRegistry()
    registry.register("data_science", build_data_science_v1_bundle)
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
