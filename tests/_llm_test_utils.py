from __future__ import annotations

from unittest.mock import patch

from llm import LLMAdapter, MockLLMProvider


class _CodegenReadyMockProvider(MockLLMProvider):
    def complete(self, prompt: str, model_config=None) -> str:
        prompt_lower = prompt.lower()
        if "quantitative researcher proposing alpha factors" in prompt_lower:
            return (
                '{"summary":"5-day momentum factor","constraints":["price-only","no-lookahead"],"virtual_score":0.7}'
            )
        if "analyze the following factor backtest results" in prompt_lower:
            return (
                '{"decision": true, "acceptable": true, "reason": "mock quant feedback", '
                '"observations": "metrics acceptable", "code_change_summary": "keep current factor"}'
            )
        if "scenario: data_science" in prompt_lower and "return only one fenced python code block" in prompt_lower:
            import json as _json

            model_suffix = ""
            if model_config is not None and getattr(model_config, "model", None):
                model_suffix = f" [model={model_config.model}]"
            meta = _json.dumps(
                {
                    "artifact_id": "artifact-llm",
                    "description": f"mock-ds-pipeline{model_suffix}",
                    "location": "/tmp/rd_agent_workspace",
                }
            )
            return (
                meta + "\n"
                "```python\n"
                "import json\n"
                "from pathlib import Path\n"
                "\n"
                "metrics = {'status': 'ok', 'accuracy': 0.91, 'row_count': 3, 'column_count': 3}\n"
                "Path('metrics.json').write_text(json.dumps(metrics), encoding='utf-8')\n"
                "print(json.dumps(metrics))\n"
                "```\n"
            )
        if "scenario: synthetic_research" in prompt_lower and "return only markdown" in prompt_lower:
            return (
                "## Findings\n"
                "1. Model accuracy improved by 15% after adding retrieval reranking.\n"
                "2. Latency increased by 8%, which remained within the operating budget.\n\n"
                "## Methodology\n"
                "- Compared baseline and reranked runs on the same benchmark split.\n\n"
                "## Conclusion\n"
                "- The reranked pipeline improved quality enough to justify the extra latency.\n"
            )
        return super().complete(prompt, model_config=model_config)


def make_mock_llm_adapter() -> LLMAdapter:
    return LLMAdapter(provider=_CodegenReadyMockProvider())


def patch_runtime_llm_provider():
    return patch("app.runtime._create_llm_provider", return_value=_CodegenReadyMockProvider())
