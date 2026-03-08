# 全面审计 + 技术债清理

## TL;DR

> **Quick Summary**: 对 FC-2/FC-3 升级后的代码库做全面技术债清理：删除死代码模块、修复配置断线 bug、消除 hasattr 反模式、解除循环依赖、修复异常处理、全面修复文档矛盾、清理 sisyphus 元数据。
> 
> **Deliverables**:
> - 删除 4 个死代码模块（development_service/、execution_service/、artifact_registry/、reasoning_service/）
> - 修复 engine.py Layer-0 配置断线
> - 引入 Protocol 接口消除 5 处 hasattr 反模式
> - 解除 plugins↔scenarios 和 exploration_manager↔core.reasoning 循环依赖
> - 修复 5 处异常处理问题
> - 修复 dev_doc/ 全部文档矛盾和过时引用
> - 清理 .sisyphus/ 元数据
> 
> **Estimated Effort**: Medium-Large
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: T1 → T5 → T8 → T11 → T14 → Final

---

## Context

### Original Request
用户在完成 FC-2/FC-3 paper-faithful 升级后，选择"全面审计 + 技术债清理"方向。要求 TDD、保守方案、论文精确复现约束下清理所有技术债。

### Interview Summary
**Key Discussions**:
- 死代码处理：直接删除（不移到 deprecated/）
- hasattr 修复深度：全部 5 处生产代码修复
- 文档修复范围：全面文档审计修复
- 测试策略：TDD（先写失败测试再改实现）

**Research Findings**:
- 6 路并行探索完成：死代码分析、架构耦合分析、文档一致性审计、测试覆盖率分析、paper gap 分析、sisyphus 元数据分析
- 3 个模块（development_service/、execution_service/、artifact_registry/）全库零引用
- reasoning_service/ 仅被 synthetic_research/plugin.py:44 和 test_scenario_fc3_integration.py:8 引用
- plugins/__init__.py:20-25 导入 scenarios 造成循环依赖
- exploration_manager/service.py 导入 core.reasoning.VirtualEvaluator 造成跨包循环
- engine.py:87-88 硬编码 n_candidates=5, k_forward=2，config 字段存在但未接通
- paper_gap_analysis.md 4 个 FC 的 Evidence 部分仍写 "Missing:" 与 "Fully Implemented" 矛盾
- 548 tests pass, 3 warnings（pre-existing PytestCollectionWarning）

### Metis Review
**Identified Gaps** (addressed):
- reasoning_service 迁移需要先做兼容 shim 再删除，不能直接删目录 → 已纳入计划
- 异常处理需区分"静默吞异常"vs"rollback+re-raise"，不能一刀切 → 已分类处理
- .sisyphus/evidence/ 不可删除 → 已设为禁区
- 文档审计需限制范围（只修 stale references/contradictions，不重写全套）→ 已设边界
- hasattr 改 Protocol 时需保留"可选能力"语义 → 已纳入 Must NOT Have

---

## Work Objectives

### Core Objective
清理 FC-2/FC-3 升级后积累的技术债，使代码库达到可维护、无矛盾、无死代码的干净状态。

### Concrete Deliverables
- 删除 4 个死代码目录及其 __init__.py
- engine.py 从 config 读取 Layer-0 参数
- 5 处 hasattr 替换为 Protocol/接口方法
- plugins/__init__.py 不再直接导入 scenarios
- exploration_manager 不再直接导入 core.reasoning
- 5 处异常处理修复（加日志或改为具体异常）
- paper_gap_analysis.md 矛盾修复
- dev_doc/ 过时引用修复
- app 层入口 smoke tests 补齐
- 环境变量文档与 `app/config.py` 对齐
- .sisyphus/ 元数据清理

### Definition of Done
- [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed
- [ ] `python -c "import plugins; import exploration_manager.service; import scenarios.synthetic_research.plugin; print('ok')"` → ok（无 ImportError）
- [ ] `grep -r "n_candidates=5" core/loop/engine.py` → 无匹配
- [ ] `grep -r "from reasoning_service" --include="*.py" .` → 无匹配（排除 .sisyphus/）
- [ ] `grep -r "from development_service\|from execution_service\|from artifact_registry" --include="*.py" .` → 无匹配

### Must Have
- 所有删除操作前必须 grep 全仓确认零引用
- reasoning_service 迁移必须先做兼容 shim + 测试通过，再删除目录
- engine.py 配置修复必须有 env 驱动测试证明参数真正生效
- 循环依赖修复必须有 import smoke test
- 异常处理修复必须区分类型（silent swallow vs rollback+reraise）
- 文档修复必须限于 stale references/contradictions/过时命令，不重写全套
- 每个任务完成后必须跑全量回归

### Must NOT Have (Guardrails)
- 禁止借"清理"之名重做插件架构、运行时装配、或重命名大批模块
- 禁止在修循环依赖时顺手统一 import 风格、统一目录结构、抽象新层
- 禁止把测试中的 hasattr 断言升级成生产重构任务
- 禁止把 hasattr 改 Protocol 时将"可选能力"误改成"强制能力"
- 禁止删除 .sisyphus/evidence/ 下的任何文件
- 禁止修改 plugins/contracts.py 的公共接口
- 禁止修改 data_models.py 的公共接口
- 禁止在文档修复中添加新的架构描述或设计文档

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD (RED → GREEN → REFACTOR)
- **Framework**: pytest (already configured)
- **Each task**: Write failing test first → implement fix → verify test passes → run full regression

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Code changes**: Use Bash — run pytest, grep, python import checks
- **Doc changes**: Use Bash — verify referenced files exist, grep for stale patterns
- **Deletion**: Use Bash — confirm directory removed, grep for residual imports

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — sisyphus cleanup + dead code prep):
├── Task 1: .sisyphus/ 元数据清理 [quick]
├── Task 2: 删除 development_service/ [quick]
├── Task 3: 删除 execution_service/ [quick]
├── Task 4: 删除 artifact_registry/ [quick]

