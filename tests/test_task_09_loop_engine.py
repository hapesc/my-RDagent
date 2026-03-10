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
from data_models import EventType, ExecutionResult, FeedbackRecord, RunSession, RunStatus, StopConditions
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


class FalseSuccessRunner:
    def run(self, artifact, scenario):
        _ = artifact
        _ = scenario
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref="process-ok-but-no-artifacts",
            artifacts_ref="[]",
        )


class NonZeroExitRunner:
    def run(self, artifact, scenario):
        _ = artifact
        _ = scenario
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=1,
            logs_ref="process-failed",
            artifacts_ref="[]",
        )


class UsefulnessRejectedRunner:
    def run(self, artifact, scenario):
        _ = artifact
        _ = scenario
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref='{"status": "ok"}',
            artifacts_ref='["artifact.json"]',
        )


class UsefulnessEligibleRunner:
    def run(self, artifact, scenario):
        _ = artifact
        _ = scenario
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref='{"status": "ok", "metric": 0.91}',
            artifacts_ref='["artifact.json"]',
        )


class AlwaysPositiveFeedbackAnalyzer:
    def summarize(self, experiment, result, score=None):
        _ = experiment
        _ = result
        _ = score
        return FeedbackRecord(
            feedback_id="fb-force-positive",
            decision=True,
            acceptable=True,
            reason="runner exited cleanly",
        )


class SyntheticReasonPositiveAnalyzer:
    def summarize(self, experiment, result, score=None):
        _ = experiment
        _ = result
        _ = score
        return FeedbackRecord(
            feedback_id="fb-synthetic-positive",
            decision=True,
            acceptable=True,
            reason="synthetic placeholder output preventing real assessment",
        )


