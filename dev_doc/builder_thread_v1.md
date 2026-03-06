# Builder Thread 启动说明（PRD V1）

## 1. 线程定位

- 线程名：`builder`
- 职责：在 MVP 已完成的基础上，继续实现 `PRD V1` 缺口，直到达到 `PRD V1 Definition of Done`。
- 边界：只做 `Task-18 ~ Task-23`；不进入 `Human Instructions`、`Knowledge Base`、多 worker、审批流等下一阶段能力。

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

1. 严格按 `Task-18 -> Task-23` 顺序执行，不跳步。
2. 单次只交付一个 Task，完成后再更新状态进入下一 Task。
3. 每个 Task 都必须包含验证证据：单元测试、集成测试、接口测试或 UI smoke。
4. 涉及 API / UI 的契约改动，必须先更新共享 DTO，再改调用方。
5. 涉及后台执行与恢复语义的改动，必须验证服务重启后的显式恢复行为。
6. 默认安全策略持续生效：sandbox timeout、fail-closed、本地执行显式 opt-in、trace 脱敏。

## 4. 启动顺序

1. 先执行 `Task-18`，冻结 V1 契约与配置扩展。
2. 再执行 `Task-19`、`Task-20`，完成第二场景与 per-step 配置基础。
3. 然后执行 `Task-21`，交付 FastAPI 控制面与 `RunSupervisor`。
4. 再执行 `Task-22`，补齐 branch/artifact 服务与 branch-aware UI。
5. 最后执行 `Task-23`，完成 V1 验收与硬化。

## 5. Builder 线程启动 Prompt（可直接用于新线程）

```text
你是 builder 线程，负责在 MVP 已完成的基础上继续实现 PRD V1。
严格按 dev_doc/builder_tasks_v1.md 的顺序执行 Task-18 到 Task-23，一次只完成一个任务。
每完成一个任务，按 dev_doc/builder_thread_v1.md 的 [Task Result] 模板汇报。
不得实现 FR-012 Human Instructions、FR-016 Knowledge Base、多 worker、审批流或其它延期能力。
```