Wave 2 (After Wave 1 — config fix + reasoning_service migration):
├── Task 5: engine.py Layer-0 配置接通 [deep]
├── Task 6: reasoning_service 兼容迁移 [deep]
├── Task 7: 异常处理修复（silent swallow 类） [quick]

Wave 3 (After Wave 2 — Protocol 引入 + 循环依赖解除):
├── Task 8: ExplorationManager Protocol 接口 + hasattr 消除 [deep]
├── Task 9: plugins↔scenarios 循环依赖解除 [unspecified-high]
├── Task 10: 其余 hasattr 修复（adapter/control_plane/ui） [quick]

Wave 4 (After Wave 3 — reasoning_service 删除 + 异常处理收尾):
├── Task 11: reasoning_service 目录删除 [quick]
├── Task 12: 异常处理修复（rollback+reraise 加日志类） [quick]

Wave 5 (After Wave 4 — 文档/测试收尾):
├── Task 13: paper_gap_analysis.md 矛盾修复 [quick]
├── Task 14: dev_doc/ 全面过时引用修复 [unspecified-high]
├── Task 15: app 层未覆盖入口 smoke tests [unspecified-high]
├── Task 16: 环境变量文档补充 [quick]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T5 → T8 → T9 → T11 → T14 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Waves 1 & 5)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | — | 1 |
| 2 | — | 11 | 1 |
| 3 | — | — | 1 |
| 4 | — | — | 1 |
| 5 | 1 | 8 | 2 |
| 6 | 2 | 11 | 2 |
| 7 | — | — | 2 |
| 8 | 5 | 9 | 3 |
| 9 | 8 | 11 | 3 |
| 10 | — | — | 3 |
| 11 | 6, 9 | 14 | 4 |
| 12 | — | — | 4 |
| 13 | — | 14 | 5 |
| 14 | 11, 13 | F1-F4 | 5 |
| 15 | 9 | F1-F4 | 5 |
| 16 | — | F1-F4 | 5 |

### Agent Dispatch Summary

- **Wave 1**: **4** — T1-T4 → `quick`
- **Wave 2**: **3** — T5 → `deep`, T6 → `deep`, T7 → `quick`
- **Wave 3**: **3** — T8 → `deep`, T9 → `unspecified-high`, T10 → `quick`
- **Wave 4**: **2** — T11 → `quick`, T12 → `quick`
- **Wave 5**: **4** — T13 → `quick`, T14 → `unspecified-high`, T15 → `unspecified-high`, T16 → `quick`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [ ] 1. .sisyphus/ 元数据清理

  **What to do**:
  - 删除 `.sisyphus/boulder.json`（指向从未执行的 paper-fc2-fc3.md，是过期跟踪元数据）
  - 归档旧计划：将 `.sisyphus/plans/paper-fc2-fc3.md` 重命名为 `.sisyphus/plans/ARCHIVED-paper-fc2-fc3.md`
  - 保留 `.sisyphus/plans/paper-fc23-upgrade.md`（实际完成的计划）和 `.sisyphus/evidence/`（证据链）
  - 保留 `.sisyphus/plans/paper-fc1456.md`、`.sisyphus/plans/paper-gap-analysis.md`、`.sisyphus/plans/rdagent-cleanup-and-p0.md`（历史参考）

  **Must NOT do**:
  - 禁止删除 `.sisyphus/evidence/` 下任何文件
  - 禁止删除 `.sisyphus/plans/paper-fc23-upgrade.md`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `.sisyphus/boulder.json` — 内容为 `{"plan": "paper-fc2-fc3", "tasks_done": 0, "tasks_total": 158}`，指向从未执行的计划
  - `.sisyphus/plans/paper-fc2-fc3.md` — 早期版本计划，从未被执行
  - `.sisyphus/plans/paper-fc23-upgrade.md` — 实际完成的 FC-2/FC-3 升级计划
  - `.sisyphus/evidence/fc23-delivery-index.md` — 交付证据索引

  **Acceptance Criteria**:
  - [ ] `.sisyphus/boulder.json` 不存在
  - [ ] `.sisyphus/plans/ARCHIVED-paper-fc2-fc3.md` 存在
  - [ ] `.sisyphus/plans/paper-fc2-fc3.md` 不存在
  - [ ] `.sisyphus/evidence/fc23-delivery-index.md` 仍存在

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: boulder.json 已删除
    Tool: Bash
    Steps:
      1. test ! -f .sisyphus/boulder.json && echo "PASS" || echo "FAIL"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-1-boulder-cleanup.txt

  Scenario: 旧计划已归档
    Tool: Bash
    Steps:
      1. test -f .sisyphus/plans/ARCHIVED-paper-fc2-fc3.md && echo "PASS" || echo "FAIL"
      2. test ! -f .sisyphus/plans/paper-fc2-fc3.md && echo "PASS" || echo "FAIL"
    Expected Result: 两行均为 PASS
    Evidence: .sisyphus/evidence/task-1-archive-check.txt

  Scenario: 证据链完整
    Tool: Bash
    Steps:
      1. test -f .sisyphus/evidence/fc23-delivery-index.md && echo "PASS" || echo "FAIL"
      2. test -f .sisyphus/plans/paper-fc23-upgrade.md && echo "PASS" || echo "FAIL"
    Expected Result: 两行均为 PASS
    Evidence: .sisyphus/evidence/task-1-evidence-intact.txt
  ```

  **Commit**: YES
  - Message: `chore(sisyphus): clean stale boulder.json and archive unused plan`
  - Files: `.sisyphus/boulder.json`, `.sisyphus/plans/paper-fc2-fc3.md` → `ARCHIVED-paper-fc2-fc3.md`

- [ ] 2. 删除 development_service/ 死代码模块

  **What to do**:
  - TDD RED: 写一个 import smoke test 确认 `development_service` 当前可导入（基线）
  - 用 grep 全仓确认零引用：`grep -r "from development_service\|import development_service" --include="*.py" .`
  - 删除整个 `development_service/` 目录（含 `__init__.py` 和 `service.py`）
  - TDD GREEN: 更新 smoke test 确认删除后无 ImportError（其他模块不受影响）
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改任何其他模块

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 11 (reasoning_service 删除需要所有死代码先清理)
  - **Blocked By**: None

  **References**:
  - `development_service/service.py` — 纯 placeholder scaffold（返回 `"artifact-placeholder"`），56 行
  - `development_service/__init__.py` — 包导出文件
  - 全库 grep 确认：`from development_service` 和 `import development_service` 均无匹配

  **Acceptance Criteria**:
  - [ ] `development_service/` 目录不存在
  - [ ] `grep -r "from development_service\|import development_service" --include="*.py" .` → 无匹配
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 目录已删除且无残留引用
    Tool: Bash
    Steps:
      1. test ! -d development_service && echo "DIR_GONE=PASS" || echo "DIR_GONE=FAIL"
      2. grep -r "from development_service\|import development_service" --include="*.py" . | wc -l
    Expected Result: DIR_GONE=PASS, grep 输出 0
    Evidence: .sisyphus/evidence/task-2-dev-service-deleted.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-2-regression.txt
  ```

  **Commit**: YES
  - Message: `chore: remove dead development_service/ placeholder module`
  - Files: `development_service/` (deleted)

