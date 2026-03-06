# Observability + Security Baseline (Task-16)

## Structured Observability

`observability/service.py` 提供：

- 结构化日志 `emit_log`
- 指标上报 `emit_metric`
- trace span `emit_trace`
- 指标快照 `snapshot_metrics`

## Trace Redaction

统一脱敏器：`observability/redaction.py::sanitize_payload`

- 默认脱敏键：`api_key/token/password/secret/authorization/access_key/private_key`
- 已接入：
  - `SQLiteMetadataStore.append_event`
  - `TraceStore.append_event`

## Context Baseline

异常/关键事件记录中保留 `run_id/step` 上下文，敏感字段以 `***` 替换。
