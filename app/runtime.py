"""Runtime assembly for CLI and app entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import LoopEngine, LoopEngineConfig, ResumeManager, RunService, RunServiceConfig, StepExecutor
from core.storage import CheckpointStoreConfig, FileCheckpointStore, SQLiteMetadataStore, SQLiteStoreConfig
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from plugins import build_default_registry

from .config import AppConfig, load_config


@dataclass
class RuntimeContext:
    """Shared runtime context used by CLI commands."""

    config: AppConfig
    sqlite_store: SQLiteMetadataStore
    checkpoint_store: FileCheckpointStore
    workspace_manager: WorkspaceManager
    planner: Planner
    exploration_manager: ExplorationManager
    memory_service: MemoryService
    evaluation_service: EvaluationService
    plugin_registry: object


def build_runtime() -> RuntimeContext:
    config = load_config()
    sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=config.sqlite_path))
    checkpoint_store = FileCheckpointStore(
        CheckpointStoreConfig(root_dir=f"{config.artifact_root}/checkpoints")
    )
    workspace_manager = WorkspaceManager(
        WorkspaceManagerConfig(root_dir=config.workspace_root),
        checkpoint_store=checkpoint_store,
    )
    return RuntimeContext(
        config=config,
        sqlite_store=sqlite_store,
        checkpoint_store=checkpoint_store,
        workspace_manager=workspace_manager,
        planner=Planner(PlannerConfig()),
        exploration_manager=ExplorationManager(ExplorationManagerConfig()),
        memory_service=MemoryService(MemoryServiceConfig()),
        evaluation_service=EvaluationService(EvaluationServiceConfig()),
        plugin_registry=build_default_registry(),
    )


def build_run_service(runtime: RuntimeContext, scenario: str) -> RunService:
    plugin_bundle = runtime.plugin_registry.create_bundle(scenario)
    step_executor = StepExecutor(
        plugin_bundle=plugin_bundle,
        evaluation_service=runtime.evaluation_service,
        workspace_manager=runtime.workspace_manager,
        event_store=runtime.sqlite_store,
    )
    loop_engine = LoopEngine(
        config=LoopEngineConfig(exception_archive_root=runtime.config.artifact_root),
        planner=runtime.planner,
        exploration_manager=runtime.exploration_manager,
        memory_service=runtime.memory_service,
        step_executor=step_executor,
        run_store=runtime.sqlite_store,
        event_store=runtime.sqlite_store,
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
    )
