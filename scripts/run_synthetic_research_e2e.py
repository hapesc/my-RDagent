from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TASK_SUMMARY = "investigate the effect of learning rate on transformer fine-tuning convergence"
REFERENCE_TOPICS = [
    "learning rate scheduling",
    "transformer architecture",
    "fine-tuning best practices",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("synthetic_research_e2e")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Synthetic Research E2E Integration Test: OpenCode Kimi K2.5")
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

    log.info("=== Synthetic Research E2E Integration Test ===")
    log.info("Task      : %s", TASK_SUMMARY)
    log.info("Topics    : %s", REFERENCE_TOPICS)
    log.info("Model     : %s", TEST_LLM_DISPLAY_NAME)
    log.info("Max loops : %d", max_loops)
    print()

    from llm import LLMAdapter, LLMAdapterConfig

    log.info("[1/4] Building LLM adapter (%s)...", TEST_LLM_DISPLAY_NAME)
    provider = build_test_llm_provider(api_key)
    llm_adapter = LLMAdapter(
        provider=provider,
        config=LLMAdapterConfig(max_retries=2),
    )
    log.info("      LLM adapter ready.")

    from plugins import PluginRegistry
    from scenarios.synthetic_research.plugin import (
        SyntheticResearchConfig,
        build_synthetic_research_bundle,
    )

    run_id = f"synthetic-research-e2e-{uuid.uuid4().hex[:8]}"
    workspace_root = f"/tmp/rd_agent_synthetic_research_e2e/{run_id}"
    artifact_root = f"/tmp/rd_agent_synthetic_research_e2e_artifacts/{run_id}"
    sqlite_path = f"/tmp/rd_agent_synthetic_research_e2e_{run_id}.db"

    log.info("[2/4] Building synthetic_research plugin bundle...")
    synthetic_config = SyntheticResearchConfig(workspace_root=workspace_root)
    synthetic_bundle = build_synthetic_research_bundle(
        config=synthetic_config,
        llm_adapter=llm_adapter,
    )

    plugin_registry = PluginRegistry()
    plugin_registry.register("synthetic_research", lambda: synthetic_bundle)
    log.info("      Plugin bundle ready.")

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
        plugin_bundle=synthetic_bundle,
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
        config=RunServiceConfig(default_scenario="synthetic_research"),
        loop_engine=loop_engine,
        run_store=sqlite_store,
        resume_manager=resume_manager,
        branch_store=branch_store,
    )
    log.info("      Runtime wired.")

    log.info("[4/4] Starting synthetic_research run (run_id=%s)...", run_id)
    print()

    session = run_service.create_run(
        run_id=run_id,
        task_summary=TASK_SUMMARY,
        scenario="synthetic_research",
        entry_input={
            "task_summary": TASK_SUMMARY,
            "reference_topics": REFERENCE_TOPICS,
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
        summary = {"scenario": "synthetic_research", "passed": False, "iterations": 0, "artifact_path": ""}
        print(json.dumps(summary))
        sys.exit(1)

    print()
    log.info("=== Run Complete ===")
    final_session = run_service.get_run(run_id)
    log.info("Status     : %s", final_session.status if final_session else "unknown")
    log.info("Iterations : %d", loop_ctx.loop_state.iteration if loop_ctx.loop_state else -1)

    workspace_path = Path(workspace_root) / run_id
    summary_files = list(workspace_path.rglob("research_summary.json")) if workspace_path.exists() else []
    if summary_files:
        print()
        log.info("Generated research findings:")
        for summary_file in summary_files:
            try:
                payload = json.loads(summary_file.read_text(encoding="utf-8"))
                log.info("  File                : %s", summary_file)
                log.info("  task_summary        : %s", payload.get("task_summary"))
                log.info("  topic_count         : %s", payload.get("topic_count"))
                log.info("  synthesized_summary : %s", payload.get("synthesized_summary"))
                findings = payload.get("synthesized_findings", [])
                if isinstance(findings, list):
                    for idx, finding in enumerate(findings, start=1):
                        log.info("  finding_%d           : %s", idx, finding)
            except Exception as exc:
                log.warning("  Could not parse %s: %s", summary_file, exc)
    else:
        log.info("No research_summary.json found in workspace (check %s)", workspace_path)

    brief_files = list(workspace_path.rglob("research_brief.md")) if workspace_path.exists() else []
    if brief_files:
        print()
        log.info("Generated research brief:")
        print("-" * 60)
        print(brief_files[0].read_text(encoding="utf-8"))
        print("-" * 60)

    print()
    log.info("Workspace : %s", workspace_root)
    log.info("SQLite    : %s", sqlite_path)

    summary = {
        "scenario": "synthetic_research",
        "passed": True,
        "iterations": loop_ctx.loop_state.iteration if loop_ctx.loop_state else 0,
        "artifact_path": str(workspace_path),
    }
    print(json.dumps(summary))
    log.info("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
