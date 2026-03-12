from __future__ import annotations

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def tmp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mock_llm() -> object:
    class MockLLM:
        def complete(self, prompt: str, system: str | None = None) -> str:
            return "mock response"

        def extract_code(self, text: str) -> str:
            return "print('mock')"

    return MockLLM()


@pytest.fixture
def mock_storage(tmp_dir: str) -> str:
    return tmp_dir
