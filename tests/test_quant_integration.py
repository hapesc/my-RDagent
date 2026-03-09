"""T12: Integration test — full factor mining loop end-to-end."""

import json
from pathlib import Path

import pytest

from data_models import (
    CodeArtifact,
    FeedbackRecord,
    LoopState,
    Proposal,
    RunSession,
    RunStatus,
)
from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider
from scenarios.quant.data_provider import MockDataProvider
from scenarios.quant.plugin import (
    QuantCoder,
    QuantConfig,
    QuantExperimentGenerator,
    QuantFeedbackAnalyzer,
    QuantRunner,
    QuantScenarioPlugin,
    build_quant_bundle,
)

# Small backtest config that fits within n_days=100
_SMALL_BT_CONFIG = {"train_end": "2020-06-30", "test_start": "2020-07-01"}


class TestFullFactorMiningLoop:
    """Tests the complete propose→code→run→feedback loop."""

    @pytest.fixture
    def run_session(self):
        return RunSession(
            run_id="integration-run-001",
            scenario="quant",
            status=RunStatus.RUNNING,
            active_branch_ids=["main"],
        )

    @pytest.fixture
    def loop_state(self):
        return LoopState(loop_id="integration-loop-001", iteration=0)

    @pytest.fixture
    def proposal(self):
        return Proposal(
            proposal_id="p-integration-001",
            summary="Compute 5-day momentum as alpha factor.",
            constraints=["use only close price", "must be cross-sectional"],
            virtual_score=0.65,
        )

    @pytest.fixture
    def tmp_workspace(self, tmp_path):
        return tmp_path

    def test_full_loop_returns_feedback_record(self, run_session, loop_state, proposal, tmp_workspace):
        """Full pipeline: build_context → generate → develop → run → summarize."""
        # 1. Build context
        plugin = QuantScenarioPlugin()
        ctx = plugin.build_context(run_session, {"task_summary": "mine momentum factor"})
        assert ctx.run_id == "integration-run-001"
        assert ctx.scenario_name == "quant"

        # 2. Generate experiment node
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        node = gen.generate(proposal, run_session, loop_state, [])
        assert node is not None
        assert "integration-run-001" in node.node_id

        # 3. Develop factor code (no LLM → falls back to default code)
        coder = QuantCoder(llm_adapter=None)
        artifact = coder.develop(node, proposal, ctx)
        assert isinstance(artifact, CodeArtifact)
        factor_path = Path(artifact.location) / "factor.py"
        assert factor_path.exists()

        # 4. Run backtest
        config = QuantConfig(
            workspace_root=str(tmp_workspace),
            n_stocks=10,
            n_days=100,
            backtest_config=_SMALL_BT_CONFIG,
            data_provider=MockDataProvider(n_stocks=10, n_days=100),
        )
        runner = QuantRunner(config=config)
        result = runner.run(artifact, ctx)
        assert result is not None
        # exit_code may be 0 (success) or non-zero (factor quality issue) — both valid
        assert result.exit_code is not None

        # 5. Analyze feedback
        analyzer = QuantFeedbackAnalyzer()
        feedback = analyzer.summarize(node, result)
        assert isinstance(feedback, FeedbackRecord)
        assert feedback.feedback_id.startswith("quant-fb-")

    def test_full_loop_with_bundle(self, run_session, loop_state, proposal, tmp_workspace):
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        bundle = build_quant_bundle(
            QuantConfig(
                workspace_root=str(tmp_workspace),
                n_stocks=10,
                n_days=100,
                backtest_config=_SMALL_BT_CONFIG,
                data_provider=MockDataProvider(n_stocks=10, n_days=100),
            ),
            llm_adapter=adapter,
        )

        ctx = bundle.scenario_plugin.build_context(run_session, {"task_summary": "mine momentum factor via bundle"})
        node = bundle.experiment_generator.generate(proposal, run_session, loop_state, [])
        artifact = bundle.coder.develop(node, proposal, ctx)
        result = bundle.runner.run(artifact, ctx)
        feedback = bundle.feedback_analyzer.summarize(node, result)

        assert isinstance(feedback, FeedbackRecord)

    def test_feedback_contains_metrics_when_run_succeeds(self, run_session, loop_state, proposal, tmp_workspace):
        config = QuantConfig(
            workspace_root=str(tmp_workspace),
            n_stocks=10,
            n_days=100,
            backtest_config=_SMALL_BT_CONFIG,
            data_provider=MockDataProvider(n_stocks=10, n_days=100),
        )
        plugin = QuantScenarioPlugin()
        ctx = plugin.build_context(run_session, {"task_summary": "test metrics"})

        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        node = gen.generate(proposal, run_session, loop_state, [])

        coder = QuantCoder(llm_adapter=None)
        artifact = coder.develop(node, proposal, ctx)

        runner = QuantRunner(config=config)
        result = runner.run(artifact, ctx)

        if result.exit_code == 0:
            # Successful run: feedback should capture metric payload
            payload = json.loads(result.logs_ref) if result.logs_ref else {}
            assert payload.get("status") == "success"
            assert "sharpe" in payload

        analyzer = QuantFeedbackAnalyzer()
        feedback = analyzer.summarize(node, result)
        assert feedback is not None

    def test_two_iteration_loop(self, run_session, tmp_workspace):
        config = QuantConfig(
            workspace_root=str(tmp_workspace),
            n_stocks=10,
            n_days=100,
            backtest_config=_SMALL_BT_CONFIG,
            data_provider=MockDataProvider(n_stocks=10, n_days=100),
        )
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        bundle = build_quant_bundle(config, llm_adapter=adapter)
        ctx = bundle.scenario_plugin.build_context(run_session, {"task_summary": "two-iteration test"})

        prev_feedback = None
        for i in range(2):
            ls = LoopState(loop_id=f"loop-iter-{i}", iteration=i)
            prop = Proposal(
                proposal_id=f"p-iter-{i}",
                summary=f"Momentum factor iteration {i}",
                constraints=["use close price"],
                virtual_score=0.6,
            )
            node = bundle.experiment_generator.generate(
                prop, run_session, ls, [prev_feedback.feedback_id] if prev_feedback else []
            )
            artifact = bundle.coder.develop(node, prop, ctx)
            result = bundle.runner.run(artifact, ctx)
            prev_feedback = bundle.feedback_analyzer.summarize(node, result)
            assert isinstance(prev_feedback, FeedbackRecord)
