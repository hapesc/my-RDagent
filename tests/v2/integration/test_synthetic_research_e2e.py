from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.graph.main_loop import build_main_graph
from v2.models import RunStatus
from v2.runtime import build_v2_runtime
from v2.scenarios.synthetic_research.plugin import SyntheticResearchBundle


class TestSyntheticResearchE2E:
    def test_single_loop_completes(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("synthetic_research", SyntheticResearchBundle())

        run_id = ctx.run_service.create_run(
            {
                "scenario": "synthetic_research",
                "task_summary": "write a brief about benchmark failure modes",
                "max_loops": 1,
            }
        )

        ctx.run_service.start_run(run_id)

        assert ctx.run_service.get_status(run_id) == RunStatus.COMPLETED.value

    def test_all_six_stages_execute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        executed_nodes: list[str] = []
        graph = build_main_graph()
        expected_nodes = ["propose", "experiment_setup", "coding", "running", "feedback", "record"]

        for node_name in expected_nodes:
            original_fn = graph.nodes[node_name]

            def _wrapped(state: dict, *, _name: str = node_name, _fn=original_fn) -> dict:
                executed_nodes.append(_name)
                return _fn(state)

            graph.nodes[node_name] = _wrapped

        monkeypatch.setattr("v2.run_service.build_main_graph", lambda: graph)

        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("synthetic_research", SyntheticResearchBundle())
        run_id = ctx.run_service.create_run(
            {
                "scenario": "synthetic_research",
                "task_summary": "write a brief about benchmark failure modes",
                "max_loops": 1,
            }
        )

        ctx.run_service.start_run(run_id)

        assert executed_nodes == expected_nodes
        assert ctx.run_service.get_status(run_id) == RunStatus.COMPLETED.value

    def test_reference_topics_flow(self) -> None:
        reference_topics = ["evaluation", "benchmarking"]

        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        bundle = SyntheticResearchBundle()
        ctx.plugin_registry.register("synthetic_research", bundle)

        run_id = ctx.run_service.create_run(
            {
                "scenario": "synthetic_research",
                "task_summary": "write a brief about benchmark failure modes",
                "reference_topics": reference_topics,
                "max_loops": 1,
            }
        )

        ctx.run_service.start_run(run_id)

        persisted_topics = ctx.run_service._runs[run_id]["config"]["reference_topics"]
        proposal = bundle.proposer.propose(
            {
                "task_summary": ctx.run_service._runs[run_id]["config"]["task_summary"],
                "reference_topics": persisted_topics,
            }
        )

        assert proposal["reference_topics"] == reference_topics
        assert ctx.run_service.get_status(run_id) == RunStatus.COMPLETED.value

    def test_checkpoint_written(self) -> None:
        bundle = SyntheticResearchBundle()
        graph = build_main_graph()
        final_state = graph.invoke(
            {
                "run_id": "synthetic-checkpoint-e2e",
                "task_summary": "write a brief about benchmark failure modes",
                "reference_topics": ["evaluation", "benchmarking"],
                "loop_iteration": 0,
                "max_loops": 1,
                "_proposer_plugin": bundle.proposer,
                "_coder_plugin": bundle.coder,
                "_runner_plugin": bundle.runner,
                "_evaluator_plugin": bundle.evaluator,
            }
        )

        assert final_state["loop_iteration"] == 1
        assert isinstance(final_state.get("metrics"), list)
        assert len(final_state["metrics"]) == 1

    def test_run_creation_and_metadata(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("synthetic_research", SyntheticResearchBundle())

        run_id = ctx.run_service.create_run(
            {
                "scenario": "synthetic_research",
                "task_summary": "write a brief about benchmark failure modes",
                "max_loops": 1,
            }
        )

        assert uuid.UUID(run_id).version == 4
        assert ctx.run_service.get_status(run_id) == RunStatus.CREATED.value
