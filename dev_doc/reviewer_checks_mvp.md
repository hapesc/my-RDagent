# Reviewer Checks (MVP Gate)

> 使用范围：`Agentic R&D Platform` MVP（Data Science 首场景）  
> 审查基线：`reverse_engineered_spec.md`、`reverse_engineered_prd.md`、`reverse_engineered_architecture.md`

## 0. 审查准备

1. 收集 `builder` 本次提交信息：
   - `TASK_ID`
   - 改动文件列表
   - 执行过的测试命令与结果
2. 拉取差异并定位变更：
   - `git diff --name-only <BASELINE_REF>...HEAD`
   - `git diff <BASELINE_REF>...HEAD -- <关键文件>`
3. 对照任务指令中的 `SCOPE/DONE_WHEN/ALLOWED_FILES`。

## 1. Spec 符合性检查

必须检查以下是否被破坏：

1. 六阶段执行模型仍可成立：`propose -> experiment_generation -> coding -> running -> feedback -> record`。
2. 场景插件化边界清晰，主循环无场景硬编码分支。
3. checkpoint 与续跑能力未退化。
4. trace 结构化记录完整且可查询。
5. sandbox 执行仍具 timeout 与隔离语义。

判定：

- 任一核心语义被破坏 => `SPEC_COMPLIANCE = fail`。

## 2. 验收标准覆盖检查

逐项核对是否有证据（测试或演示日志）：

1. A1 End-to-End：完整一轮闭环并落盘 hypothesis/code/result/feedback。
2. A2 Resume：在 coding/running 中断后恢复到下一未完成 step。
3. A4 Sandbox：超时任务被终止并记录失败事件。
4. Plugin Contract Test：替换最小第二插件，无需改 LoopEngine 核心。
5. Reliability：step 级 checkpoint，异常中断最多丢失一个 step。
6. Reproducibility：同配置同输入可重放并可追溯 artifact/trace。

判定：

- 任一必测项缺失 => `ACCEPTANCE_COVERAGE = fail`。

## 3. 新风险检查

重点关注：

1. 状态机不一致（RUNNING/PAUSED/STOPPED/FAILED 流转错误）。
2. trace 与 checkpoint 写入时序竞态导致数据不一致。
3. 分支 DAG 父子关系错误导致历史不可恢复。
4. 错误处理吞异常或 silent failure。
5. 配置默认值不安全或与文档偏离。

输出要求：

- 使用 `P0/P1/P2/P3` 标注严重级别。
- 给出触发条件、影响范围、修复建议。

## 4. 测试遗漏检查

至少检查以下缺失：

1. 失败路径测试（timeout、执行异常、持久化失败、恢复失败）。
2. 边界测试（空输入、非法 scenario、不存在 checkpoint、重复 resume）。
3. 兼容测试（配置覆盖默认值、插件注册失败）。
4. 回归测试（旧命令/旧流程是否仍可用）。

判定：

- 关键失败路径未覆盖 => `TEST_GAPS` 必须列出并可导致 `fail`。

## 5. 安全约束检查

必须满足：

1. 生成代码不在控制平面进程内直接执行（除非明确本地后端 opt-in）。
2. timeout 强制执行，且超时后子进程可清理。
3. trace/log 中敏感信息（token/key/secret/password）被脱敏。
4. workspace 被视为不可信输入，避免直接影响控制平面状态。
5. artifact 访问不允许目录穿越（path traversal）。

判定：

- 任一高危违规 => `SECURITY_CHECK = fail`。

## 6. 未授权文件修改检查

硬性流程：

1. 列出改动文件：
   - `git diff --name-only <BASELINE_REF>...HEAD`
2. 过滤忽略项：
   - `__pycache__/`
   - `.pytest_cache/`
   - 临时运行产物目录
3. 与 `ALLOWED_FILES` 比对。

判定：

- 有越界变更 => `UNAUTHORIZED_CHANGES = fail`，并在 `FINDINGS` 逐条列出。

## 7. 审查结果分级

1. `pass`：无阻断问题，所有强制检查项通过。
2. `fail`：存在任一阻断问题（高危风险、安全违规、验收缺项、未授权改动）。

## 8. Findings 格式规范

每条 finding 推荐格式：

```text
[P1] <标题>
file: <path>:<line>
impact: <影响描述>
evidence: <复现或代码证据>
fix: <最小修复建议>
```

