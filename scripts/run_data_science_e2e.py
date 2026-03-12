"""
End-to-end data_science integration test with auth-first LiteLLM backend selection.
走完整 loop engine 一次循环。

用法:
    export RD_AGENT_TEST_LLM_BACKEND=chatgpt  # optional, prefers ChatGPT subscription auth
    # or export OPENCODE_API=<your_key>        # fallback path
    python scripts/run_data_science_e2e.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

# --------------------------------------------------------------------------- #
# 把项目根加入 sys.path（脚本从 scripts/ 子目录运行时需要）
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #
TASK_SUMMARY = "classify a small synthetic dataset"

# --------------------------------------------------------------------------- #
# 日志
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("data_science_e2e")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Data Science E2E Integration Test: OpenCode Kimi K2.5, local execution enabled."
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=1,
        help="Number of loop iterations (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    max_loops = args.max_loops

    from scripts.real_test_llm import build_test_llm_provider, resolve_test_llm_backend

    backend = resolve_test_llm_backend()
    if backend.mode != "chatgpt_auth" and not backend.api_key:
        log.error(
            "No test LLM backend available. Either export RD_AGENT_TEST_LLM_BACKEND=chatgpt "
            "after LiteLLM ChatGPT login, or export OPENCODE_API / RD_AGENT_LLM_API_KEY."
        )
        sys.exit(1)

    log.info("=== Data Science E2E Integration Test ===")
    log.info("Task      : %s", TASK_SUMMARY)
    log.info("Backend   : %s", backend.display_name)
    log.info("Model     : %s", backend.model)
    log.info("Max loops : %d", max_loops)
    print()

    # ---------------------------------------------------------------------- #
    # 1. 构建 LLM adapter
    # ---------------------------------------------------------------------- #
    from llm import LLMAdapter, LLMAdapterConfig

    log.info("[1/4] Building LLM adapter (%s)...", backend.display_name)
    provider = build_test_llm_provider(backend.api_key)
    llm_adapter = LLMAdapter(
        provider=provider,
        config=LLMAdapterConfig(max_retries=2),
    )
    log.info("      LLM adapter ready.")

    # ---------------------------------------------------------------------- #
    # 2. 构建 data_science plugin bundle（开启本地执行，禁用 Docker 偏好）
    # ---------------------------------------------------------------------- #
    from scenarios.data_science.plugin import DataScienceV1Config, build_data_science_v1_bundle

    run_id = f"data-science-e2e-{uuid.uuid4().hex[:8]}"
    workspace_root = f"/tmp/rd_agent_data_science_e2e/{run_id}"
    artifact_root = f"/tmp/rd_agent_data_science_e2e_artifacts/{run_id}"
    sqlite_path = f"/tmp/rd_agent_data_science_e2e_{run_id}.db"

    log.info("[2/4] Building data_science plugin bundle...")
    ds_config = DataScienceV1Config(
        workspace_root=workspace_root,
        allow_local_execution=True,
        prefer_docker=False,
    )
    ds_bundle = build_data_science_v1_bundle(
        config=ds_config,
        llm_adapter=llm_adapter,
    )
    log.info("      Plugin bundle ready.")

    # ---------------------------------------------------------------------- #
    # 3. 构建 runtime 依赖（loop engine, run service）
    # ---------------------------------------------------------------------- #
    from core.execution import WorkspaceManager, WorkspaceManagerConfig
    from core.loop import LoopEngine, LoopEngineConfig, ResumeManager, RunService, RunServiceConfig, StepExecutor
    from core.reasoning.pipeline import ReasoningPipeline
    from core.reasoning.virtual_eval import VirtualEvaluator
    from core.storage import (
        BranchTraceStore,
        BranchTraceStoreConfig,
        CheckpointStoreConfig,
        FileCheckpointStore,
        SQLiteMetadataStore,
        SQLiteStoreConfig,
    )
    from evaluation_service import EvaluationService, EvaluationServiceConfig
    from exploration_manager import ExplorationManager, ExplorationManagerConfig
    from exploration_manager.merging import TraceMerger
    from exploration_manager.pruning import BranchPruner
    from exploration_manager.reward import RewardCalculator
    from exploration_manager.scheduler import MCTSScheduler
    from memory_service import MemoryService, MemoryServiceConfig
    from memory_service.hypothesis_selector import HypothesisSelector
    from memory_service.interaction_kernel import InteractionKernel
    from planner import Planner, PlannerConfig

    log.info("[3/4] Wiring runtime components...")

    sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=sqlite_path))
    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=sqlite_path))
    checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=f"{artifact_root}/checkpoints"))
    workspace_manager = WorkspaceManager(
        WorkspaceManagerConfig(root_dir=workspace_root),
        checkpoint_store=checkpoint_store,
    )
    interaction_kernel = InteractionKernel()
    hypothesis_selector = HypothesisSelector(
        interaction_kernel=interaction_kernel,
        llm_adapter=llm_adapter,
    )
    memory_service = MemoryService(
        MemoryServiceConfig(),
        hypothesis_selector=hypothesis_selector,
        interaction_kernel=interaction_kernel,
    )
    reasoning_pipeline = ReasoningPipeline(
        llm_adapter,
        trace_store=None,
    )
    virtual_evaluator = VirtualEvaluator(
        llm_adapter,
        n_candidates=1,
        k_forward=1,
        reasoning_pipeline=reasoning_pipeline,
    )
    scheduler = MCTSScheduler(
        c_puct=1.41,
        reward_calculator=RewardCalculator(mode="score_based"),
    )
    pruner = BranchPruner(relative_threshold=0.5)
    merger = TraceMerger(llm_adapter)

    step_executor = StepExecutor(
        plugin_bundle=ds_bundle,
        evaluation_service=EvaluationService(EvaluationServiceConfig()),
        workspace_manager=workspace_manager,
        event_store=sqlite_store,
        branch_store=branch_store,
        costeer_max_rounds=1,
        llm_adapter=llm_adapter,
        memory_service=memory_service,
    )
    loop_engine = LoopEngine(
        config=LoopEngineConfig(
            exception_archive_root=artifact_root,
            layer0_n_candidates=1,
            layer0_k_forward=1,
        ),
        planner=Planner(PlannerConfig(use_llm_planning=False)),
        exploration_manager=ExplorationManager(
            ExplorationManagerConfig(),
            scheduler=scheduler,
            pruner=pruner,
            merger=merger,
            llm_adapter=llm_adapter,
            virtual_evaluator=virtual_evaluator,
        ),
        memory_service=memory_service,
        step_executor=step_executor,
        run_store=sqlite_store,
        event_store=sqlite_store,
        scheduler=scheduler,
    )
    resume_manager = ResumeManager(
        checkpoint_store=checkpoint_store,
        workspace_manager=workspace_manager,
    )
    run_service = RunService(
        config=RunServiceConfig(default_scenario="data_science"),
        loop_engine=loop_engine,
        run_store=sqlite_store,
        resume_manager=resume_manager,
        branch_store=branch_store,
    )
    log.info("      Runtime wired.")

    # ---------------------------------------------------------------------- #
    # 4. 创建并执行 run
    # ---------------------------------------------------------------------- #
    log.info("[4/4] Starting data_science run (run_id=%s)...", run_id)
    print()

    session = run_service.create_run(
        run_id=run_id,
        task_summary=TASK_SUMMARY,
        scenario="data_science",
        entry_input={
            "task_summary": TASK_SUMMARY,
            "max_loops": max_loops,
        },
    )
    log.info("      Run session created: %s (status=%s)", session.run_id, session.status)

    try:
        loop_ctx = run_service.start_run(
            run_id=run_id,
            task_summary=TASK_SUMMARY,
            loops_per_call=max_loops,
        )
    except RuntimeError as exc:
        log.error("Run failed: %s", exc)
        summary = {"scenario": "data_science", "passed": False, "iterations": 0, "artifact_path": ""}
        print(json.dumps(summary))
        sys.exit(1)

    print()
    log.info("=== Run Complete ===")
    final_session = run_service.get_run(run_id)
    log.info("Status     : %s", final_session.status if final_session else "unknown")
    log.info("Iterations : %d", loop_ctx.loop_state.iteration if loop_ctx.loop_state else -1)

    workspace_path = Path(workspace_root) / run_id
    result_files = list(workspace_path.rglob("metrics.json")) if workspace_path.exists() else []
    if result_files:
        print()
        log.info("Execution metrics:")
        for metrics_file in result_files:
            try:
                metrics_data = json.loads(metrics_file.read_text(encoding="utf-8"))
                log.info("  File : %s", metrics_file)
                for key, value in metrics_data.items():
                    log.info("  %-12s: %s", key, value)
            except Exception as exc:  # noqa: BLE001
                log.warning("  Could not parse %s: %s", metrics_file, exc)
    else:
        log.info("No metrics.json found in workspace (check %s)", workspace_path)

    generated_files = list(workspace_path.rglob("pipeline.py")) if workspace_path.exists() else []
    if generated_files:
        print()
        log.info("Generated code:")
        print("-" * 60)
        print(generated_files[0].read_text(encoding="utf-8"))
        print("-" * 60)
    else:
        log.info("No pipeline.py found in workspace (check %s)", workspace_path)

    print()
    log.info("Workspace : %s", workspace_root)
    log.info("SQLite    : %s", sqlite_path)

    summary = {
        "scenario": "data_science",
        "passed": True,
        "iterations": loop_ctx.loop_state.iteration if loop_ctx.loop_state else 0,
        "artifact_path": str(workspace_path),
    }
    print(json.dumps(summary))
    log.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
