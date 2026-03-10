"""Tests for quant scenario plugin bundle (TDD)."""

import json
from pathlib import Path

import pytest

from data_models import (
    CodeArtifact,
    ExecutionResult,
    ExperimentNode,
    LoopState,
    Proposal,
    RunSession,
    RunStatus,
)
from llm import LLMAdapter, LLMAdapterConfig, MockLLMProvider
from plugins import build_default_registry
from plugins.contracts import ScenarioContext, UsefulnessGateInput
from scenarios.quant.data_provider import MockDataProvider
from scenarios.quant.plugin import (
    QuantCoder,
    QuantConfig,
    QuantExperimentGenerator,
    QuantRunner,
    QuantScenarioPlugin,
    _validate_quant_usefulness,
    build_quant_bundle,
)
from scenarios.quant.prompts import FACTOR_CODE_SYSTEM_PROMPT, FACTOR_CODE_USER_TEMPLATE


@pytest.fixture
def run_session():
    return RunSession(
        run_id="test-run-001",
        scenario="quant",
        status=RunStatus.RUNNING,
        active_branch_ids=["main"],
    )


@pytest.fixture
def loop_state():
    return LoopState(loop_id="loop-001", iteration=0)


@pytest.fixture
def scenario_ctx(run_session):
    plugin = QuantScenarioPlugin()
    return plugin.build_context(run_session, {"task_summary": "mine momentum factor"})


@pytest.fixture
def proposal():
    return Proposal(
        proposal_id="p-001",
        summary="Compute 20-day momentum as factor signal.",
        constraints=["use only price data", "must be cross-sectional"],
        virtual_score=0.6,
    )


@pytest.fixture
def tmp_workspace(tmp_path):
    return tmp_path


class TestQuantScenarioPlugin:
    def test_build_context_returns_correct_run_id(self, run_session):
        plugin = QuantScenarioPlugin()
        ctx = plugin.build_context(run_session, {"task_summary": "test"})
        assert ctx.run_id == "test-run-001"

    def test_build_context_sets_scenario_name(self, run_session):
        plugin = QuantScenarioPlugin()
        ctx = plugin.build_context(run_session, {})
        assert ctx.scenario_name == "quant"

    def test_build_context_default_task_summary(self, run_session):
        plugin = QuantScenarioPlugin()
        ctx = plugin.build_context(run_session, {})
        assert ctx.task_summary == "mine alpha factors"


class TestQuantPrompts:
    def test_factor_code_system_prompt_mentions_lookahead_and_self_check(self):
        assert ".shift(-n)" in FACTOR_CODE_SYSTEM_PROMPT
        assert "SELF-CHECK before returning" in FACTOR_CODE_SYSTEM_PROMPT
        assert "date, stock_id, factor_value" in FACTOR_CODE_SYSTEM_PROMPT

    def test_factor_code_user_template_contains_second_reference_pattern(self):
        assert "pct_change(5)" in FACTOR_CODE_USER_TEMPLATE
        assert "rolling(20).std()" in FACTOR_CODE_USER_TEMPLATE


class TestQuantExperimentGenerator:
    def test_generate_returns_experiment_node(self, proposal, run_session, loop_state, tmp_workspace):
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        node = gen.generate(proposal, run_session, loop_state, [])
        assert isinstance(node, ExperimentNode)

    def test_generate_node_id_contains_run_id(self, proposal, run_session, loop_state, tmp_workspace):
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        node = gen.generate(proposal, run_session, loop_state, [])
        assert "test-run-001" in node.node_id

    def test_generate_with_parent(self, proposal, run_session, loop_state, tmp_workspace):
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        node = gen.generate(proposal, run_session, loop_state, ["parent-001"])
        assert node.parent_node_id == "parent-001"


class TestQuantCoder:
    def test_develop_creates_factor_py(self, proposal, scenario_ctx, tmp_workspace):
        coder = QuantCoder(llm_adapter=None)
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        loop_state = LoopState(loop_id="loop-001", iteration=0)
        node = gen.generate(
            proposal,
            RunSession(run_id="r", scenario="quant", status=RunStatus.RUNNING),
            loop_state,
            [],
        )
        artifact = coder.develop(node, proposal, scenario_ctx)
        factor_path = Path(artifact.location) / "factor.py"
        assert factor_path.exists()

    def test_develop_returns_code_artifact(self, proposal, scenario_ctx, tmp_workspace):
        coder = QuantCoder(llm_adapter=None)
        gen = QuantExperimentGenerator(workspace_root=str(tmp_workspace))
        loop_state = LoopState(loop_id="loop-002", iteration=0)
        node = gen.generate(
            proposal,
            RunSession(run_id="r2", scenario="quant", status=RunStatus.RUNNING),
            loop_state,
            [],
        )
        artifact = coder.develop(node, proposal, scenario_ctx)
        assert isinstance(artifact, CodeArtifact)
        assert artifact.location


