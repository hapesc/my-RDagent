from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, cast

from langchain_openai import ChatOpenAI

from tracing import TracingConfig, load_tracing_config
from v2.exploration.manager import V2ExplorationManager
from v2.graph.main_loop import build_main_graph
from v2.llm.adapter import V2LLMAdapter
from v2.llm.mock import MockChatModel
from v2.plugins.registry import PluginRegistry
from v2.run_service import V2RunService
from v2.scenarios.data_science.plugin import DataScienceBundle
from v2.scenarios.quant.plugin import QuantBundle
from v2.scenarios.synthetic_research.plugin import SyntheticResearchBundle
from v2.storage.checkpoint_coordinator import CheckpointBlobCoordinator

REAL_PROVIDER_SAFE_PROFILE: dict[str, int] = {
    "layer0_n_candidates": 1,
    "layer0_k_forward": 1,
    "costeer_max_rounds": 1,
    "sandbox_timeout_sec": 120,
    "max_retries": 1,
}


@dataclass
class V2RuntimeContext:
    config: dict[str, Any]
    graph: Any
    llm: V2LLMAdapter
    run_service: V2RunService
    exploration_manager: V2ExplorationManager
    plugin_registry: PluginRegistry
    checkpoint_coordinator: CheckpointBlobCoordinator | None = field(default=None)
    tracing_config: TracingConfig | None = field(default=None)
    llm_provider_name: str = "mock"
    llm_model_name: str | None = None
    judge_model_name: str | None = None


def build_v2_runtime(config: dict[str, Any]) -> V2RuntimeContext:
    effective_config = dict(config)
    if effective_config.get("llm_provider") == "litellm":
        effective_config = {**effective_config, **REAL_PROVIDER_SAFE_PROFILE}
    tracing_config = load_tracing_config()

    graph = build_main_graph()
    llm_provider_name = str(effective_config.get("llm_provider", "mock"))
    llm_model_name = str(effective_config.get("llm_model", "gpt-4o-mini"))
    if llm_provider_name == "litellm":
        model = cast(
            Any,
            ChatOpenAI(
                model=llm_model_name,
                api_key=effective_config.get("llm_api_key"),
                base_url=effective_config.get("llm_base_url"),
            ),
        )
    else:
        model = cast(Any, MockChatModel(response="mock response"))
    llm = V2LLMAdapter(
        model=model,
        max_attempts=int(effective_config.get("max_retries", 3)),
    )
    plugin_registry = PluginRegistry()
    plugin_registry.register("data_science", DataScienceBundle())
    plugin_registry.register("quant", QuantBundle())
    plugin_registry.register("synthetic_research", SyntheticResearchBundle())
    exploration_manager = V2ExplorationManager()

    checkpoint_coordinator: CheckpointBlobCoordinator | None = None
    artifact_root = effective_config.get("artifact_root")
    if artifact_root:
        checkpoint_coordinator = CheckpointBlobCoordinator(
            checkpoint_dir=os.path.join(str(artifact_root), "checkpoints"),
            blob_dir=os.path.join(str(artifact_root), "blobs"),
        )

    run_service = V2RunService(
        plugin_registry=plugin_registry,
        checkpoint_coordinator=checkpoint_coordinator,
        runtime_metadata={
            "llm_provider": llm_provider_name,
            "llm_model": llm_model_name,
            "judge_model": effective_config.get("judge_model"),
        },
    )

    return V2RuntimeContext(
        config=effective_config,
        graph=graph,
        llm=llm,
        run_service=run_service,
        exploration_manager=exploration_manager,
        plugin_registry=plugin_registry,
        checkpoint_coordinator=checkpoint_coordinator,
        tracing_config=tracing_config,
        llm_provider_name=llm_provider_name,
        llm_model_name=llm_model_name,
        judge_model_name=effective_config.get("judge_model"),
    )


__all__ = ["REAL_PROVIDER_SAFE_PROFILE", "V2RuntimeContext", "build_v2_runtime"]
