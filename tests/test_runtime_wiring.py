"""Tests for runtime config and wiring of new MCTS/VirtualEvaluator fields."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from app.config import load_config
from app.runtime import (
    RuntimeContext,
    build_real_provider_smoke_step_overrides,
    build_run_service,
    build_runtime,
    resolve_scenario_runtime_profile,
)
from core.reasoning.virtual_eval import VirtualEvaluator
from exploration_manager.reward import RewardCalculator
from exploration_manager.scheduler import MCTSScheduler
from service_contracts import StepOverrideConfig
from tests._llm_test_utils import patch_runtime_llm_provider


class TestConfigDefaults(unittest.TestCase):
    """Test that new config fields have correct defaults."""

    def test_config_mcts_c_puct_default(self):
        """Test mcts_c_puct has default value of 1.41."""
        config = load_config({})
        self.assertEqual(config.mcts_c_puct, 1.41)

    def test_config_mcts_reward_mode_default(self):
        """Test mcts_reward_mode has default value of 'score_based'."""
        config = load_config({})
        self.assertEqual(config.mcts_reward_mode, "score_based")

    def test_config_layer0_n_candidates_default(self):
        """Test layer0_n_candidates has default value of 5."""
        config = load_config({})
        self.assertEqual(config.layer0_n_candidates, 5)

    def test_config_layer0_k_forward_default(self):
        """Test layer0_k_forward has default value of 2."""
        config = load_config({})
        self.assertEqual(config.layer0_k_forward, 2)

    def test_real_provider_defaults_switch_to_conservative_profile(self):
        config = load_config(
            {
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
            }
        )

        self.assertTrue(config.uses_real_llm_provider)
        self.assertEqual(config.layer0_n_candidates, 1)
        self.assertEqual(config.layer0_k_forward, 1)
        self.assertEqual(config.costeer_max_rounds, 1)
        self.assertEqual(config.sandbox_timeout_sec, 120)
        self.assertEqual(config.real_provider_warnings, ())

    def test_config_mcts_exploration_weight_still_exists(self):
        """Test backward compat: mcts_exploration_weight field still exists."""
        config = load_config({})
        self.assertEqual(config.mcts_exploration_weight, 1.41)


class TestConfigEnvVars(unittest.TestCase):
    """Test that load_config reads new env vars correctly."""

    def test_load_config_mcts_c_puct_from_env(self):
        """Test RD_AGENT_MCTS_C_PUCT env var is parsed."""
        config = load_config({"RD_AGENT_MCTS_C_PUCT": "2.5"})
        self.assertEqual(config.mcts_c_puct, 2.5)

    def test_load_config_mcts_reward_mode_from_env(self):
        """Test RD_AGENT_MCTS_REWARD_MODE env var is parsed."""
        config = load_config({"RD_AGENT_MCTS_REWARD_MODE": "decision_based"})
        self.assertEqual(config.mcts_reward_mode, "decision_based")

    def test_load_config_layer0_n_candidates_from_env(self):
        """Test RD_AGENT_LAYER0_N_CANDIDATES env var is parsed."""
        config = load_config({"RD_AGENT_LAYER0_N_CANDIDATES": "10"})
        self.assertEqual(config.layer0_n_candidates, 10)

    def test_load_config_layer0_k_forward_from_env(self):
        """Test RD_AGENT_LAYER0_K_FORWARD env var is parsed."""
        config = load_config({"RD_AGENT_LAYER0_K_FORWARD": "3"})
        self.assertEqual(config.layer0_k_forward, 3)

    def test_load_config_multiple_env_vars(self):
        """Test multiple env vars are parsed together."""
        env = {
            "RD_AGENT_MCTS_C_PUCT": "2.0",
            "RD_AGENT_MCTS_REWARD_MODE": "decision_based",
            "RD_AGENT_LAYER0_N_CANDIDATES": "7",
            "RD_AGENT_LAYER0_K_FORWARD": "4",
        }
        config = load_config(env)
        self.assertEqual(config.mcts_c_puct, 2.0)
        self.assertEqual(config.mcts_reward_mode, "decision_based")
        self.assertEqual(config.layer0_n_candidates, 7)
        self.assertEqual(config.layer0_k_forward, 4)

    def test_real_provider_hard_limit_rejects_unsafe_layer0_override(self):
        with self.assertRaisesRegex(
            ValueError,
            "real provider guardrail violation: layer0_n_candidates=4 exceeds hard limit 2",
        ):
            load_config(
                {
                    "RD_AGENT_LLM_PROVIDER": "litellm",
                    "RD_AGENT_LLM_API_KEY": "test-key",
                    "RD_AGENT_LAYER0_N_CANDIDATES": "4",
                }
            )

    def test_real_provider_warns_on_non_conservative_but_allowed_settings(self):
        config = load_config(
            {
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
                "RD_AGENT_COSTEER_MAX_ROUNDS": "2",
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "240",
            }
        )

        self.assertEqual(
            config.real_provider_warnings,
            (
                "real provider warning: costeer_max_rounds=2 exceeds conservative profile 1",
                "real provider warning: sandbox_timeout_sec=240 exceeds conservative profile 120",
            ),
        )

    def test_resolve_scenario_runtime_profile_warns_for_allowed_step_timeout_override(self):
        config = load_config(
            {
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
            }
        )
        with patch_runtime_llm_provider():
            manifest = build_runtime().plugin_registry.get_manifest("data_science")
        assert manifest is not None
        defaults = build_real_provider_smoke_step_overrides(
            config,
            manifest.default_step_overrides,
        )

        profile = resolve_scenario_runtime_profile(
            config,
            defaults,
            StepOverrideConfig.from_dict({"running": {"timeout_sec": 240}}),
        )

        self.assertIn(
            "real provider warning: running.timeout_sec=240 exceeds conservative profile 120",
            profile.guardrail_warnings,
        )

    def test_resolve_scenario_runtime_profile_rejects_dangerous_step_retry_override(self):
        config = load_config(
            {
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
            }
        )
        with patch_runtime_llm_provider():
            manifest = build_runtime().plugin_registry.get_manifest("data_science")
        assert manifest is not None
        defaults = build_real_provider_smoke_step_overrides(
            config,
            manifest.default_step_overrides,
        )

        with self.assertRaisesRegex(
            ValueError,
            "real provider guardrail violation: proposal.max_retries=2 exceeds hard limit 1",
        ):
            resolve_scenario_runtime_profile(
                config,
                defaults,
                StepOverrideConfig.from_dict({"proposal": {"max_retries": 2}}),
            )


class TestRuntimeWiring(unittest.TestCase):
    """Test that build_runtime() wires up new components correctly."""

    @patch("app.runtime.SQLiteMetadataStore")
    @patch("app.runtime.BranchTraceStore")
    @patch("app.runtime.FileCheckpointStore")
    @patch("app.runtime.WorkspaceManager")
    @patch("app.runtime.Planner")
    @patch("app.runtime.ExplorationManager")
    @patch("app.runtime.MemoryService")
    @patch("app.runtime.EvaluationService")
    @patch("app.runtime.build_default_registry")
    @patch("app.runtime.load_config")
    @patch("app.runtime._create_llm_provider")
    def test_build_runtime_creates_scheduler_with_c_puct(
        self,
        mock_create_llm_provider,
        mock_load_config,
        mock_build_registry,
        mock_eval_service,
        mock_mem_service,
        mock_exploration_manager,
        mock_planner,
        mock_workspace_manager,
        mock_checkpoint_store,
        mock_branch_store,
        mock_sqlite_store,
    ):
        """Test that build_runtime creates MCTSScheduler with c_puct parameter."""
        # Setup mock config with custom c_puct value
        mock_config = MagicMock()
        mock_config.mcts_c_puct = 2.5
        mock_config.mcts_reward_mode = "score_based"
        mock_config.layer0_n_candidates = 10
        mock_config.layer0_k_forward = 3
        mock_config.prune_threshold = 0.5
        mock_config.artifact_root = "/tmp"
        mock_config.sqlite_path = "/tmp/test.db"
        mock_config.workspace_root = "/tmp/workspace"
        mock_config.trace_storage_path = "/tmp/trace.jsonl"
        mock_config.allow_local_execution = False
        mock_config.sandbox_timeout_sec = 300
        mock_config.use_llm_planning = False
        mock_load_config.return_value = mock_config

        # Setup mock LLM provider
        mock_llm_provider = MagicMock()
        mock_create_llm_provider.return_value = mock_llm_provider

        # Setup other mocks
        mock_sqlite_store.return_value = MagicMock()
        mock_branch_store.return_value = MagicMock()
        mock_checkpoint_store.return_value = MagicMock()
        mock_workspace_manager.return_value = MagicMock()
        mock_planner.return_value = MagicMock()
        mock_exploration_manager.return_value = MagicMock()
        mock_mem_service.return_value = MagicMock()
        mock_eval_service.return_value = MagicMock()
        mock_build_registry.return_value = MagicMock()

        # Build runtime
        runtime = build_runtime()

        # Verify runtime context is created
        self.assertIsInstance(runtime, RuntimeContext)
        self.assertIsNotNone(runtime.scheduler)
        self.assertIsInstance(runtime.scheduler, MCTSScheduler)

        # Verify scheduler has correct c_puct value
        # (scheduler._c_puct is private, but we verify via the scheduler object)
        self.assertEqual(runtime.scheduler._c_puct, 2.5)

    @patch("app.runtime.SQLiteMetadataStore")
    @patch("app.runtime.BranchTraceStore")
    @patch("app.runtime.FileCheckpointStore")
    @patch("app.runtime.WorkspaceManager")
    @patch("app.runtime.Planner")
    @patch("app.runtime.ExplorationManager")
    @patch("app.runtime.MemoryService")
    @patch("app.runtime.EvaluationService")
    @patch("app.runtime.build_default_registry")
    @patch("app.runtime.load_config")
    @patch("app.runtime._create_llm_provider")
    def test_build_runtime_creates_scheduler_with_reward_calculator(
        self,
        mock_create_llm_provider,
        mock_load_config,
        mock_build_registry,
        mock_eval_service,
        mock_mem_service,
        mock_exploration_manager,
        mock_planner,
        mock_workspace_manager,
        mock_checkpoint_store,
        mock_branch_store,
        mock_sqlite_store,
    ):
        """Test that build_runtime creates RewardCalculator with correct mode."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.mcts_c_puct = 1.41
        mock_config.mcts_reward_mode = "decision_based"
        mock_config.layer0_n_candidates = 5
        mock_config.layer0_k_forward = 2
        mock_config.prune_threshold = 0.5
        mock_config.artifact_root = "/tmp"
        mock_config.sqlite_path = "/tmp/test.db"
        mock_config.workspace_root = "/tmp/workspace"
        mock_config.trace_storage_path = "/tmp/trace.jsonl"
        mock_config.allow_local_execution = False
        mock_config.sandbox_timeout_sec = 300
        mock_config.use_llm_planning = False
        mock_load_config.return_value = mock_config

        # Setup other mocks
        mock_llm_provider = MagicMock()
        mock_create_llm_provider.return_value = mock_llm_provider
        mock_sqlite_store.return_value = MagicMock()
        mock_branch_store.return_value = MagicMock()
        mock_checkpoint_store.return_value = MagicMock()
        mock_workspace_manager.return_value = MagicMock()
        mock_planner.return_value = MagicMock()
        mock_exploration_manager.return_value = MagicMock()
        mock_mem_service.return_value = MagicMock()
        mock_eval_service.return_value = MagicMock()
        mock_build_registry.return_value = MagicMock()

        # Build runtime
        runtime = build_runtime()

        # Verify scheduler's reward calculator has correct mode
        self.assertIsInstance(runtime.scheduler._reward_calculator, RewardCalculator)
        self.assertEqual(runtime.scheduler._reward_calculator._mode, "decision_based")

    @patch("app.runtime.SQLiteMetadataStore")
    @patch("app.runtime.BranchTraceStore")
    @patch("app.runtime.FileCheckpointStore")
    @patch("app.runtime.WorkspaceManager")
    @patch("app.runtime.Planner")
    @patch("app.runtime.ExplorationManager")
    @patch("app.runtime.MemoryService")
    @patch("app.runtime.EvaluationService")
    @patch("app.runtime.build_default_registry")
    @patch("app.runtime.load_config")
    @patch("app.runtime._create_llm_provider")
    def test_build_runtime_creates_virtual_evaluator(
        self,
        mock_create_llm_provider,
        mock_load_config,
        mock_build_registry,
        mock_eval_service,
        mock_mem_service,
        mock_exploration_manager,
        mock_planner,
        mock_workspace_manager,
        mock_checkpoint_store,
        mock_branch_store,
        mock_sqlite_store,
    ):
        """Test that build_runtime creates VirtualEvaluator with correct params."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.mcts_c_puct = 1.41
        mock_config.mcts_reward_mode = "score_based"
        mock_config.layer0_n_candidates = 8
        mock_config.layer0_k_forward = 4
        mock_config.prune_threshold = 0.5
        mock_config.artifact_root = "/tmp"
        mock_config.sqlite_path = "/tmp/test.db"
        mock_config.workspace_root = "/tmp/workspace"
        mock_config.trace_storage_path = "/tmp/trace.jsonl"
        mock_config.allow_local_execution = False
        mock_config.sandbox_timeout_sec = 300
        mock_config.use_llm_planning = False
        mock_load_config.return_value = mock_config

        # Setup other mocks
        mock_llm_provider = MagicMock()
        mock_create_llm_provider.return_value = mock_llm_provider
        mock_sqlite_store.return_value = MagicMock()
        mock_branch_store.return_value = MagicMock()
        mock_checkpoint_store.return_value = MagicMock()
        mock_workspace_manager.return_value = MagicMock()
        mock_planner.return_value = MagicMock()
        mock_exploration_manager.return_value = MagicMock()
        mock_mem_service.return_value = MagicMock()
        mock_eval_service.return_value = MagicMock()
        mock_build_registry.return_value = MagicMock()

        # Build runtime
        runtime = build_runtime()

        # Verify virtual_evaluator is created and stored in RuntimeContext
        self.assertIsNotNone(runtime.virtual_evaluator)
        self.assertIsInstance(runtime.virtual_evaluator, VirtualEvaluator)

        # Verify it has correct n_candidates and k_forward
        assert runtime.virtual_evaluator is not None
        self.assertEqual(runtime.virtual_evaluator._n_candidates, 8)
        self.assertEqual(runtime.virtual_evaluator._k_forward, 4)

    def test_build_run_service_wires_costeer_dependencies_into_step_executor(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-wiring",
                    "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-wiring",
                    "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-wiring/events.jsonl",
                    "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-wiring/meta.db",
                    "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                    "RD_AGENT_LLM_PROVIDER": "mock",
                    "RD_AGENT_COSTEER_MAX_ROUNDS": "2",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()
            run_service = build_run_service(runtime, "data_science")
            step_executor = run_service._loop_engine._step_executor

            self.assertIs(step_executor._llm_adapter, runtime.llm_adapter)
            self.assertIs(step_executor._memory_service, runtime.memory_service)
            self.assertEqual(step_executor._costeer_max_rounds, 2)

    def test_build_run_service_wires_layer0_params_into_loop_engine(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-layer0",
                    "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-layer0",
                    "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-layer0/events.jsonl",
                    "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-layer0/meta.db",
                    "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                    "RD_AGENT_LLM_PROVIDER": "mock",
                    "RD_AGENT_LAYER0_N_CANDIDATES": "11",
                    "RD_AGENT_LAYER0_K_FORWARD": "6",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()
            run_service = build_run_service(runtime, "data_science")
            loop_engine_config = run_service._loop_engine._config

            self.assertEqual(loop_engine_config.layer0_n_candidates, 11)
            self.assertEqual(loop_engine_config.layer0_k_forward, 6)

    def test_build_runtime_wires_fc3_proposal_components_into_registry(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-registry",
                    "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-registry",
                    "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-registry/events.jsonl",
                    "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-registry/meta.db",
                    "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                    "RD_AGENT_LLM_PROVIDER": "mock",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()
            data_science_bundle = runtime.plugin_registry.create_bundle("data_science")
            synthetic_bundle = runtime.plugin_registry.create_bundle("synthetic_research")

            self.assertIsNotNone(runtime.reasoning_pipeline)
            self.assertIsNotNone(runtime.virtual_evaluator)
            self.assertIs(
                getattr(data_science_bundle.proposal_engine, "_reasoning_pipeline", None),
                runtime.reasoning_pipeline,
            )
            self.assertIs(
                getattr(data_science_bundle.proposal_engine, "_virtual_evaluator", None),
                runtime.virtual_evaluator,
            )
            self.assertIs(
                getattr(synthetic_bundle.proposal_engine, "_reasoning_pipeline", None),
                runtime.reasoning_pipeline,
            )
            self.assertIs(
                getattr(synthetic_bundle.proposal_engine, "_virtual_evaluator", None),
                runtime.virtual_evaluator,
            )

    def test_build_runtime_uses_real_provider_safe_step_defaults(self):
        with patch.dict(
            "os.environ",
            {
                "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-real-safe",
                "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-real-safe",
                "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-real-safe/events.jsonl",
                "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-real-safe/meta.db",
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
            },
            clear=False,
        ):
            runtime = build_runtime()
            manifest = runtime.plugin_registry.get_manifest("data_science")

            assert manifest is not None
            self.assertEqual(runtime.config.sandbox_timeout_sec, 120)
            self.assertEqual(manifest.default_step_overrides.proposal.provider, "litellm")
            self.assertEqual(manifest.default_step_overrides.proposal.model, runtime.config.llm_model)
            self.assertEqual(manifest.default_step_overrides.proposal.max_retries, 1)
            self.assertEqual(manifest.default_step_overrides.coding.max_retries, 1)
            self.assertEqual(manifest.default_step_overrides.feedback.max_retries, 1)
            self.assertEqual(manifest.default_step_overrides.running.timeout_sec, 120)

    def test_build_runtime_injects_virtual_evaluator_into_exploration_manager(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-exploration",
                    "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-exploration",
                    "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-exploration/events.jsonl",
                    "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-exploration/meta.db",
                    "AGENTRD_ALLOW_LOCAL_EXECUTION": "true",
                    "RD_AGENT_LLM_PROVIDER": "mock",
                },
                clear=False,
            ),
            patch_runtime_llm_provider(),
        ):
            runtime = build_runtime()

            self.assertIs(runtime.exploration_manager._virtual_evaluator, runtime.virtual_evaluator)

    def test_build_real_provider_smoke_step_overrides_enforces_conservative_preset(self):
        with patch.dict(
            "os.environ",
            {
                "AGENTRD_ARTIFACT_ROOT": "/tmp/rd-agent-artifacts-runtime-smoke-profile",
                "AGENTRD_WORKSPACE_ROOT": "/tmp/rd-agent-workspace-runtime-smoke-profile",
                "AGENTRD_TRACE_STORAGE_PATH": "/tmp/rd-agent-runtime-smoke-profile/events.jsonl",
                "AGENTRD_SQLITE_PATH": "/tmp/rd-agent-runtime-smoke-profile/meta.db",
                "RD_AGENT_LLM_PROVIDER": "litellm",
                "RD_AGENT_LLM_API_KEY": "test-key",
                "RD_AGENT_COSTEER_MAX_ROUNDS": "2",
                "AGENTRD_SANDBOX_TIMEOUT_SEC": "240",
            },
            clear=False,
        ):
            runtime = build_runtime()
            manifest = runtime.plugin_registry.get_manifest("synthetic_research")

            assert manifest is not None
            smoke_overrides = build_real_provider_smoke_step_overrides(
                runtime.config,
                manifest.default_step_overrides,
            )

            self.assertEqual(smoke_overrides.proposal.max_retries, 1)
            self.assertEqual(smoke_overrides.coding.max_retries, 1)
            self.assertEqual(smoke_overrides.feedback.max_retries, 1)
            self.assertEqual(smoke_overrides.running.timeout_sec, 120)

    def test_import_smoke_for_runtime_cycle_breaks(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import plugins; import exploration_manager.service; "
                    "import scenarios.synthetic_research.plugin; print('ok')"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
