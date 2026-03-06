# Event Protocol (Task-04, MVP)

## Canonical Event Model

Event model统一定义在 `data_models.Event`，字段固定：

- `event_id`
- `run_id`
- `branch_id`
- `loop_index`
- `step_name`
- `event_type`
- `timestamp`
- `payload`

## Canonical Event Types (MVP Range)

- `run.created`
- `hypothesis.generated`
- `experiment.generated`
- `coding.round`
- `execution.finished`
- `feedback.generated`
- `trace.recorded`

## Serialization Protocol

- `Event.to_dict()` 负责序列化（时间转 UTC ISO8601 `Z` 格式）。
- `Event.from_dict()` 负责反序列化（含 `event_type` 枚举恢复）。
- `TraceStore` 使用 JSONL 持久化，每行一个 `Event.to_dict()`。

## Same Model for Storage and UI

- Trace 存储：`trace_store.service.TraceStore` 读写 `Event`。
- UI 投影：`trace_store.ui_view.TraceTimelineView` 直接消费 `List[Event]`。
