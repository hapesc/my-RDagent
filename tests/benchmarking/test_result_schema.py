from __future__ import annotations

import importlib
import importlib.util
import sys
from unittest.mock import patch


def test_benchmark_dependency_langsmith_is_available() -> None:
    assert importlib.util.find_spec("langsmith") is not None


def test_benchmark_dependency_langchain_openai_is_available() -> None:
    assert importlib.util.find_spec("langchain_openai") is not None


def test_eval_collection_gate_only_ignores_legacy_evals_without_deepeval() -> None:
    sys.modules.pop("tests.conftest", None)
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name: str):
        if name == "deepeval":
            return None
        return original_find_spec(name)

    with patch("importlib.util.find_spec", side_effect=fake_find_spec):
        module = importlib.import_module("tests.conftest")

    assert getattr(module, "collect_ignore_glob", []) == ["evals/*"]
