"""Task-13 tests for Data Science scenario plugin v1 end-to-end flow."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.execution import WorkspaceManager, WorkspaceManagerConfig
from core.loop import LoopEngine, LoopEngineConfig, StepExecutor
from core.storage import CheckpointStoreConfig, FileCheckpointStore, SQLiteMetadataStore, SQLiteStoreConfig
from data_models import EventType, ExecutionResult, LoopState, Proposal, RunSession, RunStatus, StopConditions
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider
from memory_service import MemoryService, MemoryServiceConfig
from planner import Planner, PlannerConfig
from plugins.contracts import CommonUsefulnessGate, ScenarioContext
from scenarios.data_science import DataScienceV1Config, build_data_science_v1_bundle
from scenarios.data_science.plugin import DataScienceCoder
from tests._llm_test_utils import make_mock_llm_adapter


class DataSciencePluginV1Tests(unittest.TestCase):
    def _scenario_context(self) -> ScenarioContext:
        return ScenarioContext(
            run_id="run-task-13",
            scenario_name="data_science",
            input_payload={"task_summary": "ds plugin usefulness", "loop_index": 0},
            task_summary="ds plugin usefulness",
        )

    def _write_csv(self, path: Path) -> None:
        rows = [
            {"id": "1", "x": "10", "y": "1"},
            {"id": "2", "x": "11", "y": "0"},
            {"id": "3", "x": "12", "y": "1"},
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _experiment(self, workspace: Path):
        return build_data_science_v1_bundle(
            DataScienceV1Config(
                workspace_root=str(workspace.parent),
                trace_storage_path=str(workspace.parent / "trace.jsonl"),
                prefer_docker=False,
                allow_local_execution=True,
            ),
            llm_adapter=make_mock_llm_adapter(),
        ).experiment_generator.generate(
            Proposal(proposal_id="p-1", summary="classify iris data", constraints=["no file I/O"]),
            RunSession(run_id="run-task-13", scenario="data_science", status=RunStatus.RUNNING),
            LoopState(loop_id="loop-1", iteration=0, status=RunStatus.RUNNING),
            [],
        )

    def test_real_input_one_round_e2e_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            data_path = tmp_path / "train.csv"
            self._write_csv(data_path)

            sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=str(tmp_path / "meta.db")))
            checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=str(tmp_path / "checkpoints")))
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
                    allow_local_execution=True,
                ),
                llm_adapter=make_mock_llm_adapter(),
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

            run_session = RunSession(
                run_id="run-task-13",
                scenario="data_science",
                status=RunStatus.CREATED,
                stop_conditions=StopConditions(max_loops=1, max_duration_sec=120),
                entry_input={"task_id": "task-13", "data_source": str(data_path)},
            )
            context = loop_engine.run(run_session=run_session, task_summary="ds plugin e2e", max_loops=1)

            self.assertEqual(context.loop_state.status, RunStatus.COMPLETED)
            persisted_run = sqlite_store.get_run("run-task-13")
            assert persisted_run is not None
            self.assertEqual(persisted_run.status, RunStatus.COMPLETED)

            events = sqlite_store.query_events(run_id="run-task-13")
            self.assertGreaterEqual(len(events), 6)
            execution_event = next(event for event in events if event.event_type == EventType.EXECUTION_FINISHED)
            self.assertEqual(execution_event.payload.get("process_status"), "SUCCESS")
            self.assertEqual(execution_event.payload.get("artifact_status"), "VERIFIED")
            self.assertEqual(execution_event.payload.get("usefulness_status"), "ELIGIBLE")

            checkpoints = checkpoint_store.list_checkpoints("run-task-13")
            self.assertGreaterEqual(len(checkpoints), 6)

            metrics_path = tmp_path / "workspaces" / "run-task-13" / "loop-0000" / "metrics.json"
            self.assertTrue(metrics_path.exists())

    def test_usefulness_rejects_row_count_only_even_with_positive_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "metrics.json"
            artifact.write_text(json.dumps({"status": "ok", "row_count": 42}), encoding="utf-8")
            result = ExecutionResult(
                run_id="run-task-13-gate-reject",
                exit_code=0,
                logs_ref="Great progress: model quality improved and ready for deployment.",
                artifacts_ref=json.dumps([str(artifact)]),
            )

            gate = CommonUsefulnessGate()
            bundle = build_data_science_v1_bundle(llm_adapter=make_mock_llm_adapter())
            outcome, signal = gate.evaluate(
                result,
                self._scenario_context(),
                scene_validator=bundle.scene_usefulness_validator,
            )

            self.assertFalse(outcome.usefulness_eligible)
            self.assertEqual(signal.stage, "utility")
            self.assertEqual(signal.reason, "scene validator rejected: row-count-only payload")

    def test_usefulness_accepts_informative_metrics_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "metrics.json"
            artifact.write_text(
                json.dumps({"status": "ok", "row_count": 42, "column_count": 7, "accuracy": 0.91}),
                encoding="utf-8",
            )
            result = ExecutionResult(
                run_id="run-task-13-gate-pass",
                exit_code=0,
                logs_ref="Execution completed successfully.",
                artifacts_ref=json.dumps([str(artifact)]),
            )

            gate = CommonUsefulnessGate()
            bundle = build_data_science_v1_bundle(llm_adapter=make_mock_llm_adapter())
            outcome, signal = gate.evaluate(
                result,
                self._scenario_context(),
                scene_validator=bundle.scene_usefulness_validator,
            )

            self.assertTrue(outcome.usefulness_eligible)
            self.assertEqual(signal.stage, "utility")
            self.assertEqual(signal.reason, "eligible")

    def test_generator_node_ids_are_branch_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = build_data_science_v1_bundle(
                DataScienceV1Config(
                    workspace_root=str(Path(tmpdir) / "plugin_workspace"),
                    trace_storage_path=str(Path(tmpdir) / "trace.jsonl"),
                    prefer_docker=False,
                    allow_local_execution=True,
                ),
                llm_adapter=make_mock_llm_adapter(),
            )
            proposal = Proposal(proposal_id="proposal-1", summary="branch uniqueness")
            loop_state = LoopState(loop_id="loop-1", iteration=1, status=RunStatus.RUNNING)

            main_run = RunSession(
                run_id="run-branch-unique",
                scenario="data_science",
                status=RunStatus.RUNNING,
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=60),
                active_branch_ids=["main"],
            )
            fork_run = RunSession(
                run_id="run-branch-unique",
                scenario="data_science",
                status=RunStatus.RUNNING,
                stop_conditions=StopConditions(max_loops=2, max_duration_sec=60),
                active_branch_ids=["main-fork-123"],
            )

            main_node = bundle.experiment_generator.generate(proposal, main_run, loop_state, [])
            fork_node = bundle.experiment_generator.generate(proposal, fork_run, loop_state, [])

            self.assertNotEqual(main_node.node_id, fork_node.node_id)

    def test_coder_uses_enhanced_prompt_with_few_shot(self) -> None:
        class PromptCapturingProvider:
            def __init__(self) -> None:
                self.prompts: list[str] = []

            def complete(self, prompt: str, model_config=None) -> str:
                self.prompts.append(prompt)
                return (
                    '{"artifact_id":"artifact-llm","description":"pipeline","location":"/tmp/ws"}\n'
                    "```python\n"
                    "import json\n"
                    "from pathlib import Path\n"
                    "metrics = {'accuracy': 0.9}\n"
                    "Path('metrics.json').write_text(json.dumps(metrics), encoding='utf-8')\n"
                    "```\n"
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = PromptCapturingProvider()
            adapter = LLMAdapter(provider=provider, config=LLMAdapterConfig(max_retries=0))
            coder = DataScienceCoder(llm_adapter=adapter)
            workspace = Path(tmpdir) / "plugin_workspace" / "run-task-13" / "node-run-task-13-main-0"
            experiment = self._experiment(workspace)
            scenario = self._scenario_context()

            coder.develop(experiment, Proposal(proposal_id="p", summary="classify iris data", constraints=[]), scenario)

            self.assertTrue(provider.prompts)
            self.assertIn("## Reference Implementation", provider.prompts[0])

    def test_coder_rejects_placeholder_output_from_llm(self) -> None:
        raw = (
            '{"artifact_id":"artifact-llm","description":"placeholder","location":"/tmp/ws"}\n'
            "```python\n# TODO: implement pipeline\npass\n```\n"
        )
        adapter = LLMAdapter(provider=MockLLMProvider(responses=[raw]), config=LLMAdapterConfig(max_retries=0))

        with tempfile.TemporaryDirectory() as tmpdir:
            coder = DataScienceCoder(llm_adapter=adapter)
            experiment = self._experiment(Path(tmpdir) / "workspace")
            with self.assertRaises(ValueError):
                coder.develop(experiment, Proposal(proposal_id="p", summary="task", constraints=[]), self._scenario_context())

    def test_coder_extracts_real_code_from_llm_response(self) -> None:
        raw = (
            '{"artifact_id":"artifact-llm","description":"real pipeline","location":"/tmp/ws"}\n'
            "```python\n"
            "import json\n"
            "from pathlib import Path\n"
            "metrics = {'accuracy': 0.91}\n"
            "Path('metrics.json').write_text(json.dumps(metrics), encoding='utf-8')\n"
            "```\n"
        )
        adapter = LLMAdapter(provider=MockLLMProvider(responses=[raw]), config=LLMAdapterConfig(max_retries=0))

        with tempfile.TemporaryDirectory() as tmpdir:
            coder = DataScienceCoder(llm_adapter=adapter)
            experiment = self._experiment(Path(tmpdir) / "workspace")
            artifact = coder.develop(
                experiment,
                Proposal(proposal_id="p", summary="task", constraints=[]),
                self._scenario_context(),
            )
            pipeline_text = (Path(artifact.location) / "pipeline.py").read_text(encoding="utf-8")
            self.assertIn("metrics.json", pipeline_text)
            self.assertNotIn("row_count = 0", pipeline_text)

    def test_coder_runs_quality_gate_before_returning(self) -> None:
        raw = (
            '{"artifact_id":"artifact-llm","description":"real pipeline","location":"/tmp/ws"}\n'
            "```python\ndef build_pipeline():\n    return 1\n```"
        )
        adapter = LLMAdapter(provider=MockLLMProvider(responses=[raw]), config=LLMAdapterConfig(max_retries=0))

        with tempfile.TemporaryDirectory() as tmpdir:
            coder = DataScienceCoder(llm_adapter=adapter)
            experiment = self._experiment(Path(tmpdir) / "workspace")
            with patch("scenarios.data_science.plugin.CodegenQualityGate.evaluate") as evaluate:
                from llm.codegen.quality_gate import QualityResult

                evaluate.return_value = QualityResult(
                    passed=True,
                    reasons=[],
                    extracted_code="def build_pipeline():\n    return 1",
                    metadata={"artifact_id": "artifact-llm", "description": "real pipeline", "location": "/tmp/ws"},
                )
                coder.develop(
                    experiment,
                    Proposal(proposal_id="p", summary="task", constraints=[]),
                    self._scenario_context(),
                )
                evaluate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
