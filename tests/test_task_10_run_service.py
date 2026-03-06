"""Task-10 tests for run lifecycle control and resume manager."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Optional

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import (
    LoopEngine,
    LoopEngineConfig,
    ResumeManager,
    RunService,
    RunServiceConfig,
    StepExecutor,
)
from core.storage import (
    BranchTraceStore,
    BranchTraceStoreConfig,
    CheckpointStoreConfig,
    FileCheckpointStore,
    SQLiteMetadataStore,
    SQLiteStoreConfig,
)
from data_models import (
    CodeArtifact,
    ContextPack,
    ExecutionResult,
    ExperimentNode,
    FeedbackRecord,
    LoopState,
    Plan,
    Proposal,
    RunSession,
    RunStatus,
    Score,
    StepState,
    StopConditions,
)
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from plugins.contracts import PluginBundle, ScenarioContext
from plugins.examples import build_minimal_data_science_bundle


class ResumeAwareScenarioPlugin:
    def build_context(self, run_session: RunSession, input_payload):
        return ScenarioContext(
            run_id=run_session.run_id,
            scenario_name=run_session.scenario,
            input_payload=dict(input_payload),
            task_summary=str(input_payload.get("task_summary", "")),
        )


class ResumeAwareProposalEngine:
    def propose(self, task_summary, context: ContextPack, parent_ids, plan: Plan, scenario: ScenarioContext) -> Proposal:
        _ = context
        _ = parent_ids
        _ = plan
        return Proposal(
            proposal_id=f"proposal-{scenario.run_id}-{scenario.input_payload['loop_index']}",
            summary=task_summary,
        )


class ResumeAwareExperimentGenerator:
    def generate(
        self,
        proposal: Proposal,
        run_session: RunSession,
        loop_state: LoopState,
        parent_ids,
    ) -> ExperimentNode:
        branch_id = run_session.active_branch_ids[0] if run_session.active_branch_ids else "main"
        parent_node_id = parent_ids[0] if parent_ids else None
        node_id = f"node-{run_session.run_id}-{branch_id}-{loop_state.iteration}"
        return ExperimentNode(
            node_id=node_id,
            run_id=run_session.run_id,
            branch_id=branch_id,
            parent_node_id=parent_node_id,
            loop_index=loop_state.iteration,
            step_state=StepState.EXPERIMENT_READY,
            hypothesis={"text": proposal.summary},
        )


class ResumeAwareCoder:
    def develop(self, experiment: ExperimentNode, proposal: Proposal, scenario: ScenarioContext) -> CodeArtifact:
        _ = proposal
        workspace = Path(experiment.workspace_ref)
        workspace.mkdir(parents=True, exist_ok=True)
        loop_index = int(scenario.input_payload["loop_index"])
        if loop_index == 0:
            (workspace / "seed.txt").write_text("resume-state", encoding="utf-8")
        (workspace / "artifact.txt").write_text(f"loop={loop_index}", encoding="utf-8")
        return CodeArtifact(
            artifact_id=f"artifact-{experiment.node_id}",
            description="resume-aware",
            location=str(workspace),
        )


class ResumeAwareRunner:
    def run(self, artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult:
        workspace = Path(artifact.location)
        loop_index = int(scenario.input_payload["loop_index"])
        seed_path = workspace / "seed.txt"
        if loop_index > 0 and not seed_path.exists():
            return ExecutionResult(
                run_id=scenario.run_id,
                exit_code=9,
                logs_ref="missing resumed seed",
                artifacts_ref="[]",
            )
        return ExecutionResult(
            run_id=scenario.run_id,
            exit_code=0,
            logs_ref="seed ok",
            artifacts_ref="[]",
        )


class ResumeAwareFeedbackAnalyzer:
    def summarize(
        self,
        experiment: ExperimentNode,
        result: ExecutionResult,
        score: Optional[Score] = None,
    ) -> FeedbackRecord:
        _ = score
        return FeedbackRecord(
            feedback_id=f"fb-{experiment.node_id}",
            decision=result.exit_code == 0,
            acceptable=result.exit_code == 0,
            reason=result.logs_ref,
        )


class RunServiceTests(unittest.TestCase):
    def _build_resume_aware_bundle(self) -> PluginBundle:
        return PluginBundle(
            scenario_name="data_science",
            scenario_plugin=ResumeAwareScenarioPlugin(),
            proposal_engine=ResumeAwareProposalEngine(),
            experiment_generator=ResumeAwareExperimentGenerator(),
            coder=ResumeAwareCoder(),
            runner=ResumeAwareRunner(),
            feedback_analyzer=ResumeAwareFeedbackAnalyzer(),
        )

    def _build_runtime(self, tmpdir: str, bundle: Optional[PluginBundle] = None):
        sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(Path(tmpdir) / "meta.db")))
        branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=str(Path(tmpdir) / "meta.db")))
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
        plugin_bundle = bundle or build_minimal_data_science_bundle()
        step_executor = StepExecutor(
            plugin_bundle,
            evaluation_service,
            workspace_manager,
            sqlite_store,
            branch_store=branch_store,
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
        resume_manager = ResumeManager(checkpoint_store=checkpoint_store, workspace_manager=workspace_manager)
        run_service = RunService(
            config=RunServiceConfig(default_scenario="data_science"),
            loop_engine=loop_engine,
            run_store=sqlite_store,
            resume_manager=resume_manager,
            branch_store=branch_store,
        )
        return run_service, sqlite_store, checkpoint_store, branch_store

    def test_pause_resume_stop_with_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, sqlite_store, checkpoint_store, _branch_store = self._build_runtime(tmpdir)
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

            restarted_service, restarted_store, _checkpoint_store, _branch_store = self._build_runtime(tmpdir)
            context2 = restarted_service.resume_run(run.run_id, task_summary="resume test", loops_per_call=1)
            self.assertEqual(context2.loop_state.iteration, 2)
            self.assertEqual(restarted_store.get_run(run.run_id).status, RunStatus.COMPLETED)

            stopped = restarted_service.stop_run(run.run_id)
            self.assertEqual(stopped.status, RunStatus.STOPPED)

    def test_invalid_pause_transition_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, _, _, _ = self._build_runtime(tmpdir)
            run = run_service.create_run(
                task_summary="pause invalid",
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
                run_id="run-task-10-invalid",
            )
            with self.assertRaises(RuntimeError):
                run_service.pause_run(run.run_id)

    def test_fork_branch_persists_nodes_and_updates_heads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, sqlite_store, checkpoint_store, branch_store = self._build_runtime(tmpdir)
            run = run_service.create_run(
                task_summary="fork test",
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
                run_id="run-task-10-fork",
            )

            context1 = run_service.start_run(run.run_id, task_summary="fork test", loops_per_call=1)
            self.assertEqual(context1.loop_state.iteration, 1)
            main_head = branch_store.get_branch_heads(run.run_id)["main"]

            forked = run_service.fork_branch(run.run_id, parent_node_id=main_head)
            fork_branch_id = forked.active_branch_ids[0]
            self.assertNotEqual(fork_branch_id, "main")
            self.assertEqual(forked.status, RunStatus.PAUSED)
            self.assertEqual(forked.entry_input["fork_checkpoint_id"], "loop-0000-record")

            context2 = run_service.resume_run(run.run_id, task_summary="fork test", loops_per_call=1)
            self.assertEqual(context2.loop_state.iteration, 2)
            self.assertGreaterEqual(len(checkpoint_store.list_checkpoints(run.run_id)), 12)
            self.assertEqual(sqlite_store.get_run(run.run_id).status, RunStatus.COMPLETED)

            heads = branch_store.get_branch_heads(run.run_id)
            self.assertEqual(heads["main"], main_head)
            self.assertIn(fork_branch_id, heads)

            fork_nodes = branch_store.query_nodes(run.run_id, branch_id=fork_branch_id)
            self.assertEqual(len(fork_nodes), 1)
            self.assertEqual(fork_nodes[0].parent_node_id, main_head)

    def test_resume_uses_restored_workspace_as_iteration_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, sqlite_store, _checkpoint_store, _branch_store = self._build_runtime(
                tmpdir,
                bundle=self._build_resume_aware_bundle(),
            )
            run = run_service.create_run(
                task_summary="resume workspace test",
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
                run_id="run-task-10-resume-state",
            )

            context1 = run_service.start_run(run.run_id, task_summary="resume workspace test", loops_per_call=1)
            self.assertEqual(context1.loop_state.iteration, 1)
            self.assertTrue((Path(tmpdir) / "workspaces" / run.run_id / "loop-0000" / "seed.txt").exists())

            paused = run_service.pause_run(run.run_id)
            self.assertEqual(paused.status, RunStatus.PAUSED)

            context2 = run_service.resume_run(run.run_id, task_summary="resume workspace test", loops_per_call=1)
            self.assertEqual(context2.loop_state.iteration, 2)
            self.assertEqual(sqlite_store.get_run(run.run_id).status, RunStatus.COMPLETED)

            resumed_seed = Path(tmpdir) / "workspaces" / run.run_id / "loop-0001" / "seed.txt"
            self.assertTrue(resumed_seed.exists())
            self.assertEqual(resumed_seed.read_text(encoding="utf-8"), "resume-state")

    def test_fork_from_earlier_parent_keeps_main_history_intact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_service, _sqlite_store, _checkpoint_store, branch_store = self._build_runtime(tmpdir)
            run = run_service.create_run(
                task_summary="collision test",
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=120),
                run_id="run-collision",
            )

            context = run_service.start_run(run.run_id, task_summary="collision test", loops_per_call=2)
            self.assertEqual(context.loop_state.iteration, 2)

            main_nodes_before = branch_store.query_nodes(run.run_id, branch_id="main")
            main_node_ids_before = [node.node_id for node in main_nodes_before]
            self.assertEqual(len(main_nodes_before), 2)
            main_head_before = branch_store.get_branch_heads(run.run_id)["main"]

            forked = run_service.fork_branch(run.run_id, parent_node_id=main_nodes_before[0].node_id)
            fork_branch_id = forked.active_branch_ids[0]

            resumed = run_service.resume_run(run.run_id, task_summary="collision test", loops_per_call=1)
            self.assertEqual(resumed.loop_state.iteration, 2)

            heads = branch_store.get_branch_heads(run.run_id)
            self.assertEqual(heads["main"], main_head_before)
            self.assertIn(fork_branch_id, heads)

            main_nodes_after = branch_store.query_nodes(run.run_id, branch_id="main")
            self.assertEqual([node.node_id for node in main_nodes_after], main_node_ids_before)

            fork_nodes = branch_store.query_nodes(run.run_id, branch_id=fork_branch_id)
            self.assertEqual(len(fork_nodes), 1)
            self.assertEqual(fork_nodes[0].loop_index, 1)
            self.assertEqual(fork_nodes[0].parent_node_id, main_nodes_before[0].node_id)
            self.assertNotIn(fork_nodes[0].node_id, main_node_ids_before)


if __name__ == "__main__":
    unittest.main()
