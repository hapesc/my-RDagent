from __future__ import annotations

from hypothesis import given, strategies as st

from llm.codegen.extractors import extract_code_and_metadata, extract_code_block


def test_extracts_fenced_python_block() -> None:
    raw = 'Some text\n```python\nprint("hello")\n```\nMore text'
    assert extract_code_block(raw) == 'print("hello")'


def test_extracts_unfenced_python_block() -> None:
    raw = '```\nimport pandas as pd\ndf = pd.read_csv("x.csv")\n```'
    result = extract_code_block(raw)
    assert result is not None
    assert "import pandas" in result


def test_extracts_json_then_code() -> None:
    raw = '{"artifact_id": "v1"}\n```python\ndef foo(): pass\n```'
    result = extract_code_and_metadata(raw)
    assert result.code == "def foo(): pass"
    assert result.metadata["artifact_id"] == "v1"


def test_extracts_artifact_field_from_json_payload() -> None:
    raw = (
        '```json\n'
        '{"artifact_id":"v1","artifact":"def foo():\\n    return 1"}\n'
        '```'
    )
    result = extract_code_and_metadata(raw)
    assert result.code == "def foo():\n    return 1"
    assert result.metadata["artifact_id"] == "v1"


def test_extracts_artifact_field_from_truncated_json_payload() -> None:
    raw = (
        '```json\n'
        '{"artifact_id":"v1","artifact":"## Findings\\n\\n1. Value increased by 15%\\n2. Latency fell by 8%'
    )
    result = extract_code_and_metadata(raw)
    assert result.code.startswith("## Findings")
    assert "15%" in result.code


def test_truncated_code_returns_best_effort_extraction() -> None:
    raw = "```python\ndef foo():\n    return"
    result = extract_code_block(raw)
    assert result is not None
    assert "def foo():" in result


def test_no_code_block_returns_none() -> None:
    raw = "Just plain text with no code"
    assert extract_code_block(raw) is None


@given(code=st.text(min_size=1, max_size=500))
def test_extract_never_crashes(code: str) -> None:
    extract_code_block(f"```python\n{code}\n```")


@given(code=st.from_regex(r"def [a-z_]+\([a-z_]*\):\n    return \d+", fullmatch=True))
def test_valid_function_always_extracted(code: str) -> None:
    raw = f"```python\n{code}\n```"
    result = extract_code_block(raw)
    assert result is not None
    assert "def " in result
