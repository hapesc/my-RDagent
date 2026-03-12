"""Runtime assembly for CLI and app entrypoints."""

from __future__ import annotations

import json
from dataclasses import dataclass

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
from data_models import DebugConfig
from evaluation_service import EvaluationService, EvaluationServiceConfig
from exploration_manager import ExplorationManager, ExplorationManagerConfig
from exploration_manager.merging import TraceMerger
from exploration_manager.pruning import BranchPruner
from exploration_manager.reward import RewardCalculator
from exploration_manager.scheduler import MCTSScheduler
from llm import LLMAdapter
from llm.providers.litellm_provider import LiteLLMProvider
from memory_service import MemoryService, MemoryServiceConfig
from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.interaction_kernel import InteractionKernel
from planner import Planner, PlannerConfig
from plugins import PluginRegistry, build_default_registry
from scenarios import (
    DataScienceV1Config,
    QuantConfig,
    SyntheticResearchConfig,
    default_data_science_step_overrides,
    default_synthetic_research_step_overrides,
)
from service_contracts import (
    ModelSelectorConfig,
    RunningStepConfig,
    StepOverrideConfig,
    resolve_step_override_config,
)

from .config import REAL_PROVIDER_SAFE_PROFILE, AppConfig, load_config, validate_runtime_guardrails


def _is_litellm_chatgpt_auth_eligible_model(model: str) -> bool:
    return model.startswith("chatgpt/") or model.startswith("gpt-")


@dataclass
class RuntimeContext:
    """Shared runtime context used by CLI commands."""

    config: AppConfig
    sqlite_store: SQLiteMetadataStore
    branch_store: BranchTraceStore
    checkpoint_store: FileCheckpointStore
    workspace_manager: WorkspaceManager
    planner: Planner
    exploration_manager: ExplorationManager
    memory_service: MemoryService
    evaluation_service: EvaluationService
    plugin_registry: PluginRegistry
    llm_adapter: LLMAdapter
    scheduler: MCTSScheduler
    reasoning_pipeline: ReasoningPipeline | None = None
    virtual_evaluator: VirtualEvaluator | None = None


@dataclass(frozen=True)
class ScenarioRuntimeProfile:
    effective_step_config: StepOverrideConfig
    guardrail_warnings: tuple[str, ...] = ()


class _ReasoningTraceStore:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory_service = memory_service

    def store(self, trace_record) -> None:
        payload = {
            "trace_id": trace_record.trace_id,
            "stages": trace_record.stages,
            "timestamp": trace_record.timestamp,
            "metadata": trace_record.metadata,
        }
        metadata = {
            "kind": "reasoning_trace",
            "trace_id": str(trace_record.trace_id),
            "scenario": str(trace_record.metadata.get("scenario", "")),
            "iteration": str(trace_record.metadata.get("iteration", "")),
        }
        self._memory_service.write_memory(json.dumps(payload, sort_keys=True), metadata)


def _create_llm_provider(config: AppConfig):
    if config.llm_provider == "litellm":
        model = config.llm_model
        api_key = config.llm_api_key or ""
        base_url = config.llm_base_url

        if not api_key:
            if _is_litellm_chatgpt_auth_eligible_model(model):
                if model.startswith("gpt-"):
                    model = f"chatgpt/{model}"
                base_url = None
            else:
                raise RuntimeError(
                    f"Unknown or missing LLM provider: '{config.llm_provider}'. "
                    "Set RD_AGENT_LLM_PROVIDER=litellm and provide RD_AGENT_LLM_API_KEY. "
                    "For LiteLLM ChatGPT auth, use an auth-eligible model such as chatgpt/... or gpt-*."
                )

        return LiteLLMProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
    raise RuntimeError(
        f"Unknown or missing LLM provider: '{config.llm_provider}'. "
        "Set RD_AGENT_LLM_PROVIDER=litellm and provide RD_AGENT_LLM_API_KEY. "
        "Supported providers: litellm"
    )