class LoopEngineTests(unittest.TestCase):
    def _build_services(self, tmpdir: str):
        sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(Path(tmpdir) / "meta.db")))
        checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=str(Path(tmpdir) / "checkpoints")))
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
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.COMPLETED)

            events = sqlite_store.query_events(run_id="run-task-09-success")
            self.assertGreaterEqual(len(events), 6)
            timed_events = [
                event
                for event in events
                if event.event_type
                in {
                    EventType.HYPOTHESIS_GENERATED,
                    EventType.EXPERIMENT_GENERATED,
                    EventType.CODING_ROUND,
                    EventType.EXECUTION_FINISHED,
                    EventType.FEEDBACK_GENERATED,
                }
            ]
            self.assertTrue(timed_events)
            self.assertTrue(all(isinstance(event.payload.get("step_latency_ms"), int) for event in timed_events))
            self.assertTrue(all(event.payload.get("step_latency_ms", -1) >= 0 for event in timed_events))

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
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.FAILED)

            archive_file = Path(tmpdir) / "artifacts" / "run-task-09-fail" / "exceptions" / "loop-0000.log"
            self.assertTrue(archive_file.exists())
            self.assertIn("simulated execution failure", archive_file.read_text(encoding="utf-8"))

            events = sqlite_store.query_events(run_id="run-task-09-fail")
            self.assertGreaterEqual(len(events), 1)
            self.assertEqual(events[-1].payload.get("status"), "FAILED")

    def test_false_success_is_marked_ineligible_by_shared_contract(self) -> None:
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
            contract_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=FalseSuccessRunner(),
                feedback_analyzer=AlwaysPositiveFeedbackAnalyzer(),
            )
            step_executor = StepExecutor(contract_bundle, evaluation_service, workspace_manager, sqlite_store)
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
                run_id="run-task-09-contract",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09-contract"},
            )
            context = loop_engine.run(run_session=run_session, task_summary="contract test", max_loops=1)

            self.assertEqual(context.loop_state.status, RunStatus.FAILED)
            persisted_run = sqlite_store.get_run("run-task-09-contract")
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.FAILED)
            events = sqlite_store.query_events(run_id="run-task-09-contract")
            execution_event = next(event for event in events if event.event_type == EventType.EXECUTION_FINISHED)
            feedback_event = next(event for event in events if event.event_type == EventType.FEEDBACK_GENERATED)

            self.assertEqual(execution_event.payload.get("process_status"), "SUCCESS")
            self.assertEqual(execution_event.payload.get("artifact_status"), "MISSING_REQUIRED")
            self.assertEqual(execution_event.payload.get("usefulness_status"), "INELIGIBLE")
            execution_latency_ms = execution_event.payload.get("step_latency_ms")
            self.assertIsInstance(execution_latency_ms, int)
            assert isinstance(execution_latency_ms, int)
            self.assertGreaterEqual(execution_latency_ms, 0)
            self.assertFalse(feedback_event.payload.get("decision"))
            self.assertFalse(feedback_event.payload.get("acceptable"))
            feedback_latency_ms = feedback_event.payload.get("step_latency_ms")
            self.assertIsInstance(feedback_latency_ms, int)
            assert isinstance(feedback_latency_ms, int)
            self.assertGreaterEqual(feedback_latency_ms, 0)

    def test_nonzero_exit_fails_iteration_and_run(self) -> None:
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
            failed_process_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=NonZeroExitRunner(),
                feedback_analyzer=AlwaysPositiveFeedbackAnalyzer(),
            )
            step_executor = StepExecutor(failed_process_bundle, evaluation_service, workspace_manager, sqlite_store)
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
                run_id="run-task-09-process-fail",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09-process-fail"},
            )
            context = loop_engine.run(run_session=run_session, task_summary="process failure", max_loops=1)

            self.assertEqual(context.loop_state.status, RunStatus.FAILED)
            persisted_run = sqlite_store.get_run("run-task-09-process-fail")
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.FAILED)

            events = sqlite_store.query_events(run_id="run-task-09-process-fail")
            self.assertGreaterEqual(len(events), 2)
            self.assertEqual(events[-1].payload.get("status"), "FAILED")
            self.assertEqual(events[-1].payload.get("failed_stage"), "running")

    def test_usefulness_reject_keeps_mock_run_completed_for_compatibility(self) -> None:
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
            usefulness_reject_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=UsefulnessRejectedRunner(),
                feedback_analyzer=AlwaysPositiveFeedbackAnalyzer(),
            )
            step_executor = StepExecutor(
                usefulness_reject_bundle,
                evaluation_service,
                workspace_manager,
                sqlite_store,
            )
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
                run_id="run-task-09-usefulness-reject",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09-usefulness-reject"},
            )
            context = loop_engine.run(
                run_session=run_session,
                task_summary="usefulness reject contract",
                max_loops=1,
            )

            self.assertEqual(context.loop_state.status, RunStatus.COMPLETED)
            persisted_run = sqlite_store.get_run("run-task-09-usefulness-reject")
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.COMPLETED)

            events = sqlite_store.query_events(run_id="run-task-09-usefulness-reject")
            execution_event = next(event for event in events if event.event_type == EventType.EXECUTION_FINISHED)
            self.assertEqual(execution_event.payload.get("process_status"), "SUCCESS")
            self.assertEqual(execution_event.payload.get("artifact_status"), "VERIFIED")
            self.assertEqual(execution_event.payload.get("usefulness_status"), "INELIGIBLE")

    def test_usefulness_reject_fails_real_provider_run(self) -> None:
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
            usefulness_reject_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=UsefulnessRejectedRunner(),
                feedback_analyzer=AlwaysPositiveFeedbackAnalyzer(),
            )
            step_executor = StepExecutor(
                usefulness_reject_bundle,
                evaluation_service,
                workspace_manager,
                sqlite_store,
            )
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
                run_id="run-task-09-usefulness-reject-real-provider",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09-usefulness-reject-real-provider"},
                config_snapshot={"runtime": {"uses_real_llm_provider": True}},
            )
            context = loop_engine.run(
                run_session=run_session,
                task_summary="usefulness reject real-provider contract",
                max_loops=1,
            )

            self.assertEqual(context.loop_state.status, RunStatus.FAILED)
            persisted_run = sqlite_store.get_run("run-task-09-usefulness-reject-real-provider")
            if persisted_run is None:
                self.fail("expected persisted run")
            self.assertEqual(persisted_run.status, RunStatus.FAILED)

    def test_negative_feedback_reason_forces_unacceptable(self) -> None:
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
            guardrail_bundle = PluginBundle(
                scenario_name=base_bundle.scenario_name,
                scenario_plugin=base_bundle.scenario_plugin,
                proposal_engine=base_bundle.proposal_engine,
                experiment_generator=base_bundle.experiment_generator,
                coder=base_bundle.coder,
                runner=UsefulnessEligibleRunner(),
                feedback_analyzer=SyntheticReasonPositiveAnalyzer(),
            )
            step_executor = StepExecutor(
                guardrail_bundle,
                evaluation_service,
                workspace_manager,
                sqlite_store,
            )
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
                run_id="run-task-09-negative-feedback-guardrail",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-09-negative-feedback-guardrail"},
            )
            _ = loop_engine.run(
                run_session=run_session,
                task_summary="negative reason should force unacceptable",
                max_loops=1,
            )

            events = sqlite_store.query_events(run_id="run-task-09-negative-feedback-guardrail")
            feedback_event = next(event for event in events if event.event_type == EventType.FEEDBACK_GENERATED)

            self.assertFalse(feedback_event.payload.get("acceptable"))
            self.assertTrue(feedback_event.payload.get("decision"))


if __name__ == "__main__":
    unittest.main()
