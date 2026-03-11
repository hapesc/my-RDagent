"""Task-19 tests for the formal synthetic_research scenario."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agentrd_cli import ExitCode, main
from app.runtime import build_run_service, build_runtime
from data_models import ExecutionResult, StopConditions
from plugins import build_default_registry
from plugins.contracts import CommonUsefulnessGate, ScenarioContext
from scenarios.synthetic_research.plugin import SyntheticResearchCoder, build_synthetic_research_bundle
from tests._llm_test_utils import make_mock_llm_adapter, patch_runtime_llm_provider


class SyntheticResearchScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmpdir.name)
        self._env_patch = patch.dict(
            os.environ,
            {
                "AGENTRD_SQLITE_PATH": str(tmp_path / "meta.db"),
                "AGENTRD_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
                "AGENTRD_WORKSPACE_ROOT": str(tmp_path / "workspaces"),
                "AGENTRD_TRACE_STORAGE_PATH": str(tmp_path / "trace.jsonl"),
                "AGENTRD_ALLOW_LOCAL_EXECUTION": "1",
            },
            clear=False,
        )
        self._env_patch.start()
        self._llm_patch = patch_runtime_llm_provider()
        self._llm_patch.start()

    def tearDown(self) -> None:
        self._llm_patch.stop()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def _run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def _synthetic_usefulness_result(self, payload: dict) -> tuple:
        bundle = build_synthetic_research_bundle(llm_adapter=make_mock_llm_adapter())
        artifact = Path(self._tmpdir.name) / "validator-summary.json"
        artifact.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        result = ExecutionResult(
            run_id="run-task-19-usefulness",
            exit_code=0,
            logs_ref="synthetic research complete",
            artifacts_ref=json.dumps([str(artifact)]),
        )
        scenario = ScenarioContext(
            run_id="run-task-19-usefulness",
            scenario_name="synthetic_research",
            input_payload={"task_summary": payload.get("task_summary", "")},
            task_summary=str(payload.get("task_summary", "")),
        )
        gate = CommonUsefulnessGate()
        return gate.evaluate(result, scenario, scene_validator=bundle.scene_usefulness_validator)

    def test_default_registry_exposes_formal_synthetic_research_scenario(self) -> None:
        registry = build_default_registry(llm_adapter=make_mock_llm_adapter())

        self.assertIn("data_science", registry.list_scenarios())
        self.assertIn("synthetic_research", registry.list_scenarios())
        self.assertNotIn("data_science_minimal", registry.list_scenarios())

        bundle = registry.create_bundle("synthetic_research")
        manifest = registry.get_manifest("synthetic_research")

        self.assertEqual(bundle.scenario_name, "synthetic_research")
        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest.scenario_name, "synthetic_research")

    def test_synthetic_research_runs_through_shared_loop_engine(self) -> None:
        runtime = build_runtime()
        run_service = build_run_service(runtime, "synthetic_research")
        run = run_service.create_run(
            task_summary="synth scenario",
            scenario="synthetic_research",
            run_id="run-task-19-runtime",
            stop_conditions=StopConditions(max_loops=1, max_duration_sec=60),
        )

        context = run_service.start_run(
            run_id=run.run_id,
            task_summary="synth scenario",
            loops_per_call=1,
        )

        assert context is not None
        assert context.run_session is not None
        self.assertEqual(context.run_session.scenario, "synthetic_research")
        self.assertEqual(context.run_session.status.value, "COMPLETED")
        events = runtime.sqlite_store.query_events(run_id=run.run_id)
        self.assertGreaterEqual(len(events), 6)
        summary_path = Path(os.environ["AGENTRD_WORKSPACE_ROOT"]) / run.run_id / "loop-0000" / "research_summary.json"
        self.assertTrue(summary_path.exists())

    def test_cli_run_supports_synthetic_research(self) -> None:
        code, out, err = self._run_cli(
            [
                "run",
                "--scenario",
                "synthetic_research",
                "--input",
                '{"task_summary":"synthetic cli","reference_topics":["llm","benchmark"],"max_loops":1}',
            ]
        )

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload["scenario"], "synthetic_research")
        self.assertEqual(payload["run"]["scenario"], "synthetic_research")
        self.assertEqual(payload["run"]["config_snapshot"]["scenario_manifest"]["scenario_name"], "synthetic_research")
        artifact_paths = [item["path"] for item in payload["artifacts_page"]["items"]]
        self.assertTrue(any(path.endswith("research_summary.json") for path in artifact_paths))

    def test_health_check_lists_synthetic_research_manifest(self) -> None:
        code, out, err = self._run_cli(["health-check", "--verbose"])

        self.assertEqual(code, int(ExitCode.OK))
        self.assertEqual(err, "")
        payload = json.loads(out)
        manifests = payload["details"]["scenario_manifests"]

        self.assertIn("synthetic_research", payload["details"]["registered_scenarios"])
        self.assertTrue(any(item["scenario_name"] == "synthetic_research" for item in manifests))
        self.assertFalse(any(item["scenario_name"] == "data_science_minimal" for item in manifests))

    def test_usefulness_rejects_template_only_synthesized_summary(self) -> None:
        outcome, signal = self._synthetic_usefulness_result(
            {
                "task_summary": "compare retrieval strategies for coding agents",
                "artifact_id": "artifact-1",
                "topic_count": 1,
                "topics": ["retrieval"],
                "synthesized_summary": "Synthesized summary",
                "synthesized_findings": ["Compared retrieval depth because latency rises."],
            }
        )

        self.assertFalse(outcome.usefulness_eligible)
        self.assertEqual(signal.stage, "utility")
        self.assertEqual(
            signal.reason,
            "scene validator rejected: generic synthesized summary",
        )

    def test_usefulness_rejects_prompt_echo_findings(self) -> None:
        task_summary = "benchmark retrieval depth for synthetic research"
        outcome, signal = self._synthetic_usefulness_result(
            {
                "task_summary": task_summary,
                "artifact_id": "artifact-2",
                "topic_count": 1,
                "topics": ["retrieval depth"],
                "synthesized_summary": "Compared retrieval depth because latency rises.",
                "synthesized_findings": [
                    f"Task: {task_summary}",
                    f"Research task: {task_summary}",
                ],
            }
        )

        self.assertFalse(outcome.usefulness_eligible)
        self.assertEqual(signal.stage, "utility")
        self.assertEqual(
            signal.reason,
            "scene validator rejected: prompt-echo synthesized findings",
        )

    def test_usefulness_accepts_task_specific_synthesized_findings(self) -> None:
        outcome, signal = self._synthetic_usefulness_result(
            {
                "task_summary": "evaluate retrieval depth and rerank quality",
                "artifact_id": "artifact-3",
                "topic_count": 2,
                "topics": ["retrieval depth", "rerank quality"],
                "synthesized_summary": (
                    "Compared retrieval depth against rerank quality because latency "
                    "and precision move in opposite directions."
                ),
                "synthesized_findings": [
                    (
                        "Compared retrieval depth options, precision gains plateau "
                        "after top-20 context while latency keeps increasing."
                    ),
                    (
                        "However, rerank quality improves evidence relevance, so a "
                        "depth-10 plus rerank trade-off reduces risk under tight budgets."
                    ),
                ],
            }
        )

        self.assertTrue(outcome.usefulness_eligible)
        self.assertEqual(signal.stage, "utility")
        self.assertEqual(signal.reason, "eligible")

    def test_coder_falls_back_on_placeholder_output_from_llm(self) -> None:
        """synthetic_research is text-first and non-blocking — placeholder LLM output
        triggers a graceful fallback (proposal.summary used as description) instead of
        raising an exception."""
        from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider
        from data_models import ExperimentNode, Proposal

        raw = "## Findings\n1. TODO: fill in results\n2. TBD"
        coder = SyntheticResearchCoder(
            llm_adapter=LLMAdapter(provider=MockLLMProvider(responses=[raw]), config=LLMAdapterConfig(max_retries=0))
        )
        experiment = ExperimentNode(node_id="node-1", run_id="run-1", branch_id="main", workspace_ref=self._tmpdir.name)
        proposal = Proposal(proposal_id="p-1", summary="synthetic task", constraints=[])
        scenario = ScenarioContext(
            run_id="run-1", scenario_name="synthetic_research", input_payload={}, task_summary="synthetic task"
        )

        artifact = coder.develop(experiment, proposal, scenario)
        self.assertIsNotNone(artifact)
        self.assertIn("synthetic task", artifact.description)


if __name__ == "__main__":
    unittest.main()
