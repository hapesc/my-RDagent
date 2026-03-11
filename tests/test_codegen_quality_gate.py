from __future__ import annotations

from llm.codegen.quality_gate import CodegenQualityGate


def test_gate_passes_clean_code() -> None:
    result = CodegenQualityGate(scenario="quant").evaluate(
        raw_output='{"artifact_id":"v1"}\n```python\ndef compute_factor(df):\n    return df\n```'
    )
    assert result.passed is True


def test_gate_rejects_syntax_error() -> None:
    result = CodegenQualityGate(scenario="quant").evaluate(raw_output="```python\ndef compute_factor(df\n```")
    assert result.passed is False
    assert any("compile" in reason.lower() for reason in result.reasons)


def test_gate_rejects_placeholder() -> None:
    result = CodegenQualityGate(scenario="data_science").evaluate(
        raw_output="```python\n# TODO: implement pipeline\npass\n```"
    )
    assert result.passed is False
    assert any("placeholder" in reason.lower() for reason in result.reasons)


def test_gate_rejects_forbidden_import_for_quant() -> None:
    result = CodegenQualityGate(scenario="quant").evaluate(
        raw_output="```python\nimport os\ndef compute_factor(df):\n    return df\n```"
    )
    assert result.passed is False


def test_gate_rejects_missing_signature_for_quant() -> None:
    result = CodegenQualityGate(scenario="quant").evaluate(raw_output="```python\ndef my_func(df):\n    pass\n```")
    assert result.passed is False
    assert any("compute_factor" in reason for reason in result.reasons)


def test_gate_returns_extracted_code_on_pass() -> None:
    result = CodegenQualityGate(scenario="quant").evaluate(
        raw_output="```python\nimport pandas as pd\ndef compute_factor(df):\n    return df\n```"
    )
    assert result.passed
    assert result.extracted_code is not None
    assert "compute_factor" in result.extracted_code


def test_gate_passes_structured_text_with_findings() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "## Findings\n"
            "1. Temperature increased by 0.8C per decade.\n"
            "2. CO2 correlation is 0.95.\n\n"
            "## Methodology\n"
            "- Linear regression on annual anomalies.\n"
        )
    )
    assert result.passed is True
    assert result.extracted_code is not None


def test_gate_rejects_empty_structured_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(raw_output="")
    assert result.passed is False


def test_gate_rejects_too_short_structured_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(raw_output="Some results.")
    assert result.passed is False
    assert any("length" in reason.lower() or "short" in reason.lower() for reason in result.reasons)


def test_gate_rejects_placeholder_structured_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output="## Findings\n1. TODO: fill in results\n2. TBD\n\n## Conclusion\nPlaceholder."
    )
    assert result.passed is False
    assert any("placeholder" in reason.lower() for reason in result.reasons)


def test_gate_rejects_unstructured_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "The analysis shows some interesting trends in the data. "
            "We looked at several variables and found that some were correlated. "
            "Further investigation is needed to draw conclusions."
        )
    )
    assert result.passed is False
    assert any("structure" in reason.lower() for reason in result.reasons)


def test_gate_rejects_task_restatement() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "## Task\nThe task is to analyze temperature trends.\n\n## Approach\nWe will analyze temperature trends."
        )
    )
    assert result.passed is False


def test_gate_rejects_well_formatted_but_vacuous_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "## Findings\n"
            "1. The analysis reveals several interesting patterns across multiple dimensions of the dataset "
            "that warrant further investigation and deeper exploration.\n"
            "2. Various factors appear to contribute to the observed outcomes in complex and multifaceted ways "
            "that suggest the need for additional research.\n"
            "3. The results indicate that there are meaningful relationships between the variables studied, "
            "though the precise nature of these relationships requires more thorough examination.\n\n"
            "## Conclusion\n"
            "Further investigation is recommended to fully understand the implications of these findings."
        )
    )
    assert result.passed is False
    assert any(
        "substance" in reason.lower() or "quantitative" in reason.lower() or "hedging" in reason.lower()
        for reason in result.reasons
    )


def test_gate_rejects_hedging_heavy_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "## Results\n"
            "1. It appears that some trends may possibly exist in the data.\n"
            "2. It seems likely that certain variables might be somewhat correlated.\n"
            "3. There could potentially be an effect, though it is unclear.\n\n"
            "## Discussion\n"
            "These preliminary observations suggest that further analysis would probably be needed."
        )
    )
    assert result.passed is False


def test_gate_passes_text_with_quantitative_findings() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "## Findings\n"
            "1. Global mean temperature anomaly increased by 0.18°C per decade from 1970-2020 (R²=0.87).\n"
            "2. The sharpest inflection point occurred in 1976, with a 0.3°C step change.\n"
            "3. CO2 concentration shows a Pearson correlation of 0.95 with temperature anomaly.\n\n"
            "## Methodology\n"
            "- Linear regression on annual anomaly data from 1950-2020.\n"
        )
    )
    assert result.passed is True


def test_gate_passes_fenced_markdown_structured_text() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "```markdown\n"
            "## Findings\n"
            "1. Accuracy improved by 15%.\n"
            "2. Latency fell by 8%.\n\n"
            "## Methodology\n"
            "- Compared baseline and reranked runs.\n\n"
            "## Conclusion\n"
            "- The trade-off is favorable.\n"
            "```"
        )
    )
    assert result.passed is True


def test_gate_passes_structured_text_stored_in_json_artifact_field() -> None:
    result = CodegenQualityGate(scenario="synthetic_research").evaluate(
        raw_output=(
            "```json\n"
            '{"artifact_id":"report_v1","artifact":"## Findings\\n\\n1. Accuracy improved by 15%.\\n'
            "2. Latency fell by 8%.\\n\\n## Methodology\\n\\n- Compared baseline and reranked runs."
            '\\n\\n## Conclusion\\n\\n- The trade-off is favorable."}\n'
            "```"
        )
    )
    assert result.passed is True
