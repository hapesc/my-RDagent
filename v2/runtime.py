from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, cast

from v2.exploration.manager import V2ExplorationManager
from v2.graph.main_loop import build_main_graph
from v2.llm.adapter import V2LLMAdapter
from v2.llm.mock import MockChatModel
from v2.plugins.registry import PluginRegistry
from v2.run_service import V2RunService
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


def build_v2_runtime(config: dict[str, Any]) -> V2RuntimeContext:
    effective_config = dict(config)
    if effective_config.get("llm_provider") == "litellm":
        effective_config = {**effective_config, **REAL_PROVIDER_SAFE_PROFILE}

    graph = build_main_graph()
    llm = V2LLMAdapter(
        model=cast(Any, MockChatModel()),
        max_attempts=int(effective_config.get("max_retries", 3)),
    )
    plugin_registry = PluginRegistry()
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
    )

    return V2RuntimeContext(
        config=effective_config,
        graph=graph,
        llm=llm,
        run_service=run_service,
        exploration_manager=exploration_manager,
        plugin_registry=plugin_registry,
        checkpoint_coordinator=checkpoint_coordinator,
    )


__all__ = ["REAL_PROVIDER_SAFE_PROFILE", "V2RuntimeContext", "build_v2_runtime"]
