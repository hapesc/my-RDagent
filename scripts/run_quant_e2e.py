"""
End-to-end quant integration test: real data (yfinance) + OpenCode Kimi K2.5
走完整 loop engine 一次循环。

用法:
    export OPENCODE_API=<your_key>
    python scripts/run_quant_e2e.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
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
TICKERS = ["QQQ", "VOO", "GOOG", "GLD", "SLV", "SCHD"]
START_DATE = "2022-01-01"
END_DATE = "2024-12-31"
TASK_SUMMARY = (
    "Mine a single alpha factor using price/volume data for QQQ, VOO, GOOG, GLD, SLV, SCHD. "
    "The factor should predict next-day returns. Avoid look-ahead bias."
)

# --------------------------------------------------------------------------- #
# 日志
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("quant_e2e")

# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Quant E2E Integration Test: real data (yfinance) + OpenCode Kimi K2.5"
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
    from scripts.real_test_llm import TEST_LLM_DISPLAY_NAME, build_test_llm_provider, get_test_llm_api_key

    api_key = get_test_llm_api_key()
    if not api_key:
        log.error("No OpenCode-compatible API key is set. Export OPENCODE_API or RD_AGENT_LLM_API_KEY.")
        sys.exit(1)

    log.info("=== Quant E2E Integration Test ===")
    log.info("Tickers   : %s", TICKERS)
    log.info("Date range: %s → %s", START_DATE, END_DATE)
    log.info("Model     : %s", TEST_LLM_DISPLAY_NAME)
    log.info("Max loops : %d", max_loops)
    print()

    # ---------------------------------------------------------------------- #
    # 1. 构建 LLM adapter
    # ---------------------------------------------------------------------- #
    from llm import LLMAdapter, LLMAdapterConfig

    log.info("[1/5] Building LLM adapter (%s)...", TEST_LLM_DISPLAY_NAME)
    provider = build_test_llm_provider(api_key)
    llm_adapter = LLMAdapter(
        provider=provider,
        config=LLMAdapterConfig(max_retries=2),
    )
    log.info("      LLM adapter ready.")

    # ---------------------------------------------------------------------- #
    # 2. 构建 YFinance data provider
    # ---------------------------------------------------------------------- #
    from scenarios.quant.data_provider import YFinanceDataProvider

    log.info("[2/5] Fetching OHLCV data via yfinance...")
    data_provider = YFinanceDataProvider(
        tickers=TICKERS,
        start=START_DATE,
        end=END_DATE,
    )
    # 提前验证数据可以正常拉取
    sample_df = data_provider.load()
    log.info(
        "      Data fetched: %d rows, %d tickers, date range %s → %s",
        len(sample_df),
        sample_df["stock_id"].nunique(),
        str(sample_df["date"].min())[:10],
        str(sample_df["date"].max())[:10],
    )
    print()

    # ---------------------------------------------------------------------- #
    # 3. 构建 QuantConfig + plugin registry（直接注入，绕过 build_runtime env
    #    依赖，保持脚本自包含）
    # ---------------------------------------------------------------------- #
    from plugins import PluginRegistry
    from scenarios.quant.data_provider import YFinanceDataProvider
    from scenarios.quant.plugin import QuantConfig, build_quant_bundle

    RUN_ID = f"quant-e2e-{uuid.uuid4().hex[:8]}"
    WORKSPACE_ROOT = f"/tmp/rd_agent_quant_e2e/{RUN_ID}"
    ARTIFACT_ROOT = f"/tmp/rd_agent_quant_e2e_artifacts/{RUN_ID}"
    SQLITE_PATH = f"/tmp/rd_agent_quant_e2e_{RUN_ID}.db"

    log.info("[3/5] Building quant plugin bundle...")
    quant_config = QuantConfig(
        workspace_root=WORKSPACE_ROOT,
        n_stocks=len(TICKERS),
        n_days=len(sample_df) // len(TICKERS),
        data_provider=data_provider,
    )
    quant_bundle = build_quant_bundle(
        config=quant_config,
        llm_adapter=llm_adapter,
    )

    plugin_registry = PluginRegistry()
    plugin_registry.register("quant", lambda: quant_bundle)
    log.info("      Plugin bundle ready.")

    # ---------------------------------------------------------------------- #
    # 4. 构建 runtime 依赖（loop engine, run service）
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

    log.info("[4/5] Wiring runtime components...")

    sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=SQLITE_PATH))
    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=SQLITE_PATH))
    checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=f"{ARTIFACT_ROOT}/checkpoints"))
    workspace_manager = WorkspaceManager(
        WorkspaceManagerConfig(root_dir=WORKSPACE_ROOT),
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
        plugin_bundle=quant_bundle,
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
            exception_archive_root=ARTIFACT_ROOT,
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
        config=RunServiceConfig(default_scenario="quant"),
        loop_engine=loop_engine,
        run_store=sqlite_store,
        resume_manager=resume_manager,
        branch_store=branch_store,
    )
    log.info("      Runtime wired.")

    # ---------------------------------------------------------------------- #
    # 5. 创建并执行 run
    # ---------------------------------------------------------------------- #
    log.info("[5/5] Starting quant run (run_id=%s)...", RUN_ID)
    print()

    session = run_service.create_run(
        run_id=RUN_ID,
        task_summary=TASK_SUMMARY,
        scenario="quant",
        entry_input={
            "task_summary": TASK_SUMMARY,
            "tickers": TICKERS,
            "max_loops": max_loops,
        },
    )
    log.info("      Run session created: %s (status=%s)", session.run_id, session.status)

    try:
        loop_ctx = run_service.start_run(
            run_id=RUN_ID,
            task_summary=TASK_SUMMARY,
            loops_per_call=max_loops,
        )
    except RuntimeError as exc:
        log.error("Run failed: %s", exc)
        summary = {"scenario": "quant", "passed": False, "iterations": 0, "artifact_path": ""}
        print(json.dumps(summary))
        sys.exit(1)

    # ---------------------------------------------------------------------- #
    # 结果汇总
    # ---------------------------------------------------------------------- #
    print()
    log.info("=== Run Complete ===")
    final_session = run_service.get_run(RUN_ID)
    log.info("Status     : %s", final_session.status if final_session else "unknown")
    log.info("Iterations : %d", loop_ctx.loop_state.iteration if loop_ctx.loop_state else "?")

    # 打印 backtest 结果（如果 workspace 里有 result.json）
    workspace_path = Path(WORKSPACE_ROOT) / RUN_ID
    result_files = list(workspace_path.rglob("result.json")) if workspace_path.exists() else []
    if result_files:
        print()
        log.info("Backtest results:")
        for rf in result_files:
            try:
                result_data = json.loads(rf.read_text())
                metrics = result_data.get("metrics", result_data)
                log.info("  File : %s", rf)
                for k, v in metrics.items():
                    if isinstance(v, (int, float)) and v is not None:
                        log.info("  %-12s: %s", k, f"{v:.4f}" if isinstance(v, float) else v)
            except Exception as e:
                log.warning("  Could not parse %s: %s", rf, e)
    else:
        log.info("No result.json found in workspace (check %s)", workspace_path)

    # 打印 factor.py（如果存在）
    factor_files = list(workspace_path.rglob("factor.py")) if workspace_path.exists() else []
    if factor_files:
        print()
        log.info("Generated factor code:")
        print("-" * 60)
        print(factor_files[0].read_text())
        print("-" * 60)

    print()
    log.info("Workspace : %s", WORKSPACE_ROOT)
    log.info("SQLite    : %s", SQLITE_PATH)

    summary = {
        "scenario": "quant",
        "passed": True,
        "iterations": loop_ctx.loop_state.iteration if loop_ctx.loop_state else 0,
        "artifact_path": str(workspace_path),
    }
    print(json.dumps(summary))
    log.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
