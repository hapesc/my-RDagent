# LLM Adapter (Task-12)

实现目录：`llm/`

- `llm/adapter.py`
  - `LLMProvider` 抽象
  - `LLMAdapter`（结构化解析 + 重试）
  - `MockLLMProvider`（测试与离线稳定输出）
- `llm/schemas.py`
  - `ProposalDraft`
  - `CodeDraft`
  - `FeedbackDraft`

## Integration

`plugins/examples/data_science_minimal.py` 中 proposal/coding/feedback 三段均已接入 `LLMAdapter`。

## Acceptance

`tests/test_task_12_llm_adapter.py` 覆盖：

- mock provider 结构化输出
- 解析失败重试
- proposal/coding/feedback 三段接入验证