- [ ] 3. 删除 execution_service/ 死代码模块

  **What to do**:
  - 用 grep 全仓确认零引用：`grep -r "from execution_service\|import execution_service" --include="*.py" .`
  - 删除整个 `execution_service/` 目录
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改任何其他模块
  - 注意：不要与 `core/execution/` 混淆，那是活跃代码

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `execution_service/service.py` — 纯 placeholder scaffold（返回 `"run-placeholder"`），78 行
  - `execution_service/__init__.py` — 包导出文件
  - 全库 grep 确认：零引用

  **Acceptance Criteria**:
  - [ ] `execution_service/` 目录不存在
  - [ ] `grep -r "from execution_service\|import execution_service" --include="*.py" .` → 无匹配
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 目录已删除且无残留引用
    Tool: Bash
    Steps:
      1. test ! -d execution_service && echo "DIR_GONE=PASS" || echo "DIR_GONE=FAIL"
      2. grep -r "from execution_service\|import execution_service" --include="*.py" . | wc -l
    Expected Result: DIR_GONE=PASS, grep 输出 0
    Evidence: .sisyphus/evidence/task-3-exec-service-deleted.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-3-regression.txt
  ```

  **Commit**: YES (groups with Task 2, 4)
  - Message: `chore: remove dead execution_service/ placeholder module`
  - Files: `execution_service/` (deleted)

- [ ] 4. 删除 artifact_registry/ 死代码模块

  **What to do**:
  - 用 grep 全仓确认零引用：`grep -r "from artifact_registry\|import artifact_registry\|ArtifactRegistry" --include="*.py" .`
  - 注意：grep 会匹配 artifact_registry/ 自身的文件，需排除自引用
  - 删除整个 `artifact_registry/` 目录
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改任何其他模块

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `artifact_registry/service.py` — placeholder scaffold，定义 ArtifactRegistry 和 ArtifactRegistryConfig
  - `artifact_registry/__init__.py` — re-export
  - 全库 grep 确认：仅自引用，无外部引用

  **Acceptance Criteria**:
  - [ ] `artifact_registry/` 目录不存在
  - [ ] 外部无引用（排除自身后 grep 为 0）
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 目录已删除且无残留引用
    Tool: Bash
    Steps:
      1. test ! -d artifact_registry && echo "DIR_GONE=PASS" || echo "DIR_GONE=FAIL"
      2. grep -r "from artifact_registry\|import artifact_registry\|ArtifactRegistry" --include="*.py" . | wc -l
    Expected Result: DIR_GONE=PASS, grep 输出 0
    Evidence: .sisyphus/evidence/task-4-artifact-registry-deleted.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-4-regression.txt
  ```

  **Commit**: YES (groups with Task 2, 3)
  - Message: `chore: remove dead artifact_registry/ placeholder module`
  - Files: `artifact_registry/` (deleted)

