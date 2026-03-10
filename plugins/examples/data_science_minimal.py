"""Compatibility wrapper around the formal Synthetic Research bundle."""

from __future__ import annotations

from dataclasses import dataclass

from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider
from plugins.contracts import PluginBundle
from scenarios import SyntheticResearchConfig, build_synthetic_research_bundle


@dataclass
class MinimalDataSciencePluginConfig(SyntheticResearchConfig):
    """Deprecated compatibility alias for the formal synthetic research config."""


def build_minimal_data_science_bundle(
    config: MinimalDataSciencePluginConfig | None = None,
    llm_adapter: LLMAdapter | None = None,
) -> PluginBundle:
    """Build the legacy example bundle via the formal synthetic research implementation."""

    plugin_config = config or MinimalDataSciencePluginConfig()
    adapter = llm_adapter or LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
    return build_synthetic_research_bundle(
        SyntheticResearchConfig(workspace_root=plugin_config.workspace_root),
        llm_adapter=adapter,
    )