def _create_memory_service(config: AppConfig, llm_adapter: LLMAdapter) -> MemoryService:
    mem_config = MemoryServiceConfig(
        enable_hypothesis_storage=config.enable_hypothesis_storage,
    )
    if config.enable_hypothesis_storage:
        kernel = InteractionKernel()
        selector = HypothesisSelector(kernel, llm_adapter=llm_adapter)
        return MemoryService(mem_config, hypothesis_selector=selector, interaction_kernel=kernel)
    return MemoryService(mem_config)


def _effective_step_overrides(defaults: StepOverrideConfig, config: AppConfig) -> StepOverrideConfig:
    if not config.uses_real_llm_provider:
        return defaults
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.proposal.temperature,
            max_tokens=defaults.proposal.max_tokens,
            max_retries=1,
        ),
        coding=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.coding.temperature,
            max_tokens=defaults.coding.max_tokens,
            max_retries=1,
        ),
        running=RunningStepConfig(timeout_sec=config.sandbox_timeout_sec),
        feedback=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.feedback.temperature,
            max_tokens=defaults.feedback.max_tokens,
            max_retries=1,
        ),
    )


def build_real_provider_smoke_step_overrides(
    config: AppConfig,
    defaults: StepOverrideConfig,
) -> StepOverrideConfig:
    if not config.uses_real_llm_provider:
        return defaults
    return StepOverrideConfig(
        proposal=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.proposal.temperature,
            max_tokens=defaults.proposal.max_tokens,
            max_retries=REAL_PROVIDER_SAFE_PROFILE["max_retries"],
        ),
        coding=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.coding.temperature,
            max_tokens=defaults.coding.max_tokens,
            max_retries=REAL_PROVIDER_SAFE_PROFILE["max_retries"],
        ),
        running=RunningStepConfig(timeout_sec=REAL_PROVIDER_SAFE_PROFILE["sandbox_timeout_sec"]),
        feedback=ModelSelectorConfig(
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=defaults.feedback.temperature,
            max_tokens=defaults.feedback.max_tokens,
            max_retries=REAL_PROVIDER_SAFE_PROFILE["max_retries"],
        ),
    )


def resolve_scenario_runtime_profile(
    config: AppConfig,
    defaults: StepOverrideConfig,
    requested_step_overrides: StepOverrideConfig | None = None,
) -> ScenarioRuntimeProfile:
    effective_step_config = resolve_step_override_config(defaults, requested_step_overrides)
    warnings = validate_runtime_guardrails(
        config,
        step_max_retries=[
            ("proposal", effective_step_config.proposal.max_retries),
            ("coding", effective_step_config.coding.max_retries),
            ("feedback", effective_step_config.feedback.max_retries),
        ],
        running_timeout_sec=effective_step_config.running.timeout_sec,
    )
    return ScenarioRuntimeProfile(
        effective_step_config=effective_step_config,
        guardrail_warnings=tuple(config.real_provider_warnings + warnings),
    )


