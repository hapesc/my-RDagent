from __future__ import annotations

from unittest.mock import patch

from llm import LLMAdapter, MockLLMProvider


class _CodegenReadyMockProvider(MockLLMProvider):
    def complete(self, prompt: str, model_config=None) -> str:
        prompt_lower = prompt.lower()
        if "## research proposal" in prompt_lower and "scenario: data_science" in prompt_lower:
            return (
                '{"artifact_id":"artifact-llm","description":"data science pipeline","location":"/tmp/rd_agent_workspace"}\n'
                "```python\n"
                "import json\n"
                "from pathlib import Path\n"
                "metrics = {'status': 'ok', 'accuracy': 0.91, 'row_count': 3, 'column_count': 3}\n"
                "Path('metrics.json').write_text(json.dumps(metrics), encoding='utf-8')\n"
                "print(json.dumps(metrics))\n"
                "```\n"
            )
        return super().complete(prompt, model_config=model_config)


def make_mock_llm_adapter() -> LLMAdapter:
    return LLMAdapter(provider=_CodegenReadyMockProvider())


def patch_runtime_llm_provider():
    return patch("app.runtime._create_llm_provider", return_value=MockLLMProvider())