- [ ] 5. engine.py Layer-0 配置接通

  **What to do**:
  - TDD RED: 写测试验证 `RD_AGENT_LAYER0_N_CANDIDATES=10` 和 `RD_AGENT_LAYER0_K_FORWARD=3` 环境变量能影响 `LoopEngine.run()` 中 `generate_diverse_roots` 的调用参数。当前测试应 FAIL（因为 engine.py 硬编码 5/2）
  - 修改 `core/loop/engine.py`：
    - 在 `LoopEngine.__init__` 中接受 `layer0_n_candidates: int = 5` 和 `layer0_k_forward: int = 2` 参数
    - 在 `run()` 方法第 87-88 行，将硬编码的 `n_candidates=5, k_forward=2` 替换为 `self._layer0_n_candidates` 和 `self._layer0_k_forward`
  - 修改 `app/runtime.py`：在构造 `LoopEngine` 时从 `AppConfig` 传入 `layer0_n_candidates` 和 `layer0_k_forward`
  - TDD GREEN: 验证测试通过
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改 `generate_diverse_roots` 的签名
  - 禁止修改 `AppConfig` 的字段定义（已存在）
  - 禁止修改 `VirtualEvaluator` 的构造（它已经从 runtime 接收这些参数）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 涉及 runtime wiring 链路，需要理解 config → runtime → engine 的完整传递路径
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 6, 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 8 (Protocol 引入依赖 engine 参数化完成)
  - **Blocked By**: Task 1

  **References**:
  - `core/loop/engine.py:82-88` — 当前硬编码位置：`if hasattr(self._exploration_manager, "generate_diverse_roots"): roots = self._exploration_manager.generate_diverse_roots(task_summary, n_candidates=5, k_forward=2, ...)`
  - `app/config.py:89-90` — 已有字段：`layer0_n_candidates: int` 和 `layer0_k_forward: int`，从 `RD_AGENT_LAYER0_N_CANDIDATES` / `RD_AGENT_LAYER0_K_FORWARD` 读取
  - `app/runtime.py:129` — 已将 layer0 参数传入 VirtualEvaluator，但未传入 LoopEngine
  - `app/runtime.py:145-155` — LoopEngine 构造位置
  - `tests/test_runtime_wiring.py` — 已有 config 加载测试，可扩展

  **Acceptance Criteria**:
  - [ ] `grep "n_candidates=5" core/loop/engine.py` → 无匹配
  - [ ] `grep "k_forward=2" core/loop/engine.py` → 无匹配
  - [ ] 新测试：设置 `RD_AGENT_LAYER0_N_CANDIDATES=10`，验证 engine 传递 `n_candidates=10` 给 exploration_manager
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 硬编码已消除
    Tool: Bash
    Steps:
      1. grep -n "n_candidates=5" core/loop/engine.py | wc -l
      2. grep -n "k_forward=2" core/loop/engine.py | wc -l
    Expected Result: 两行均输出 0
    Evidence: .sisyphus/evidence/task-5-hardcode-removed.txt

  Scenario: 环境变量驱动参数生效
    Tool: Bash
    Steps:
      1. RD_AGENT_LAYER0_N_CANDIDATES=10 RD_AGENT_LAYER0_K_FORWARD=3 python -m pytest tests/test_runtime_wiring.py -q -k "layer0" 2>&1 | tail -5
    Expected Result: 相关测试 PASS
    Evidence: .sisyphus/evidence/task-5-env-driven.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-5-regression.txt
  ```

  **Commit**: YES
  - Message: `fix(engine): wire Layer-0 params from config instead of hardcoding 5/2`
  - Files: `core/loop/engine.py`, `app/runtime.py`, `tests/test_runtime_wiring.py`

- [ ] 6. reasoning_service 兼容迁移（Phase 1: shim）

  **What to do**:
  - TDD RED: 写测试验证 `synthetic_research/plugin.py` 的 `SyntheticResearchProposalEngine` 在没有 `reasoning_service` 的情况下仍能正常工作（当前应 FAIL 因为 fallback 路径依赖 reasoning_service）
  - 修改 `scenarios/synthetic_research/plugin.py`:
    - 移除 `from reasoning_service import ReasoningService, ReasoningServiceConfig`（line 44）
    - 将 `ReasoningService` 的 fallback 逻辑内联为一个简单的 placeholder proposal 生成（与原 reasoning_service 行为一致：返回 `Proposal(proposal_id="proposal-placeholder", summary=task_summary, constraints=[policy], virtual_score=0.0)`）
    - 或者：将 fallback 改为直接使用已注入的 `reasoning_pipeline`（如果存在），完全跳过 reasoning_service
  - 修改 `tests/test_scenario_fc3_integration.py`:
    - 移除 `from reasoning_service import ReasoningService, ReasoningServiceConfig`（line 8）
    - 更新测试以不依赖 reasoning_service
  - TDD GREEN: 验证测试通过
  - 跑全量回归
  - 注意：此任务只做迁移，不删除 reasoning_service/ 目录（Task 11 负责删除）

  **Must NOT do**:
  - 禁止在此任务中删除 reasoning_service/ 目录
  - 禁止修改 `core/reasoning/pipeline.py` 或 `core/reasoning/virtual_eval.py`
  - 禁止修改 `plugins/contracts.py`

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解 proposal engine 的 fallback 链路（virtual_evaluator → reasoning_pipeline → llm_adapter → reasoning_service），确保迁移不破坏行为
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 11 (reasoning_service 删除)
  - **Blocked By**: Task 2 (development_service 删除完成确认模式可行)

  **References**:
  - `scenarios/synthetic_research/plugin.py:44` — `from reasoning_service import ReasoningService, ReasoningServiceConfig`
  - `scenarios/synthetic_research/plugin.py:87-193` — `SyntheticResearchProposalEngine.propose()` 方法，fallback 链路：virtual_evaluator → reasoning_pipeline → llm_adapter → reasoning_service
  - `scenarios/synthetic_research/plugin.py:351-377` — `build_synthetic_research_bundle()` 构造 ReasoningService 实例
  - `tests/test_scenario_fc3_integration.py:8` — `from reasoning_service import ReasoningService, ReasoningServiceConfig`
  - `reasoning_service/service.py:26-56` — 原始 `generate_proposal` 实现（返回 placeholder）

  **Acceptance Criteria**:
  - [ ] `grep -r "from reasoning_service" --include="*.py" . | grep -v ".sisyphus" | grep -v "reasoning_service/"` → 无匹配
  - [ ] `python -m pytest tests/test_scenario_fc3_integration.py tests/test_task_19_synthetic_research.py -q` → PASS
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: reasoning_service 引用已从调用方移除
    Tool: Bash
    Steps:
      1. grep -r "from reasoning_service" --include="*.py" . | grep -v ".sisyphus" | grep -v "reasoning_service/" | wc -l
    Expected Result: 0
    Evidence: .sisyphus/evidence/task-6-refs-removed.txt

  Scenario: synthetic_research 场景仍可构建并运行 proposal
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_scenario_fc3_integration.py -q 2>&1 | tail -5
      2. python -m pytest tests/test_task_19_synthetic_research.py -q 2>&1 | tail -5
    Expected Result: 全部 PASS
    Evidence: .sisyphus/evidence/task-6-scenario-tests.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-6-regression.txt
  ```

  **Commit**: YES
  - Message: `refactor(synthetic-research): inline reasoning_service fallback, remove dependency`
  - Files: `scenarios/synthetic_research/plugin.py`, `tests/test_scenario_fc3_integration.py`

