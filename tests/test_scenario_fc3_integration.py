from __future__ import annotations

from core.reasoning.pipeline import ReasoningPipeline
from core.reasoning.virtual_eval import VirtualEvaluator
from data_models import ContextPack, Plan
from llm.adapter import LLMAdapter, MockLLMProvider
from plugins.contracts import ProposalEngine, ScenarioContext
from scenarios.data_science.plugin import DataScienceProposalEngine, build_data_science_v1_bundle
from scenarios.synthetic_research.plugin import (
    SyntheticResearchProposalEngine,
    build_synthetic_research_bundle,
)
from service_contracts import StepOverrideConfig


def _make_adapter() -> LLMAdapter:
    return LLMAdapter(MockLLMProvider())


def _make_pipeline(adapter: LLMAdapter | None = None) -> ReasoningPipeline:
    llm_adapter = adapter or _make_adapter()
    return ReasoningPipeline(llm_adapter)


def _make_evaluator(
    adapter: LLMAdapter | None = None,
    n: int = 3,
    k: int = 1,
) -> VirtualEvaluator:
    llm_adapter = adapter or _make_adapter()
    return VirtualEvaluator(llm_adapter, n_candidates=n, k_forward=k)


def _make_scenario_context(
    scenario_name: str = "data_science",
    input_payload: dict | None = None,
) -> ScenarioContext:
    payload = {"loop_index": 0}
    if input_payload:
        payload.update(input_payload)
    return ScenarioContext(
        run_id="r-test",
        scenario_name=scenario_name,
        input_payload=payload,
        task_summary="test task",
        step_config=StepOverrideConfig(),
    )


def _base_inputs() -> tuple[ContextPack, list[str], Plan]:
    return ContextPack(), ["p0"], Plan(plan_id="plan-test")


def test_data_science_proposal_engine_virtual_evaluator_path() -> None:
    adapter = _make_adapter()
    evaluator = _make_evaluator(adapter, n=2, k=1)
    engine = DataScienceProposalEngine(adapter, virtual_evaluator=evaluator)

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose("", context, parent_ids, plan, _make_scenario_context("data_science"))

    assert proposal.proposal_id == "proposal-ds-fc3"
    assert proposal.summary.strip()
    assert proposal.constraints


def test_data_science_proposal_engine_reasoning_pipeline_only_path() -> None:
    adapter = _make_adapter()
    pipeline = _make_pipeline(adapter)
    engine = DataScienceProposalEngine(adapter, reasoning_pipeline=pipeline)

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose("", context, parent_ids, plan, _make_scenario_context("data_science"))

    assert proposal.proposal_id == "proposal-ds-fc3-pipeline"
    assert proposal.summary.strip()
    assert proposal.constraints


def test_data_science_proposal_engine_backward_compat_path() -> None:
    adapter = _make_adapter()
    engine = DataScienceProposalEngine(adapter)

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose("", context, parent_ids, plan, _make_scenario_context("data_science"))

    assert proposal.proposal_id == "proposal-ds-v1"
    assert proposal.summary.strip()


def test_synthetic_proposal_engine_virtual_evaluator_path() -> None:
    adapter = _make_adapter()
    evaluator = _make_evaluator(adapter, n=2, k=1)
    engine = SyntheticResearchProposalEngine(
        llm_adapter=adapter,
        virtual_evaluator=evaluator,
    )

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert proposal.proposal_id == "proposal-synthetic-fc3"
    assert proposal.summary.strip()
    assert proposal.constraints


def test_synthetic_proposal_engine_reasoning_pipeline_only_path() -> None:
    adapter = _make_adapter()
    pipeline = _make_pipeline(adapter)
    engine = SyntheticResearchProposalEngine(
        llm_adapter=adapter,
        reasoning_pipeline=pipeline,
    )

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert proposal.proposal_id == "proposal-synthetic-fc3-pipeline"
    assert proposal.summary.strip()
    assert proposal.constraints


def test_synthetic_proposal_engine_backward_compat_llm_path() -> None:
    adapter = _make_adapter()
    engine = SyntheticResearchProposalEngine(llm_adapter=adapter)

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert proposal.proposal_id == "proposal-llm"
    assert "synthetic_research" in proposal.constraints


def test_synthetic_proposal_engine_reasoning_service_fallback() -> None:
    engine = SyntheticResearchProposalEngine(llm_adapter=None)

    context, parent_ids, plan = _base_inputs()
    proposal = engine.propose(
        "fallback-task",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert proposal.proposal_id == "proposal-placeholder"
    assert proposal.summary == "fallback-task"


def test_build_data_science_bundle_accepts_fc3_components() -> None:
    adapter = _make_adapter()
    pipeline = _make_pipeline(adapter)
    evaluator = _make_evaluator(adapter, n=2, k=1)

    bundle = build_data_science_v1_bundle(
        llm_adapter=adapter,
        reasoning_pipeline=pipeline,
        virtual_evaluator=evaluator,
    )

    context, parent_ids, plan = _base_inputs()
    proposal = bundle.proposal_engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("data_science"),
    )

    assert proposal.proposal_id == "proposal-ds-fc3"


def test_build_synthetic_bundle_accepts_fc3_components() -> None:
    adapter = _make_adapter()
    pipeline = _make_pipeline(adapter)
    evaluator = _make_evaluator(adapter, n=2, k=1)

    bundle = build_synthetic_research_bundle(
        llm_adapter=adapter,
        reasoning_pipeline=pipeline,
        virtual_evaluator=evaluator,
    )

    context, parent_ids, plan = _base_inputs()
    proposal = bundle.proposal_engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert proposal.proposal_id == "proposal-synthetic-fc3"


def test_fc3_proposals_have_non_empty_summary_and_constraints() -> None:
    adapter = _make_adapter()
    context, parent_ids, plan = _base_inputs()

    ds_engine = DataScienceProposalEngine(adapter, reasoning_pipeline=_make_pipeline(adapter))
    ds_proposal = ds_engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("data_science"),
    )

    synthetic_engine = SyntheticResearchProposalEngine(
        llm_adapter=adapter,
        reasoning_pipeline=_make_pipeline(adapter),
    )
    synthetic_proposal = synthetic_engine.propose(
        "",
        context,
        parent_ids,
        plan,
        _make_scenario_context("synthetic_research"),
    )

    assert ds_proposal.summary.strip() and ds_proposal.constraints
    assert synthetic_proposal.summary.strip() and synthetic_proposal.constraints


def test_proposal_engine_protocol_compliance_with_fc3() -> None:
    adapter = _make_adapter()

    ds_engine = DataScienceProposalEngine(adapter, reasoning_pipeline=_make_pipeline(adapter))
    synthetic_engine = SyntheticResearchProposalEngine(
        llm_adapter=adapter,
        virtual_evaluator=_make_evaluator(adapter, n=2, k=1),
    )

    assert isinstance(ds_engine, ProposalEngine)
    assert isinstance(synthetic_engine, ProposalEngine)
