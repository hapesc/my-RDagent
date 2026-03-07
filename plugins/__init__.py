"""Plugin contracts and registry."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from service_contracts import ScenarioManifest

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
from .registry import PluginRegistry
from scenarios import (
    DataScienceV1Config,
    SyntheticResearchConfig,
    build_data_science_v1_bundle,
    build_synthetic_research_bundle,
)

if TYPE_CHECKING:
    from llm import LLMAdapter


def _data_science_manifest(config: Optional[DataScienceV1Config] = None) -> ScenarioManifest:
    plugin_config = config or DataScienceV1Config()
    return ScenarioManifest(
        scenario_name="data_science",
        title="Data Science",
        description="Generate, execute, and evaluate small data-science experiments against a dataset.",
        tags=["built-in", "python", "dataset"],
        supports_branching=True,
        supports_resume=True,
        supports_local_execution=plugin_config.allow_local_execution,
        default_step_overrides=plugin_config.default_step_overrides,
    )


def _synthetic_research_manifest(config: Optional[SyntheticResearchConfig] = None) -> ScenarioManifest:
    plugin_config = config or SyntheticResearchConfig()
    return ScenarioManifest(
        scenario_name="synthetic_research",
        title="Synthetic Research",
        description="Generate a lightweight synthetic research brief and findings package through the shared loop engine.",
        tags=["built-in", "research", "synthetic"],
        supports_branching=True,
        supports_resume=True,
        supports_local_execution=True,
        default_step_overrides=plugin_config.default_step_overrides,
    )


def build_default_registry(
    data_science_config: Optional[DataScienceV1Config] = None,
    synthetic_research_config: Optional[SyntheticResearchConfig] = None,
    llm_adapter: Optional["LLMAdapter"] = None,
) -> PluginRegistry:
    """Create registry with built-in minimal plugins."""

    registry = PluginRegistry()
    registry.register(
        "data_science",
        lambda: build_data_science_v1_bundle(data_science_config, llm_adapter=llm_adapter),
        manifest=_data_science_manifest(data_science_config),
    )
    registry.register(
        "synthetic_research",
        lambda: build_synthetic_research_bundle(synthetic_research_config, llm_adapter=llm_adapter),
        manifest=_synthetic_research_manifest(synthetic_research_config),
    )
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
