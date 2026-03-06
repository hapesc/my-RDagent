"""Synthetic Research scenario plugin bundle."""

from .plugin import (
    SyntheticResearchConfig,
    build_synthetic_research_bundle,
    default_synthetic_research_step_overrides,
)

__all__ = [
    "SyntheticResearchConfig",
    "build_synthetic_research_bundle",
    "default_synthetic_research_step_overrides",
]
