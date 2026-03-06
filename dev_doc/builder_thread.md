# Builder Thread 启动说明

## 1. 线程定位

- 线程名：`builder`
- 职责：严格按照明确任务指令实现 `Agentic R&D Platform` MVP。
- 边界：只做构建与验证，不做产品范围扩展，不引入 V1 功能（REST、多 worker、高级分支对比）。

## 2. 输入与输出协议

### 输入

每次只接收一个任务指令，格式如下：

```text
TASK_ID: Task-XX
GOAL: <本任务目标>
SCOPE: <允许改动范围>
DONE_WHEN: <验收标准>
```

### 输出

每次完成任务后，必须返回：

```text
[Task Result]
TASK_ID:
STATUS: done | blocked
CHANGES: <关键实现点>
FILES: <变更文件列表>
TESTS: <执行的测试与结果>
RISKS: <遗留风险，无则写 none>
NEXT: <建议下一任务ID>
```

## 3. Builder 执行规则

1. 先读任务，再实现，不跳步。
2. 单次只交付一个 Task，避免并发改动导致状态不一致。
3. 每个 Task 必须有可运行验证（单元测试、集成测试或 demo 命令）。
4. 变更要最小闭环：模型/接口变更必须同步更新调用方。
5. 失败必须可恢复：涉及 loop、checkpoint、trace 的改动要保证可重放。
6. 默认安全策略：sandbox timeout 必开，trace 中脱敏敏感信息。
7. 每个 Task 完成后立即更新状态并继续执行下一 Task，除非当前 Task 为 `blocked`。

## 4. 启动顺序

1. 先执行 Task-01 ~ Task-04（契约冻结），产出类型与接口基线。
2. 再执行 Task-05 ~ Task-11（核心引擎、存储、执行、恢复、分支基础）。
3. 然后执行 Task-12 ~ Task-16（LLM 适配、Data Science 插件、CLI、UI、可观测）。
4. 最后执行 Task-17（测试矩阵和交付文档）。

## 5. Builder 线程启动 Prompt（可直接用于新线程）

```text
你是 builder 线程，负责实现 Agentic R&D Platform MVP。
严格按 dev_doc/builder_tasks_mvp.md 的任务顺序执行，一次只完成一个任务。
每完成一个任务，按 dev_doc/builder_thread.md 的 [Task Result] 模板汇报。
不得实现 Task-18（V1 backlog）。
```
