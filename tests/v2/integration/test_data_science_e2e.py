from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from v2.graph.main_loop import build_main_graph
from v2.models import RunStatus
from v2.runtime import build_v2_runtime
from v2.scenarios.data_science.plugin import DataScienceBundle


class TestDataScienceE2E:
    def test_single_loop_completes(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("data_science", DataScienceBundle())

        run_id = ctx.run_service.create_run(
            {
                "scenario": "data_science",
                "task_summary": "classify iris",
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
        ctx.plugin_registry.register("data_science", DataScienceBundle())
        run_id = ctx.run_service.create_run(
            {
                "scenario": "data_science",
                "task_summary": "classify iris",
                "max_loops": 1,
            }
        )

        ctx.run_service.start_run(run_id)

        assert executed_nodes == expected_nodes
        assert ctx.run_service.get_status(run_id) == RunStatus.COMPLETED.value

    def test_costeer_subgraph_invoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import v2.graph.costeer as costeer_module

        invoked = {"count": 0}
        original_build = costeer_module.build_costeer_subgraph

        def _wrapped_build_costeer_subgraph(*args: object, **kwargs: object):
            invoked["count"] += 1
            return original_build(*args, **kwargs)

        monkeypatch.setattr(costeer_module, "build_costeer_subgraph", _wrapped_build_costeer_subgraph)

        graph = build_main_graph()
        final_state = graph.invoke(
            {
                "run_id": "costeer-e2e",
                "task_summary": "classify iris",
                "loop_iteration": 0,
                "max_loops": 1,
                "_coder_plugin": DataScienceBundle().coder,
            }
        )

        assert invoked["count"] >= 1
        assert final_state.get("code_result") is not None

    def test_checkpoint_written(self) -> None:
        graph = build_main_graph()
        final_state = graph.invoke(
            {
                "run_id": "checkpoint-e2e",
                "task_summary": "classify iris",
                "loop_iteration": 0,
                "max_loops": 1,
            }
        )

        assert final_state["loop_iteration"] == 1
        assert isinstance(final_state.get("metrics"), list)
        assert len(final_state["metrics"]) == 1

    def test_run_creation_and_metadata(self) -> None:
        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("data_science", DataScienceBundle())

        run_id = ctx.run_service.create_run(
            {
                "scenario": "data_science",
                "task_summary": "classify iris",
                "max_loops": 1,
            }
        )

        assert uuid.UUID(run_id).version == 4
        assert ctx.run_service.get_status(run_id) == RunStatus.CREATED.value

    def test_registered_bundle_plugins_are_injected_into_graph(self) -> None:
        proposer_called: list[bool] = []

        bundle = DataScienceBundle()
        original_propose = bundle.proposer.propose

        def _spy_propose(state: dict) -> dict:
            proposer_called.append(True)
            return original_propose(state)

        bundle.proposer.propose = _spy_propose  # type: ignore[method-assign]

        ctx = build_v2_runtime({"llm_provider": "mock", "max_loops": 1})
        ctx.plugin_registry.register("data_science", bundle)

        run_id = ctx.run_service.create_run(
            {"scenario": "data_science", "task_summary": "classify iris", "max_loops": 1}
        )
        ctx.run_service.start_run(run_id)

        assert proposer_called, "registered proposer plugin was never called — plugin injection is broken"
        assert ctx.run_service.get_status(run_id) == RunStatus.COMPLETED.value