def build_runtime(config_path: str | None = None, quant_config: QuantConfig | None = None) -> RuntimeContext:
    config = load_config(config_path=config_path)
    data_science_defaults = _effective_step_overrides(
        default_data_science_step_overrides(config.sandbox_timeout_sec),
        config,
    )
    synthetic_research_defaults = _effective_step_overrides(
        default_synthetic_research_step_overrides(config.sandbox_timeout_sec),
        config,
    )
    llm_provider = _create_llm_provider(config)
    llm_adapter = LLMAdapter(llm_provider)
    scheduler = MCTSScheduler(
        c_puct=config.mcts_c_puct,
        reward_calculator=RewardCalculator(mode=config.mcts_reward_mode),
    )
    pruner = BranchPruner(relative_threshold=config.prune_threshold)
    merger = TraceMerger(llm_adapter)
    sqlite_store = SQLiteMetadataStore(SQLiteStoreConfig(sqlite_path=config.sqlite_path))
    branch_store = BranchTraceStore(BranchTraceStoreConfig(sqlite_path=config.sqlite_path))
    checkpoint_store = FileCheckpointStore(CheckpointStoreConfig(root_dir=f"{config.artifact_root}/checkpoints"))
    workspace_manager = WorkspaceManager(
        WorkspaceManagerConfig(root_dir=config.workspace_root),
        checkpoint_store=checkpoint_store,
    )
    memory_service = _create_memory_service(config, llm_adapter)
    reasoning_pipeline = ReasoningPipeline(
        llm_adapter,
        trace_store=_ReasoningTraceStore(memory_service),
    )
    virtual_evaluator = VirtualEvaluator(
        llm_adapter,
        n_candidates=config.layer0_n_candidates,
        k_forward=config.layer0_k_forward,
        reasoning_pipeline=reasoning_pipeline,
    )
    return RuntimeContext(
        config=config,
        sqlite_store=sqlite_store,
        branch_store=branch_store,
        checkpoint_store=checkpoint_store,
        workspace_manager=workspace_manager,
        planner=Planner(
            PlannerConfig(use_llm_planning=config.use_llm_planning),
            llm_adapter=llm_adapter if config.use_llm_planning else None,
        ),
        exploration_manager=ExplorationManager(
            ExplorationManagerConfig(),
            scheduler=scheduler,
            pruner=pruner,
            merger=merger,
            llm_adapter=llm_adapter,
            virtual_evaluator=virtual_evaluator,
        ),
        memory_service=memory_service,
        evaluation_service=EvaluationService(EvaluationServiceConfig()),
        plugin_registry=build_default_registry(
            DataScienceV1Config(
                workspace_root=config.workspace_root,
                trace_storage_path=config.trace_storage_path,
                allow_local_execution=config.allow_local_execution,
                default_step_overrides=data_science_defaults,
            ),
            SyntheticResearchConfig(
                workspace_root=config.workspace_root,
                default_step_overrides=synthetic_research_defaults,
            ),
            quant_config,
            llm_adapter=llm_adapter,
            reasoning_pipeline=reasoning_pipeline,
            virtual_evaluator=virtual_evaluator,
        ),
        llm_adapter=llm_adapter,
        scheduler=scheduler,
        reasoning_pipeline=reasoning_pipeline,
        virtual_evaluator=virtual_evaluator,
    )


def build_run_service(runtime: RuntimeContext, scenario: str) -> RunService:
    plugin_bundle = runtime.plugin_registry.create_bundle(scenario)
    debug_config = DebugConfig(
        debug_mode=runtime.config.debug_mode,
        sample_fraction=runtime.config.debug_sample_fraction,
        max_epochs=runtime.config.debug_max_epochs,
    )
    step_executor = StepExecutor(
        plugin_bundle=plugin_bundle,
        evaluation_service=runtime.evaluation_service,
        workspace_manager=runtime.workspace_manager,
        event_store=runtime.sqlite_store,
        branch_store=runtime.branch_store,
        costeer_max_rounds=runtime.config.costeer_max_rounds,
        llm_adapter=runtime.llm_adapter,
        memory_service=runtime.memory_service,
        debug_config=debug_config,
    )
    loop_engine = LoopEngine(
        config=LoopEngineConfig(
            exception_archive_root=runtime.config.artifact_root,
            layer0_n_candidates=runtime.config.layer0_n_candidates,
            layer0_k_forward=runtime.config.layer0_k_forward,
        ),
        planner=runtime.planner,
        exploration_manager=runtime.exploration_manager,
        memory_service=runtime.memory_service,
        step_executor=step_executor,
        run_store=runtime.sqlite_store,
        event_store=runtime.sqlite_store,
        scheduler=runtime.scheduler,
        evaluation_service=runtime.evaluation_service,
    )
    resume_manager = ResumeManager(
        checkpoint_store=runtime.checkpoint_store,
        workspace_manager=runtime.workspace_manager,
    )
    return RunService(
        config=RunServiceConfig(default_scenario=scenario),
        loop_engine=loop_engine,
        run_store=runtime.sqlite_store,
        resume_manager=resume_manager,
        branch_store=runtime.branch_store,
    )
