"""Tests for runtime config and wiring of new MCTS/VirtualEvaluator fields."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.config import AppConfig, load_config
from app.runtime import RuntimeContext, build_run_service, build_runtime
from core.reasoning.virtual_eval import VirtualEvaluator
from exploration_manager.reward import RewardCalculator
from exploration_manager.scheduler import MCTSScheduler
from llm import LLMAdapter


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
        with patch.dict(
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
        ):
            runtime = build_runtime()
            run_service = build_run_service(runtime, "data_science")
            step_executor = run_service._loop_engine._step_executor

            self.assertIs(step_executor._llm_adapter, runtime.llm_adapter)
            self.assertIs(step_executor._memory_service, runtime.memory_service)
            self.assertEqual(step_executor._costeer_max_rounds, 2)


if __name__ == "__main__":
    unittest.main()
