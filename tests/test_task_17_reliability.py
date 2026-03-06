"""Task-17 reliability acceptance test."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import LoopEngine, LoopEngineConfig, StepExecutor
from core.storage import CheckpointStoreConfig, FileCheckpointStore, SQLiteMetadataStore, SQLiteStoreConfig
from data_models import RunSession, RunStatus, StopConditions
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from scenarios.data_science import DataScienceV1Config, build_data_science_v1_bundle


class ReliabilityAcceptanceTests(unittest.TestCase):
    def test_multiple_runs_complete_without_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(tmp_path / "meta.db")))
            checkpoint_store = FileCheckpointStore(
                CheckpointStoreConfig(root_dir=str(tmp_path / "checkpoints"))
            )
            workspace_manager = WorkspaceManager(
                WorkspaceManagerConfig(root_dir=str(tmp_path / "workspaces")),
                checkpoint_store=checkpoint_store,
            )
            planner = Planner(PlannerConfig())
            exploration_manager = ExplorationManager(ExplorationManagerConfig())
            memory_service = MemoryService(MemoryServiceConfig())
            evaluation_service = EvaluationService(EvaluationServiceConfig())
            plugin_bundle = build_data_science_v1_bundle(
                DataScienceV1Config(
                    workspace_root=str(tmp_path / "plugin_workspace"),
                    trace_storage_path=str(tmp_path / "trace.jsonl"),
                    prefer_docker=False,
                )
            )
            step_executor = StepExecutor(plugin_bundle, evaluation_service, workspace_manager, sqlite_store)
            loop_engine = LoopEngine(
                config=LoopEngineConfig(exception_archive_root=str(tmp_path / "artifacts")),
                planner=planner,
                exploration_manager=exploration_manager,
                memory_service=memory_service,
                step_executor=step_executor,
                run_store=sqlite_store,
                event_store=sqlite_store,
            )

            for idx in range(3):
                run_id = f"run-rel-{idx}"
                run_session = RunSession(
                    run_id=run_id,
                    scenario="data_science",
                    status=RunStatus.CREATED,
                    stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                    entry_input={"task_id": f"task-{idx}"},
                )
                context = loop_engine.run(run_session=run_session, task_summary="reliability", max_loops=1)
                self.assertEqual(context.loop_state.status, RunStatus.COMPLETED)

            persisted_runs = sqlite_store.list_runs()
            statuses = {run.run_id: run.status for run in persisted_runs}
            for idx in range(3):
                self.assertEqual(statuses[f"run-rel-{idx}"], RunStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