- [ ] 7. 异常处理修复（silent swallow 类）

  **What to do**:
  - TDD RED: 写测试验证 `workspace_manager.py` 的 `execute_with_rollback` 在操作失败时记录日志（当前无日志）
  - 修复 `core/execution/workspace_manager.py:124-129`:
    - 在 `except Exception:` 块中添加 `logger.exception("workspace operation failed, rolling back")` 
    - 保留现有的 rollback + return False 行为
  - 修复 `ui/trace_ui.py:203`:
    - 在 `except Exception:` 块中添加 `logger.exception("trace UI error")`
    - 或改为捕获具体异常类型
  - TDD GREEN: 验证日志测试通过
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改 rollback+re-raise 类的异常处理（sqlite_store.py:43、branch_trace_store.py:43、memory_service/service.py:61）——这些是正确的模式，Task 12 会单独加日志
  - 禁止改变 workspace_manager 的返回值语义（仍返回 False）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `core/execution/workspace_manager.py:122-129` — `execute_with_rollback` 方法，bare except 无日志
  - `ui/trace_ui.py:200-210` — bare except 无日志
  - `core/execution/workspace_manager.py:1-10` — 检查是否已有 logger 定义

  **Acceptance Criteria**:
  - [ ] `workspace_manager.py` 的 except 块包含 `logger.exception` 或 `logger.error` 调用
  - [ ] `ui/trace_ui.py` 的 except 块包含日志调用
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: workspace_manager 异常处理有日志
    Tool: Bash
    Steps:
      1. grep -A2 "except Exception" core/execution/workspace_manager.py
    Expected Result: 包含 logger.exception 或 logger.error
    Evidence: .sisyphus/evidence/task-7-workspace-logging.txt

  Scenario: trace_ui 异常处理有日志
    Tool: Bash
    Steps:
      1. grep -A2 "except Exception" ui/trace_ui.py
    Expected Result: 包含 logger 调用
    Evidence: .sisyphus/evidence/task-7-ui-logging.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-7-regression.txt
  ```

  **Commit**: YES
  - Message: `fix: add logging to silent exception handlers in workspace_manager and trace_ui`
  - Files: `core/execution/workspace_manager.py`, `ui/trace_ui.py`

- [ ] 8. ExplorationManager Protocol 接口 + engine.py hasattr 消除

  **What to do**:
  - TDD RED: 为 `LoopEngine` 写测试，验证当 exploration manager 支持/不支持 Layer-0 diverse roots 和 merge_traces 时，两条分支行为都正确
  - 在 `exploration_manager/` 引入明确的 capability Protocol（例如 `SupportsDiverseRoots`、`SupportsTraceMerge`），或在 `ExplorationManager` 公共接口上定义稳定方法
  - 修改 `core/loop/engine.py`：移除 `hasattr(self._exploration_manager, "generate_diverse_roots")` 和 `hasattr(self._exploration_manager, "merge_traces")`
  - 保持“可选能力”语义：不支持时必须回退到当前单根/不合并路径，不能把可选能力升级为强制能力
  - TDD GREEN: 验证支持/不支持两条路径都通过
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改 `plugins/contracts.py`
  - 禁止把 optional capability 变成必填 capability
  - 禁止重写 LoopEngine 整体架构

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 9
  - **Blocked By**: Task 5

  **References**:
  - `core/loop/engine.py:82` - Layer-0 capability probe via `hasattr(..., "generate_diverse_roots")`
  - `core/loop/engine.py:237` - merge capability probe via `hasattr(..., "merge_traces")`
  - `exploration_manager/service.py` - 当前 ExplorationManager 实现
  - `tests/test_engine_multibranch.py` - 多分支行为测试模式
  - `tests/test_exploration_manager.py` - exploration manager 行为测试模式

  **Acceptance Criteria**:
  - [ ] `core/loop/engine.py` 不再包含 `hasattr(self._exploration_manager`
  - [ ] 新测试覆盖“支持 diverse roots”和“不支持 diverse roots”两条路径
  - [ ] 新测试覆盖“支持 merge_traces”和“不支持 merge_traces”两条路径
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: engine.py 中 hasattr 已消除
    Tool: Bash
    Steps:
      1. grep -n "hasattr(self._exploration_manager" core/loop/engine.py | wc -l
    Expected Result: 0
    Evidence: .sisyphus/evidence/task-8-engine-hasattr-removed.txt

  Scenario: 支持与不支持 capability 的测试均通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_engine_multibranch.py tests/test_exploration_manager.py -q 2>&1 | tail -8
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-8-capability-tests.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-8-regression.txt
  ```

  **Commit**: YES
  - Message: `refactor(engine): replace exploration_manager hasattr probes with explicit capabilities`
  - Files: `core/loop/engine.py`, `exploration_manager/service.py`, `tests/test_engine_multibranch.py`

- [ ] 9. 解除 plugins↔scenarios 与 exploration_manager↔core.reasoning 循环依赖

  **What to do**:
  - TDD RED: 写 import smoke tests，验证 `import plugins`, `import scenarios.synthetic_research.plugin`, `import exploration_manager.service` 在当前实现下暴露出的循环导入/时序脆弱点
  - 修改 `plugins/__init__.py`：移除对 `scenarios` 的直接导入，把 scenario builder 注册下沉到 `app/runtime.py` 或独立 registry wiring 层
  - 修改 `exploration_manager/service.py`：停止直接 import `core.reasoning.virtual_eval.VirtualEvaluator`，改为通过构造注入 Protocol/接口
  - 修改 `app/runtime.py`：承担 built-in scenario 注册与 evaluator 注入职责
  - TDD GREEN: import smoke tests + runtime wiring tests 通过
  - 跑全量回归

  **Must NOT do**:
  - 禁止顺手统一 import 风格或重构目录结构
  - 禁止改动 scenarios 的业务语义
  - 禁止改动 `plugins/contracts.py` 公共接口

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 11, Task 15
  - **Blocked By**: Task 8

  **References**:
  - `plugins/__init__.py:20-25` - 顶层导入 `scenarios`
  - `scenarios/data_science/plugin.py` - 反向导入 `plugins.contracts`
  - `scenarios/synthetic_research/plugin.py` - 反向导入 `plugins.contracts`
  - `exploration_manager/service.py` - 当前 runtime import `core.reasoning.virtual_eval`
  - `app/runtime.py` - 当前 runtime 组装点
  - `tests/test_runtime_wiring.py` - runtime 组装测试
  - `tests/test_integration_full_loop.py` - 最少 mock 的真实集成路径

  **Acceptance Criteria**:
  - [ ] `plugins/__init__.py` 不再导入 `scenarios`
  - [ ] `exploration_manager/service.py` 不再导入 `core.reasoning.virtual_eval`
  - [ ] `python - <<'PY'\nimport plugins\nimport exploration_manager.service\nimport scenarios.synthetic_research.plugin\nprint('ok')\nPY` → `ok`
  - [ ] `python -m pytest tests/test_runtime_wiring.py tests/test_integration_full_loop.py -q` → PASS

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: import smoke test 通过
    Tool: Bash
    Steps:
      1. python - <<'PY'
import plugins
import exploration_manager.service
import scenarios.synthetic_research.plugin
print('ok')
PY
    Expected Result: 输出 ok，且无 ImportError
    Evidence: .sisyphus/evidence/task-9-import-smoke.txt

  Scenario: runtime wiring 与 full loop 集成通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_runtime_wiring.py tests/test_integration_full_loop.py -q 2>&1 | tail -8
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-9-runtime-integration.txt

  Scenario: 全量回归通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q 2>&1 | tail -3
    Expected Result: 548+ passed, 0 failed
    Evidence: .sisyphus/evidence/task-9-regression.txt
  ```

  **Commit**: YES
  - Message: `refactor(runtime): break plugin-scenario and exploration-reasoning import cycles`
  - Files: `plugins/__init__.py`, `exploration_manager/service.py`, `app/runtime.py`

- [ ] 10. 其余 hasattr 修复（adapter / control_plane / trace_ui）

  **What to do**:
  - 修复 `llm/adapter.py:299` 的 `hasattr(schema_cls, "from_dict")`
  - 修复 `app/control_plane.py:212` 的 `hasattr(request.stop_conditions, "to_dict")`
  - 修复 `ui/trace_ui.py:137` 的 `hasattr(client, f"{action}_run")`
  - 优先用 Protocol、稳定接口、或显式属性校验替代
  - 补对应单元/契约测试
  - 跑全量回归

  **Must NOT do**:
  - 禁止修改对外 DTO 字段名
  - 禁止改 UI 行为语义

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 9 after Task 8 starts)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `llm/adapter.py:299`
  - `app/control_plane.py:212`
  - `ui/trace_ui.py:137`
  - `tests/test_task_21_control_plane.py`
  - `tests/test_task_15_trace_ui.py`
  - `tests/test_task_12_llm_adapter.py`

  **Acceptance Criteria**:
  - [ ] 以上 3 处生产代码不再使用 `hasattr(`
  - [ ] 对应测试 PASS
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 剩余 hasattr 清零
    Tool: Bash
    Steps:
      1. grep -n "hasattr(" llm/adapter.py app/control_plane.py ui/trace_ui.py | wc -l
    Expected Result: 0
    Evidence: .sisyphus/evidence/task-10-hasattr-cleared.txt

  Scenario: 相关模块测试通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_task_12_llm_adapter.py tests/test_task_21_control_plane.py tests/test_task_15_trace_ui.py -q 2>&1 | tail -8
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-10-module-tests.txt
  ```

  **Commit**: YES
  - Message: `refactor: replace remaining hasattr checks with explicit interfaces`
  - Files: `llm/adapter.py`, `app/control_plane.py`, `ui/trace_ui.py`

- [ ] 11. 删除 reasoning_service/ 死代码目录

  **What to do**:
  - 在 Task 6 完成兼容迁移后，再次 grep 全仓确认所有调用方/测试已迁出
  - 删除 `reasoning_service/` 目录
  - 跑 targeted tests + 全量回归

  **Must NOT do**:
  - 禁止在 Task 6 未完成前删除目录

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 14
  - **Blocked By**: Task 6, Task 9

  **References**:
  - `reasoning_service/service.py` - placeholder fallback 实现
  - `scenarios/synthetic_research/plugin.py` - 迁移后应不再引用
  - `tests/test_scenario_fc3_integration.py` - 迁移后应不再引用

  **Acceptance Criteria**:
  - [ ] `reasoning_service/` 目录不存在
  - [ ] `grep -r "from reasoning_service\|import reasoning_service" --include="*.py" . | grep -v ".sisyphus"` → 无匹配
  - [ ] `python -m pytest tests/test_scenario_fc3_integration.py tests/test_task_19_synthetic_research.py -q` → PASS
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 目录已删除且无残留引用
    Tool: Bash
    Steps:
      1. test ! -d reasoning_service && echo "DIR_GONE=PASS" || echo "DIR_GONE=FAIL"
      2. grep -r "from reasoning_service\|import reasoning_service" --include="*.py" . | grep -v ".sisyphus" | wc -l
    Expected Result: DIR_GONE=PASS, grep 输出 0
    Evidence: .sisyphus/evidence/task-11-reasoning-service-removed.txt
  ```

  **Commit**: YES
  - Message: `chore: remove reasoning_service after synthetic_research migration`
  - Files: `reasoning_service/` (deleted)

- [ ] 12. 异常处理修复（rollback+reraise 加日志类）

  **What to do**:
  - 给 `memory_service/service.py:61`、`core/storage/sqlite_store.py:43`、`core/storage/branch_trace_store.py:43` 的 rollback+reraise 路径补结构化日志
  - 保留 rollback + raise 语义，不改变异常传播
  - 补日志断言测试
  - 跑全量回归

  **Must NOT do**:
  - 禁止吞掉异常
  - 禁止改变事务边界

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 11)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `memory_service/service.py:56-65`
  - `core/storage/sqlite_store.py:38-47`
  - `core/storage/branch_trace_store.py:38-47`
  - `tests/test_memory_service.py`
  - `tests/test_task_06_storage_foundation.py`
  - `tests/test_task_11_branch_trace_store.py`

  **Acceptance Criteria**:
  - [ ] 3 处 rollback+reraise 块都有日志
  - [ ] 相关测试 PASS
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: rollback+reraise 路径有日志且仍抛异常
    Tool: Bash
    Steps:
      1. python -m pytest tests/test_memory_service.py tests/test_task_06_storage_foundation.py tests/test_task_11_branch_trace_store.py -q 2>&1 | tail -8
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-12-storage-logging.txt
  ```

  **Commit**: YES
  - Message: `fix(storage): add logging to rollback-and-reraise paths`
  - Files: `memory_service/service.py`, `core/storage/sqlite_store.py`, `core/storage/branch_trace_store.py`

- [ ] 13. 修复 paper_gap_analysis.md 内部矛盾

  **What to do**:
  - 修复 `dev_doc/paper_gap_analysis.md` 中 FC-1/4/5/6 的 “Fully Implemented” 与 “Evidence: Missing:” 矛盾
  - 更新对应 `Impact` 段落，改为已实现后的剩余 minor gap 描述，或删除过时影响说明
  - 保留论文 gap 分析整体结构，不重写整份文档

  **Must NOT do**:
  - 禁止重写整篇 gap analysis
  - 禁止改变已确认完成的 FC-2/FC-3 事实状态

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: Task 14
  - **Blocked By**: None

  **References**:
  - `dev_doc/paper_gap_analysis.md:46` + `:69-71` - FC-1 矛盾
  - `dev_doc/paper_gap_analysis.md:214` + `:237-239` - FC-4 矛盾
  - `dev_doc/paper_gap_analysis.md:269` + `:292-294` - FC-5 矛盾
  - `dev_doc/paper_gap_analysis.md:324` + `:347-349` - FC-6 矛盾

  **Acceptance Criteria**:
  - [ ] 文档中不再出现同一 FC 同时“Fully Implemented”又“Missing:”
  - [ ] `grep -n "Missing:" dev_doc/paper_gap_analysis.md` 仅保留真实未实现项，或为 0

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: FC 矛盾已消除
    Tool: Bash
    Steps:
      1. grep -n "Missing:" dev_doc/paper_gap_analysis.md
    Expected Result: 不再出现 FC-1/4/5/6 的旧 Missing 文本
    Evidence: .sisyphus/evidence/task-13-gap-analysis-clean.txt
  ```

  **Commit**: YES
  - Message: `docs(gap-analysis): remove stale missing bullets and impact contradictions`
  - Files: `dev_doc/paper_gap_analysis.md`

- [ ] 14. 全面修复 dev_doc / README 过时引用与 stale 内容

  **What to do**:
  - 修复 `dev_doc/` 与 `README.md` 中的过时文件路径（如 `main.py`、`orchestrator_rd_loop_engine`、demo files）
  - 修复过时测试计数、旧 commit hash 描述、过时命令/入口说明
  - 校验 README 中列出的命令入口文件仍存在，并把描述更新为当前真实状态
  - 只修 stale references / contradictions / outdated commands，不扩写新设计

  **Must NOT do**:
  - 禁止重写整套文档
  - 禁止新增超出代码现状的架构承诺

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5
  - **Blocks**: Final verification
  - **Blocked By**: Task 11, Task 13

  **References**:
  - `README.md` - 启动/CLI/API/UI 命令说明
  - `dev_doc/reverse_engineered_architecture.md` - stale `main.py` 示例
  - `dev_doc/reverse_engineered_spec.md` - 旧引用
  - `dev_doc/task_21_control_plane.md` - 控制面入口说明
  - `dev_doc/config_env_mapping.md` - 环境变量映射
  - `dev_doc/adr/005-dual-architecture-cleanup.md` - 历史删除项说明

  **Acceptance Criteria**:
  - [ ] `grep -r "main.py\|orchestrator_rd_loop_engine" dev_doc README.md` 仅保留历史 ADR 上下文中的必要说明
  - [ ] README 中所有命令引用的文件都存在
  - [ ] 过时测试计数被移除或更新为动态描述

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: stale 引用已清理
    Tool: Bash
    Steps:
      1. grep -r "main.py\|orchestrator_rd_loop_engine" dev_doc README.md
    Expected Result: 仅保留必要历史 ADR 语境，或无匹配
    Evidence: .sisyphus/evidence/task-14-stale-refs.txt

  Scenario: README 命令入口文件存在
    Tool: Bash
    Steps:
      1. python - <<'PY'
from pathlib import Path
targets = ["agentrd_cli.py", "cli.py", "app/api_main.py", "app/startup.py", "ui/trace_ui.py"]
for t in targets:
    print(t, Path(t).exists())
PY
    Expected Result: 所有目标输出 True
    Evidence: .sisyphus/evidence/task-14-readme-targets.txt
  ```

  **Commit**: YES
  - Message: `docs: fix stale references and outdated commands across dev_doc and README`
  - Files: `README.md`, `dev_doc/*.md`

- [ ] 15. 补齐 app 层未覆盖入口 smoke tests

  **What to do**:
  - 为 `app/api_main.py`、`app/startup.py`、`app/run_supervisor.py`、`app/query_services.py`、`app/fastapi_compat.py` 补最小 smoke/integration tests
  - 优先验证：导入成功、基础启动成功、关键查询函数在空状态不崩溃
  - 避免重度 mock，仅在必要的外部依赖处 stub
  - 跑对应 targeted tests + 全量回归

  **Must NOT do**:
  - 禁止为测试而修改生产代码接口
  - 禁止把 smoke test 写成纯 mock call-count 测试

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Task 14 after Task 9)
  - **Blocks**: Final verification
  - **Blocked By**: Task 9

  **References**:
  - `app/api_main.py`
  - `app/startup.py`
  - `app/run_supervisor.py`
  - `app/query_services.py`
  - `app/fastapi_compat.py`
  - `tests/test_runtime_wiring.py` - 当前 app 层 wiring 测试过度依赖 mock

  **Acceptance Criteria**:
  - [ ] 新增 smoke tests 覆盖上述 5 个文件
  - [ ] 至少 1 个测试使用真实 `build_runtime()` 或最少 mock 路径
  - [ ] `python -m pytest tests/ -q` → 548+ passed, 0 failed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: app 层 smoke tests 通过
    Tool: Bash
    Steps:
      1. python -m pytest tests/ -q -k "api_main or startup or run_supervisor or query_services or fastapi_compat" 2>&1 | tail -10
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-15-app-smoke.txt
  ```

  **Commit**: YES
  - Message: `test(app): add smoke coverage for untested app entrypoints`
  - Files: `tests/`

- [ ] 16. 环境变量文档对齐与单一真相源校准

  **What to do**:
  - 以 `app/config.py` 为唯一真相源，更新 `dev_doc/config_env_mapping.md` 和 `README.md` 的环境变量说明
  - 记录 `AGENTRD_*` 与 `RD_AGENT_*` 两套前缀的职责边界
  - 去掉过时/重复配置说明，明确当前推荐变量集合

  **Must NOT do**:
  - 禁止新增不存在于 `app/config.py` 的变量
  - 禁止在文档里承诺尚未实现的配置行为

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5
  - **Blocks**: Final verification
  - **Blocked By**: None

  **References**:
  - `app/config.py` - 单一真相源
  - `dev_doc/config_env_mapping.md`
  - `README.md`

  **Acceptance Criteria**:
  - [ ] 文档中列出的环境变量均可在 `app/config.py` 找到
  - [ ] `AGENTRD_*` / `RD_AGENT_*` 角色边界描述清晰

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 文档中的环境变量都来自 app/config.py
    Tool: Bash
    Steps:
      1. python - <<'PY'
from pathlib import Path
text = Path('app/config.py').read_text()
for key in ['AGENTRD_ENV','AGENTRD_DEFAULT_SCENARIO','RD_AGENT_LLM_PROVIDER','RD_AGENT_LAYER0_N_CANDIDATES','RD_AGENT_LAYER0_K_FORWARD']:
    print(key, key in text)
PY
    Expected Result: 所有目标输出 True
    Evidence: .sisyphus/evidence/task-16-env-source.txt
  ```

  **Commit**: YES
  - Message: `docs(config): align env var documentation with app/config.py`
  - Files: `dev_doc/config_env_mapping.md`, `README.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. Verify dead modules are gone, config wiring landed, hasattr probes removed, cycles broken, docs corrected, evidence files exist. Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/ -q` and review changed files for accidental scope creep, swallowed exceptions, commented-out code, generic helper bloat. Output: `Tests [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA** — `unspecified-high`
  Execute every QA scenario in this plan, including import smoke tests, grep checks, targeted pytest suites, and evidence capture. Save to `.sisyphus/evidence/final-qa/`.

- [ ] F4. **Scope Fidelity Check** — `deep`
  Compare actual diff against plan. Ensure cleanup stayed cleanup: no bonus refactors, no API churn, no deleted evidence. Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- Wave 1: `chore(sisyphus): clean stale tracking metadata` + `chore: remove dead placeholder modules`
- Wave 2: `fix(engine): wire Layer-0 params from config` + `refactor(synthetic-research): remove reasoning_service dependency` + `fix: add logging to silent exception handlers`
- Wave 3: `refactor(engine): replace hasattr probes` + `refactor(runtime): break import cycles` + `refactor: remove remaining hasattr checks`
- Wave 4: `chore: remove reasoning_service` + `fix(storage): add rollback-path logging`
- Wave 5: `docs(gap-analysis): remove stale contradictions` + `docs: fix stale references across dev_doc and README` + `test(app): add app smoke coverage` + `docs(config): align env docs with app/config`

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -q
python - <<'PY'
import plugins
import exploration_manager.service
import scenarios.synthetic_research.plugin
print('ok')
PY
grep -n "hasattr(self._exploration_manager" core/loop/engine.py
grep -r "from reasoning_service\|import reasoning_service" --include="*.py" . | grep -v ".sisyphus"
```

### Final Checklist
- [ ] 4 个死代码模块已删除
- [ ] Layer-0 参数从 config 贯通到 engine 调用点
- [ ] 5 处生产代码 hasattr 已消除
- [ ] 两条循环依赖已解除
- [ ] silent swallow 与 rollback+reraise 异常处理都已修正
- [ ] paper_gap_analysis.md 不再自相矛盾
- [ ] dev_doc / README stale 引用已修复
- [ ] app 层 smoke tests 已补齐
- [ ] 环境变量文档与 `app/config.py` 对齐
- [ ] 全量测试通过
