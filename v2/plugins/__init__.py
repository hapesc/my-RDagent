"""Plugin system for scenarios and extensibility."""

from v2.plugins.contracts import (
    CoderPlugin,
    EvaluatorPlugin,
    ProposerPlugin,
    RunnerPlugin,
    ScenarioBundle,
)
from v2.plugins.registry import PluginRegistry

__all__ = [
    "ProposerPlugin",
    "CoderPlugin",
    "RunnerPlugin",
    "EvaluatorPlugin",
    "ScenarioBundle",
    "PluginRegistry",
]
