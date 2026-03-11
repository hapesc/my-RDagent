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
    raw = '```json\n{"artifact_id":"v1","artifact":"def foo():\\n    return 1"}\n```'
    result = extract_code_and_metadata(raw)
    assert result.code == "def foo():\n    return 1"
    assert result.metadata["artifact_id"] == "v1"


def test_extracts_artifact_field_from_truncated_json_payload() -> None:
    raw = '```json\n{"artifact_id":"v1","artifact":"## Findings\\n\\n1. Value increased by 15%\\n2. Latency fell by 8%'
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


def test_extracts_code_from_python_code_json_key() -> None:
    raw = '{"python_code": "import pandas as pd\\n\\ndef compute_factor(df):\\n    return df"}'
    result = extract_code_and_metadata(raw)
    assert "def compute_factor" in result.code
    assert result.source == "json_plus_block"


def test_extracts_code_from_code_json_key() -> None:
    raw = '{"code": "def foo():\\n    return 1", "description": "a function"}'
    result = extract_code_and_metadata(raw)
    assert result.code == "def foo():\n    return 1"


def test_truncated_json_with_python_code_key() -> None:
    raw = '{"python_code": "import pandas as pd\\ndef compute(df):\\n    return df[\\"close\\"].pct_change()\\n'
    result = extract_code_and_metadata(raw)
    assert "import pandas" in result.code
    assert "pct_change" in result.code


def test_truncated_json_with_code_key() -> None:
    raw = '{"description": "momentum factor", "code": "import numpy as np\\ndef factor(df):\\n    return df[\\"vol'
    result = extract_code_and_metadata(raw)
    assert "import numpy" in result.code
    assert "def factor" in result.code


def test_truncated_json_picks_longest_code_value() -> None:
    raw = '{"description": "momentum", "python_code": "import pandas as pd\\ndef big_func():\\n    return 42", "code": "x=1'
    result = extract_code_and_metadata(raw)
    assert "big_func" in result.code


def test_truncated_json_handles_escaped_chars() -> None:
    raw = '{"python_code": "line1\\nline2\\tindented\\\\backslash\\"quoted\\""}'
    result = extract_code_and_metadata(raw)
    assert "line1\nline2" in result.code
    assert "\tindented" in result.code
    assert "\\backslash" in result.code
    assert '"quoted"' in result.code


def test_truncated_json_empty_value_returns_none() -> None:
    raw = '{"python_code": ""}'
    result = extract_code_and_metadata(raw)
    assert result.code == ""
    assert result.source == "raw_fallback"


def test_strips_fenced_wrapper_from_json_value() -> None:
    raw = '{"implementation": "```python\\nimport pandas as pd\\ndef compute_factor(df):\\n    return df\\n```"}'
    result = extract_code_and_metadata(raw)
    assert not result.code.startswith("```")
    assert "import pandas" in result.code
    assert "def compute_factor" in result.code


def test_extracts_python_function_key() -> None:
    raw = '{"python_function": "import pandas as pd\\ndef compute_factor(df):\\n    return df"}'
    result = extract_code_and_metadata(raw)
    assert "def compute_factor" in result.code