class TestQuantRunner:
    def test_run_success_with_valid_factor(self, scenario_ctx, tmp_workspace):
        config = QuantConfig(
            workspace_root=str(tmp_workspace),
            n_stocks=10,
            n_days=100,
            backtest_config={"train_end": "2020-06-30", "test_start": "2020-07-01"},
            data_provider=MockDataProvider(n_stocks=10, n_days=100),
        )
        runner = QuantRunner(config=config)
        factor_dir = tmp_workspace / "factor_workspace"
        factor_dir.mkdir()
        (factor_dir / "factor.py").write_text(
            "import pandas as pd\n"
            "def compute_factor(df):\n"
            "    return df.groupby('stock_id')['close'].pct_change(5).fillna(0)\n"
        )
        artifact = CodeArtifact(artifact_id="a1", description="test", location=str(factor_dir))
        result = runner.run(artifact, scenario_ctx)
        assert isinstance(result, ExecutionResult)

    def test_run_error_when_no_factor_file(self, scenario_ctx, tmp_workspace):
        runner = QuantRunner()
        empty_dir = tmp_workspace / "empty"
        empty_dir.mkdir()
        artifact = CodeArtifact(artifact_id="a2", description="test", location=str(empty_dir))
        result = runner.run(artifact, scenario_ctx)
        assert result.exit_code != 0


class TestValidateQuantUsefulness:
    def _make_gate_input(self, payload):
        from data_models import ExecutionResult

        result = ExecutionResult(
            run_id="test",
            exit_code=0,
            logs_ref=json.dumps(payload),
            artifacts_ref=json.dumps([]),
        )
        ctx = ScenarioContext(run_id="test", scenario_name="quant", input_payload={})
        return UsefulnessGateInput(
            scenario=ctx,
            result=result,
            artifact_paths=[],
            artifact_texts={},
            normalized_text=json.dumps(payload),
            structured_payload=payload,
        )

    def test_missing_payload_rejected(self):
        gate = self._make_gate_input(None)
        gate.structured_payload = None
        reason = _validate_quant_usefulness(gate)
        assert reason is not None

    def test_failed_status_rejected(self):
        reason = _validate_quant_usefulness(self._make_gate_input({"status": "error"}))
        assert reason is not None

    def test_good_metrics_pass(self):
        payload = {"status": "success", "sharpe": 1.2, "ic_mean": 0.05, "icir": 0.5, "mdd": -0.1}
        reason = _validate_quant_usefulness(self._make_gate_input(payload))
        assert reason is None

    def test_low_sharpe_rejected(self):
        payload = {"status": "success", "sharpe": 0.1, "ic_mean": 0.05}
        reason = _validate_quant_usefulness(self._make_gate_input(payload))
        assert reason is not None

    def test_low_ic_rejected(self):
        payload = {"status": "success", "sharpe": 1.5, "ic_mean": 0.001}
        reason = _validate_quant_usefulness(self._make_gate_input(payload))
        assert reason is not None


class TestBuildQuantBundle:
    def test_bundle_has_correct_scenario_name(self):
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        bundle = build_quant_bundle(llm_adapter=adapter)
        assert bundle.scenario_name == "quant"

    def test_bundle_has_all_components(self):
        adapter = LLMAdapter(provider=MockLLMProvider(), config=LLMAdapterConfig(max_retries=1))
        bundle = build_quant_bundle(llm_adapter=adapter)
        assert bundle.scenario_plugin is not None
        assert bundle.proposal_engine is not None
        assert bundle.experiment_generator is not None
        assert bundle.coder is not None
        assert bundle.runner is not None
        assert bundle.feedback_analyzer is not None

    def test_registry_includes_quant(self):
        registry = build_default_registry()
        assert "quant" in registry.list_scenarios()
