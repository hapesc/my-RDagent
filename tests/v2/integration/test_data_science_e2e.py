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

    def test_all_six_stages_execute(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        bundle = DataScienceBundle()
        graph = build_main_graph(
            checkpointer=MemorySaver(),
            proposer_plugin=bundle.proposer,
            coder_plugin=bundle.coder,
            runner_plugin=bundle.runner,
            evaluator_plugin=bundle.evaluator,
        )
        config = {"configurable": {"thread_id": "ds-stages"}}

        state = {
            "run_id": "ds-stages",
            "task_summary": "classify iris",
            "loop_iteration": 0,
            "max_loops": 1,
            "step_state": "CREATED",
            "proposal": None,
            "experiment": None,
            "code_result": None,
            "run_result": None,
            "feedback": None,
            "metrics": None,
            "error": None,
            "tokens_used": 0,
            "token_budget": 0,
        }
        events = list(graph.stream(state, config, stream_mode="updates"))
        executed_nodes = [list(e.keys())[0] for e in events if not list(e.keys())[0].startswith("__")]

        assert executed_nodes == ["propose", "experiment_setup", "coding", "running", "feedback", "record"]

    def test_costeer_subgraph_invoked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import v2.graph.costeer as costeer_module

        invoked = {"count": 0}
        original_build = costeer_module.build_costeer_subgraph

        def _wrapped_build_costeer_subgraph(*args: object, **kwargs: object):
            invoked["count"] += 1
            return original_build(*args, **kwargs)

        monkeypatch.setattr(costeer_module, "build_costeer_subgraph", _wrapped_build_costeer_subgraph)

        bundle = DataScienceBundle()
        graph = build_main_graph(coder_plugin=bundle.coder)
        final_state = graph.invoke(
            {
                "run_id": "costeer-e2e",
                "task_summary": "classify iris",
                "loop_iteration": 0,
                "max_loops": 1,
                "step_state": "CREATED",
                "proposal": None,
                "experiment": None,
                "code_result": None,
                "run_result": None,
                "feedback": None,
                "metrics": None,
                "error": None,
                "tokens_used": 0,
                "token_budget": 0,
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
                "step_state": "CREATED",
                "proposal": None,
                "experiment": None,
                "code_result": None,
                "run_result": None,
                "feedback": None,
                "metrics": None,
                "error": None,
                "tokens_used": 0,
                "token_budget": 0,
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
