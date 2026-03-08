"""Plugin contracts and registry."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Optional, TYPE_CHECKING

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

if TYPE_CHECKING:
    from core.reasoning.pipeline import ReasoningPipeline
    from core.reasoning.virtual_eval import VirtualEvaluator
    from llm import LLMAdapter


def _load_scenarios_module() -> Any:
    return import_module("scenarios")


def _data_science_manifest(config: Optional[Any] = None) -> ScenarioManifest:
    scenarios_module = _load_scenarios_module()
    plugin_config = config or scenarios_module.DataScienceV1Config()
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


def _synthetic_research_manifest(config: Optional[Any] = None) -> ScenarioManifest:
    scenarios_module = _load_scenarios_module()
    plugin_config = config or scenarios_module.SyntheticResearchConfig()
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
    data_science_config: Optional[Any] = None,
    synthetic_research_config: Optional[Any] = None,
    llm_adapter: Optional["LLMAdapter"] = None,
    reasoning_pipeline: Optional["ReasoningPipeline"] = None,
    virtual_evaluator: Optional["VirtualEvaluator"] = None,
) -> PluginRegistry:
    """Create registry with built-in minimal plugins."""

    scenarios_module = _load_scenarios_module()

    registry = PluginRegistry()
    registry.register(
        "data_science",
        lambda: scenarios_module.build_data_science_v1_bundle(
            data_science_config,
            llm_adapter=llm_adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        manifest=_data_science_manifest(data_science_config),
    )
    registry.register(
        "synthetic_research",
        lambda: scenarios_module.build_synthetic_research_bundle(
            synthetic_research_config,
            llm_adapter=llm_adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
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
