from __future__ import annotations

from benchmarking.evaluators.criteria import (
    FEEDBACK_ACTIONABILITY_CRITERIA,
    HYPOTHESIS_FEASIBILITY_CRITERIA,
    HYPOTHESIS_SPECIFICITY_CRITERIA,
    REPORT_COHERENCE_CRITERIA,
    REPORT_DEPTH_CRITERIA,
    REPORT_FAITHFULNESS_CRITERIA,
    build_hypothesis_feasibility_criteria,
)


def test_criteria_constants_exist() -> None:
    assert HYPOTHESIS_SPECIFICITY_CRITERIA
    assert HYPOTHESIS_FEASIBILITY_CRITERIA
    assert FEEDBACK_ACTIONABILITY_CRITERIA
    assert REPORT_DEPTH_CRITERIA
    assert REPORT_COHERENCE_CRITERIA
    assert REPORT_FAITHFULNESS_CRITERIA


def test_criteria_strings_preserve_expected_labels() -> None:
    assert "CONCRETENESS" in HYPOTHESIS_SPECIFICITY_CRITERIA
    assert "RESOURCE FEASIBILITY" in HYPOTHESIS_FEASIBILITY_CRITERIA
    assert "FIX SUGGESTION" in FEEDBACK_ACTIONABILITY_CRITERIA
    assert "CAUSAL REASONING" in REPORT_DEPTH_CRITERIA
    assert "FLOW" in REPORT_COHERENCE_CRITERIA


def test_faithfulness_requires_bounded_evidence_or_reference_facts() -> None:
    lowered = REPORT_FAITHFULNESS_CRITERIA.lower()
    assert "reference fact" in lowered or "reference facts" in lowered
    assert "bounded evidence" in lowered or "bounded by the provided evidence" in lowered


def test_feasibility_builder_adds_scenario_specific_constraints() -> None:
    quant = build_hypothesis_feasibility_criteria("quant").lower()
    data_science = build_hypothesis_feasibility_criteria("data_science").lower()

    assert "ohlcv" in quant
    assert "metrics.json" in data_science
