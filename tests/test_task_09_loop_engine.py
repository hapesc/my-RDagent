"""Task-09 tests for loop engine and step executor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import LoopEngine, LoopEngineConfig, StepExecutor
from core.storage import (
    CheckpointStoreConfig,
    FileCheckpointStore,
    SQLiteMetadataStore,
    SQLiteStoreConfig,
)
from data_models import RunSession, RunStatus, StopConditions
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from plugins.contracts import PluginBundle
from plugins.examples import build_minimal_data_science_bundle


class FailingRunner:
    def run(self, artifact, scenario):
        _ = artifact
        _ = scenario
        raise RuntimeError("simulated execution failure")


class LoopEngineTests(unittest.TestCase):
    def _build_services(self, tmpdir: str):
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
        return (
            sqlite_store,
            checkpoint_store,
            workspace_manager,
            planner,
            exploration_manager,
            memory_service,
            evaluation_service,
        )

    def test_single_thread_completes_one_loop_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (
                sqlite_store,
                checkpoint_store,
                workspace_manager,
                planner,
                exploration_manager,
                memory_service,
                evaluation_service,
            ) = self._build_services(tmpdir)

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

            run_session = RunSession(
                run_id="run-task-09-success",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09"},
            )
            context = loop_engine.run(run_session=run_session, task_summary="loop test", max_loops=1)

            self.assertEqual(context.loop_state.iteration, 1)
            self.assertEqual(context.loop_state.status, RunStatus.COMPLETED)

            persisted_run = sqlite_store.get_run("run-task-09-success")
            self.assertIsNotNone(persisted_run)
            self.assertEqual(persisted_run.status, RunStatus.COMPLETED)

            events = sqlite_store.query_events(run_id="run-task-09-success")
            self.assertGreaterEqual(len(events), 6)

            checkpoints = checkpoint_store.list_checkpoints("run-task-09-success")
            self.assertGreaterEqual(len(checkpoints), 6)

    def test_exception_is_archived_and_run_marked_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (
                sqlite_store,
                _checkpoint_store,
                workspace_manager,
                planner,
                exploration_manager,
                memory_service,
                evaluation_service,
            ) = self._build_services(tmpdir)

            base_bundle = build_minimal_data_science_bundle()
            failing_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=FailingRunner(),
                feedback_analyzer=base_bundle.feedback_analyzer,
            )
            step_executor = StepExecutor(failing_bundle, evaluation_service, workspace_manager, sqlite_store)
            loop_engine = LoopEngine(
                config=LoopEngineConfig(exception_archive_root=str(Path(tmpdir) / "artifacts")),
                planner=planner,
                exploration_manager=exploration_manager,
                memory_service=memory_service,
                step_executor=step_executor,
                run_store=sqlite_store,
                event_store=sqlite_store,
            )

            run_session = RunSession(
                run_id="run-task-09-fail",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09"},
            )
            context = loop_engine.run(run_session=run_session, task_summary="loop failure", max_loops=1)

            self.assertEqual(context.loop_state.status, RunStatus.FAILED)
            persisted_run = sqlite_store.get_run("run-task-09-fail")
            self.assertIsNotNone(persisted_run)
            self.assertEqual(persisted_run.status, RunStatus.FAILED)

            archive_file = Path(tmpdir) / "artifacts" / "run-task-09-fail" / "exceptions" / "loop-0000.log"
            self.assertTrue(archive_file.exists())
            self.assertIn("simulated execution failure", archive_file.read_text(encoding="utf-8"))

            events = sqlite_store.query_events(run_id="run-task-09-fail")
            self.assertGreaterEqual(len(events), 1)
            self.assertEqual(events[-1].payload.get("status"), "FAILED")


if __name__ == "__main__":
    unittest.main()
