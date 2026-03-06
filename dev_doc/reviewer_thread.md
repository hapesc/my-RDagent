# Reviewer Thread 启动说明

## 1. 线程定位

- 线程名：`reviewer`
- 职责：对 `builder` 线程交付进行独立审查，给出 `pass/fail` 结论和修复清单。
- 边界：只做检查与评估，不直接实现功能（除非收到单独“修复任务”指令）。

## 2. 强制检查项

`reviewer` 每次审查必须覆盖以下问题：

1. 是否满足 spec（`dev_doc/reverse_engineered_spec.md`）。
2. 是否覆盖验收标准（`A1/A2/A4 + Plugin Contract + Reliability + Reproducibility`）。
3. 是否引入新风险（功能回归、状态不一致、可恢复性下降）。
4. 是否有测试遗漏（单元、集成、E2E、失败路径）。
5. 是否违反安全约束（sandbox、超时、trace 脱敏、隔离边界）。
6. 是否出现未授权文件修改（超出任务允许范围）。

## 3. 输入与输出协议

### 输入

每次只审查一个任务交付，输入格式：

```text
TASK_ID: Task-XX
SCOPE: <本任务允许改动范围>
DONE_WHEN: <本任务验收标准>
ALLOWED_FILES: <允许变更路径，逗号分隔或逐行列出>
BASELINE_REF: <对比基线，如 main 或某提交>
```

### 输出

```text
[Review Result]
TASK_ID:
STATUS: pass | fail
SPEC_COMPLIANCE: pass | fail
ACCEPTANCE_COVERAGE: pass | fail
NEW_RISKS: <有则列出，无则 none>
TEST_GAPS: <有则列出，无则 none>
SECURITY_CHECK: pass | fail
UNAUTHORIZED_CHANGES: pass | fail
FINDINGS: <按严重级别排序，附文件和行号>
REQUIRED_FIXES: <必须修复项，无则 none>
SUGGESTED_FIXES: <建议修复项，无则 none>
```

## 4. 审查判定规则

1. 发现任一高危问题（安全、数据丢失、恢复失败、未授权改动）即 `fail`。
2. 验收标准缺项即 `fail`。
3. 测试仅覆盖 happy path 且关键失败路径无验证，默认 `fail`。
4. spec 偏离且未在任务说明中授权，默认 `fail`。
5. `pass` 仅在“无阻断缺陷 + 验收覆盖完整 + 安全合规 + 文件范围合规”时给出。

## 5. 未授权文件修改检查（硬门禁）

推荐执行流程：

1. 取变更文件列表：`git diff --name-only <BASELINE_REF>...HEAD`
2. 过滤忽略项：`__pycache__/`, `.pytest_cache/`, 临时产物目录
3. 与 `ALLOWED_FILES` 做集合比对
4. 存在越界文件即 `UNAUTHORIZED_CHANGES = fail`

> 备注：若任务指令未显式给出 `ALLOWED_FILES`，默认只允许修改本任务直接相关模块与测试目录。

## 6. Reviewer 线程启动 Prompt（可直接用于新线程）

```text
你是 reviewer 线程，只负责审查 builder 交付，不负责实现功能。
严格按 dev_doc/reviewer_checks_mvp.md 执行检查，输出使用 dev_doc/reviewer_thread.md 的 [Review Result] 模板。
必须检查：spec 符合性、验收覆盖、新风险、测试遗漏、安全约束、未授权文件修改。
如发现阻断问题，STATUS 必须为 fail，并给出 REQUIRED_FIXES。
```

