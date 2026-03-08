"""Runtime assembly for CLI and app entrypoints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import LoopEngine, LoopEngineConfig, ResumeManager, RunService, RunServiceConfig, StepExecutor
from core.reasoning.pipeline import ReasoningPipeline
from core.reasoning.virtual_eval import VirtualEvaluator
from core.storage import (
    BranchTraceStore,
    BranchTraceStoreConfig,
    CheckpointStoreConfig,
    FileCheckpointStore,
    SQLiteMetadataStore,
    SQLiteStoreConfig,
)
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from exploration_manager.merging import TraceMerger
from exploration_manager.pruning import BranchPruner
from exploration_manager.reward import RewardCalculator
from exploration_manager.scheduler import MCTSScheduler
from llm import LLMAdapter, MockLLMProvider
from llm.providers.litellm_provider import LiteLLMProvider
from memory_service import MemoryService, MemoryServiceConfig
from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.interaction_kernel import InteractionKernel
from planner import Planner, PlannerConfig
from plugins import PluginRegistry, build_default_registry
from scenarios import (
    DataScienceV1Config,
    SyntheticResearchConfig,
    default_data_science_step_overrides,
    default_synthetic_research_step_overrides,
)

from .config import AppConfig, load_config


@dataclass
class RuntimeContext:
    """Shared runtime context used by CLI commands."""

    config: AppConfig
    sqlite_store: SQLiteMetadataStore
    branch_store: BranchTraceStore
    checkpoint_store: FileCheckpointStore
    workspace_manager: WorkspaceManager
    planner: Planner
    exploration_manager: ExplorationManager
    memory_service: MemoryService
    evaluation_service: EvaluationService
    plugin_registry: PluginRegistry
    llm_adapter: LLMAdapter
    scheduler: MCTSScheduler
    reasoning_pipeline: Optional[ReasoningPipeline] = None
    virtual_evaluator: Optional[VirtualEvaluator] = None


class _ReasoningTraceStore:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    def store(self, trace_record) -> None:
        payload = {
            "trace_id": trace_record.trace_id,
            "stages": trace_record.stages,
            "timestamp": trace_record.timestamp,
            "metadata": trace_record.metadata,
        }
        metadata = {
            "kind": "reasoning_trace",
            "trace_id": str(trace_record.trace_id),
            "scenario": str(trace_record.metadata.get("scenario", "")),
            "iteration": str(trace_record.metadata.get("iteration", "")),
        }
        self._memory_service.write_memory(json.dumps(payload, sort_keys=True), metadata)


def _create_llm_provider(config: AppConfig):
    if config.llm_provider == "litellm":
        return LiteLLMProvider(
            api_key=config.llm_api_key or "",
            model=config.llm_model,
            base_url=config.llm_base_url,
        )
    return MockLLMProvider()


def _create_memory_service(config: AppConfig, llm_adapter: LLMAdapter) -> MemoryService:
    mem_config = MemoryServiceConfig(
        enable_hypothesis_storage=config.enable_hypothesis_storage,
    )
    if config.enable_hypothesis_storage:
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel, llm_adapter=llm_adapter)
        return MemoryService(mem_config, hypothesis_selector=selector, interaction_kernel=kernel)
    return MemoryService(mem_config)


def build_runtime() -> RuntimeContext:
    config = load_config()
    llm_provider = _create_llm_provider(config)
    llm_adapter = LLMAdapter(llm_provider)
    scheduler = MCTSScheduler(
        c_puct=config.mcts_c_puct,
        reward_calculator=RewardCalculator(mode=config.mcts_reward_mode),
    )
    pruner = BranchPruner(relative_threshold=config.prune_threshold)
    merger = TraceMerger(llm_adapter)
    sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=config.sqlite_path))
    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=config.sqlite_path))
    checkpoint_store = FileCheckpointStore(
        CheckpointStoreConfig(root_dir=f"{config.artifact_root}/checkpoints")
    )
    workspace_manager = WorkspaceManager(
        WorkspaceManagerConfig(root_dir=config.workspace_root),
        checkpoint_store=checkpoint_store,
    )
    memory_service = _create_memory_service(config, llm_adapter)
    reasoning_pipeline = ReasoningPipeline(
        llm_adapter,
        trace_store=_ReasoningTraceStore(memory_service),
    )
    virtual_evaluator = VirtualEvaluator(
        llm_adapter,
        n_candidates=config.layer0_n_candidates,
        k_forward=config.layer0_k_forward,
        reasoning_pipeline=reasoning_pipeline,
    )
    return RuntimeContext(
        config=config,
        sqlite_store=sqlite_store,
        branch_store=branch_store,
        checkpoint_store=checkpoint_store,
        workspace_manager=workspace_manager,
        planner=Planner(
            PlannerConfig(use_llm_planning=config.use_llm_planning),
            llm_adapter=llm_adapter if config.use_llm_planning else None,
        ),
        exploration_manager=ExplorationManager(
            ExplorationManagerConfig(),
            scheduler=scheduler,
            pruner=pruner,
            merger=merger,
            llm_adapter=llm_adapter,
            virtual_evaluator=virtual_evaluator,
        ),
        memory_service=memory_service,
        evaluation_service=EvaluationService(EvaluationServiceConfig()),
        plugin_registry=build_default_registry(
            DataScienceV1Config(
                workspace_root=config.workspace_root,
                trace_storage_path=config.trace_storage_path,
                allow_local_execution=config.allow_local_execution,
                default_step_overrides=default_data_science_step_overrides(config.sandbox_timeout_sec),
            ),
            SyntheticResearchConfig(
                workspace_root=config.workspace_root,
                default_step_overrides=default_synthetic_research_step_overrides(
                    config.sandbox_timeout_sec
                ),
            ),
            llm_adapter=llm_adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        llm_adapter=llm_adapter,
        scheduler=scheduler,
        reasoning_pipeline=reasoning_pipeline,
        virtual_evaluator=virtual_evaluator,
    )


def build_run_service(runtime: RuntimeContext, scenario: str) -> RunService:
    plugin_bundle = runtime.plugin_registry.create_bundle(scenario)
    step_executor = StepExecutor(
        plugin_bundle=plugin_bundle,
        evaluation_service=runtime.evaluation_service,
        workspace_manager=runtime.workspace_manager,
        event_store=runtime.sqlite_store,
        branch_store=runtime.branch_store,
        costeer_max_rounds=runtime.config.costeer_max_rounds,
        llm_adapter=runtime.llm_adapter,
        memory_service=runtime.memory_service,
    )
    loop_engine = LoopEngine(
        config=LoopEngineConfig(exception_archive_root=runtime.config.artifact_root),
        planner=runtime.planner,
        exploration_manager=runtime.exploration_manager,
        memory_service=runtime.memory_service,
        step_executor=step_executor,
        run_store=runtime.sqlite_store,
        event_store=runtime.sqlite_store,
        scheduler=runtime.scheduler,
    )
    resume_manager = ResumeManager(
        checkpoint_store=runtime.checkpoint_store,
        workspace_manager=runtime.workspace_manager,
    )
    return RunService(
        config=RunServiceConfig(default_scenario=scenario),
        loop_engine=loop_engine,
        run_store=runtime.sqlite_store,
        resume_manager=resume_manager,
        branch_store=runtime.branch_store,
    )
