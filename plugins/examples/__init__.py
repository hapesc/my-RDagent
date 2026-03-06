"""Example plugin bundles."""

from .data_science_minimal import (
    MinimalDataSciencePluginConfig,
    build_minimal_data_science_bundle,
)

__all__ = ["MinimalDataSciencePluginConfig", "build_minimal_data_science_bundle"]
