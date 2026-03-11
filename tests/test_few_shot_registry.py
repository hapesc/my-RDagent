from __future__ import annotations

from llm.codegen.few_shot import get_few_shot_examples


def test_registry_returns_examples_for_known_scenario() -> None:
    examples = get_few_shot_examples("quant")
    assert len(examples) >= 2
    for example in examples:
        assert "task" in example
        assert "artifact" in example
        assert "artifact_type" in example


def test_registry_returns_empty_for_unknown_scenario() -> None:
    assert get_few_shot_examples("nonexistent") == []


def test_quant_examples_are_code_type() -> None:
    for example in get_few_shot_examples("quant"):
        assert example["artifact_type"] == "code"
        assert "def compute_factor" in example["artifact"]


def test_quant_examples_pass_compile_check() -> None:
    for example in get_few_shot_examples("quant"):
        compile(example["artifact"], "<few-shot>", "exec")


def test_data_science_examples_are_code_type() -> None:
    for example in get_few_shot_examples("data_science"):
        assert example["artifact_type"] == "code"
        assert "metrics" in example["artifact"].lower()


def test_synthetic_examples_are_structured_text_type() -> None:
    for example in get_few_shot_examples("synthetic_research"):
        assert example["artifact_type"] == "structured_text"
        assert "## Findings" in example["artifact"] or "## Results" in example["artifact"]


def test_synthetic_examples_contain_findings_structure() -> None:
    for example in get_few_shot_examples("synthetic_research"):
        lines = example["artifact"].strip().splitlines()
        has_structure = any(line.strip().startswith(("1.", "2.", "-", "*")) for line in lines)
        assert has_structure, "synthetic example must show structured findings"
