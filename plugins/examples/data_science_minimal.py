"""Compatibility wrapper around the formal Synthetic Research bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from plugins.contracts import PluginBundle
from scenarios import SyntheticResearchConfig, build_synthetic_research_bundle


@dataclass
class MinimalDataSciencePluginConfig(SyntheticResearchConfig):
    """Deprecated compatibility alias for the formal synthetic research config."""


def build_minimal_data_science_bundle(config: Optional[MinimalDataSciencePluginConfig] = None) -> PluginBundle:
    """Build the legacy example bundle via the formal synthetic research implementation."""

    plugin_config = config or MinimalDataSciencePluginConfig()
    return build_synthetic_research_bundle(SyntheticResearchConfig(workspace_root=plugin_config.workspace_root))
