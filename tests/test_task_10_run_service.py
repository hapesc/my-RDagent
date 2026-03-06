"""Task-10 tests for run lifecycle control and resume manager."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import (
    LoopEngine,
    LoopEngineConfig,
    ResumeManager,
    RunService,
    RunServiceConfig,
    StepExecutor,
)
from core.storage import CheckpointStoreConfig, FileCheckpointStore, SQLiteMetadataStore, SQLiteStoreConfig
from data_models import RunStatus, StopConditions
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from plugins.examples import build_minimal_data_science_bundle


class RunServiceTests(unittest.TestCase):
    def _build_runtime(self, tmpdir: str):
        sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(Path(tmpdir) / "meta.db")))
        checkpoint_store = FileCheckpointStore(
            CheckpointStoreConfig(root_dir=str(Path(tmpdir) / "checkpoints"))
        )
        workspace_manager = WorkspaceManager(
            WorkspaceManagerConfig(root_dir=str(Path(tmpdir) / "workspaces")),
            checkpoint_store=checkpoint_store,
        )
        planner = Planner(PlannerConfig())
        exploration_manager = ExplorationManager(ExplorationManagerConfig())
        memory_service = MemoryService(MemoryServiceConfig())
        evaluation_service = EvaluationService(EvaluationServiceConfig())
        bundle = build_minimal_data_science_bundle()
        step_executor = StepExecutor(bundle, evaluation_service, workspace_manager, sqlite_store)
        loop_engine = LoopEngine(
            config=LoopEngineConfig(exception_archive_root=str(Path(tmpdir) / "artifacts")),
            planner=planner,
            exploration_manager=exploration_manager,
            memory_service=memory_service,
            step_executor=step_executor,
            run_store=sqlite_store,
            event_store=sqlite_store,
        )
        resume_manager = ResumeManager(checkpoint_store=checkpoint_store, workspace_manager=workspace_manager)
        run_service = RunService(
            config=RunServiceConfig(default_scenario="data_science"),
            loop_engine=loop_engine,
            run_store=sqlite_store,
            resume_manager=resume_manager,
        )
        return run_service, sqlite_store, checkpoint_store

    def test_pause_resume_stop_with_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, sqlite_store, checkpoint_store = self._build_runtime(tmpdir)
            run = run_service.create_run(
                task_summary="resume test",
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
                run_id="run-task-10",
            )

            context1 = run_service.start_run(run.run_id, task_summary="resume test", loops_per_call=1)
            self.assertEqual(context1.loop_state.iteration, 1)
            self.assertEqual(sqlite_store.get_run(run.run_id).status, RunStatus.RUNNING)
            self.assertGreaterEqual(len(checkpoint_store.list_checkpoints(run.run_id)), 6)

            paused = run_service.pause_run(run.run_id)
            self.assertEqual(paused.status, RunStatus.PAUSED)

            restarted_service, restarted_store, _ = self._build_runtime(tmpdir)
            context2 = restarted_service.resume_run(run.run_id, task_summary="resume test", loops_per_call=1)
            self.assertEqual(context2.loop_state.iteration, 2)
            self.assertEqual(restarted_store.get_run(run.run_id).status, RunStatus.COMPLETED)

            stopped = restarted_service.stop_run(run.run_id)
            self.assertEqual(stopped.status, RunStatus.STOPPED)

    def test_invalid_pause_transition_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, _, _ = self._build_runtime(tmpdir)
            run = run_service.create_run(
                task_summary="pause invalid",
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                run_id="run-task-10-invalid",
            )
            with self.assertRaises(RuntimeError):
                run_service.pause_run(run.run_id)


if __name__ == "__main__":
    unittest.main()
