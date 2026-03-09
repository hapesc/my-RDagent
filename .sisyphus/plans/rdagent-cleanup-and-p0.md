# RDAgent 架构清理 + 文档修补 + P0 功能实现

## TL;DR

> **Quick Summary**: 清理 my-RDagent 项目中的重复代码和死代码（main.py、demo 文件、orchestrator_rd_loop_engine），修补 PRD/架构/Spec 文档中的偏移和缺失，然后实现三个 P0 核心功能：真实 LLM Adapter（LiteLLM）、最小知识库（失败案例存储）、CoSTEER 多轮代码演化。
> 
> **Deliverables**:
> - 清理后的代码库：无死代码、无重复入口、data_models.py 精简
> - 修补后的 3 篇核心文档 + 新增 ADR 文件
> - 真实 LLM Provider 实现（LiteLLM 适配）
> - 最小知识库（memory_service 实现 + 失败案例存储/检索）
> - CoSTEER 多轮代码演化（DataScienceCoder evolve loop）
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 → Task 5 → Task 9 → Task 11 → Task 12

---

## Context

### Original Request
用户请求审查 PRD 与架构设计文档，发现 16 个问题（P0-P3），然后决定：
1. 清理双架构体系
2. 修补现有文档
3. 实现 P0 功能（LLM adapter、KB、CoSTEER）

### Interview Summary
**Key Discussions**:
- 架构清理策略: 务实整合 — 保留 System B 模块作为 System A 的组件桩，删除真正的死代码
- 文档策略: 修补现有文档，不重写
- 范围: 全部包含在一个计划中
- 测试策略: TDD（RED-GREEN-REFACTOR）

**Research Findings**:
- `core/loop/engine.py` 的 LoopEngine 直接引用 System B 的 planner、exploration_manager、memory_service 作为依赖注入组件
- `core/loop/step_executor.py` 导入 `evaluation_service.EvaluationService`
- `app/runtime.py` 的 `build_runtime()` 是体系A的真正入口，注入所有 System B 服务
- `main.py` 是老式入口，使用 `OrchestratorRDLoopEngine`，与 `app/runtime.py` 功能重复
- `test_task_01_core_models.py` 引用了 `orchestrator_rd_loop_engine`，删除时需更新测试
- LLM 只有 MockLLMProvider + LLMAdapter（带重试的 JSON 解析器）
- `llm/schemas.py` 有 ProposalDraft, CodeDraft, FeedbackDraft 三个结构化输出 schema
- 测试框架: unittest，23 个 test_task_*.py 文件

### Metis Review
Metis 咨询超时。基于深度代码审查的自有分析替代。

**自识别的潜在缺口** (已在计划中处理):
- 删除 main.py 后需要确保 CLI 入口完整可用
- data_models.py 清理需要验证没有隐藏引用
- LiteLLM 集成需要考虑 API key 配置和环境变量
- KB 实现需要决定存储后端（SQLite vs 文件）
- CoSTEER 需要 feedback 信号驱动代码修改的机制

---

## Work Objectives

### Core Objective
消除代码库中的架构混乱，更新文档反映真实状态，然后实现让系统真正可用的三个核心功能。

### Concrete Deliverables
- 删除: `main.py`, `demo_planner_loop.py`, `demo_task_intake_loop.py`, `orchestrator_rd_loop_engine/`
- 更新: `test_task_01_core_models.py` 移除对已删除代码的引用
- 精简: `data_models.py` 移除仅被删除代码使用的模型（如果有）
- 修补: `dev_doc/reverse_engineered_prd.md`, `reverse_engineered_architecture.md`, `reverse_engineered_spec.md`
- 新增: `dev_doc/adr/` 目录 + ADR 文档
- 实现: `llm/providers/litellm_provider.py` — 真实 LLM provider
- 实现: `memory_service/service.py` — 失败案例存储/检索
- 实现: CoSTEER evolve loop — 在 coding 阶段支持多轮代码改进

### Definition of Done
- [ ] `python -m pytest tests/ -v` 全部通过（含新增测试）
- [ ] `python -c "from app.runtime import build_runtime; r = build_runtime()"` 成功
- [ ] 无 import 引用到已删除的模块
- [ ] LLM adapter 可配置真实 provider 或 mock
- [ ] memory_service 可写入和查询失败案例
- [ ] CoSTEER 支持 ≥2 轮代码演化

### Must Have
- 所有现有 23 个测试继续通过（或适当更新后通过）
- LLM provider 必须支持 mock 和真实模式切换
- KB 必须使用与现有项目一致的存储模式（SQLite）
- CoSTEER 必须通过 feedback 信号决定是否继续演化

### Must NOT Have (Guardrails)
- 不引入新的 Web 框架或 ORM
- 不修改 PluginBundle 的 6 个 Protocol 接口签名（向后兼容）
- 不删除 System B 的 service 模块目录（它们是组件桩，要填充不是删除）
- 不添加 React/Vue 前端
- 不实现完整的 RAG 管道（只做最小 KB）
- 不添加 Docker 相关的新依赖或基础设施变更
- 不过度抽象：每个新文件必须有明确的单一职责
- 不添加未使用的"未来扩展"代码

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (unittest, 23 test files)
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: unittest (保持与现有测试一致)
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Module/Library**: Use Bash (python -c / python -m pytest) — Import, call functions, compare output
- **CLI**: Use Bash — Run CLI commands, validate output
- **API**: Use Bash (curl) — Send requests, assert status + response fields

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — cleanup + foundation):
├── Task 1: Delete dead code files [quick]
├── Task 2: Clean data_models.py [quick]
├── Task 3: Update test_task_01 for deleted modules [quick]
├── Task 4: Add ADR document [writing]
├── Task 5: LLM provider config schema + env vars [quick]

Wave 2 (After Wave 1 — docs + LLM provider):
├── Task 6: Patch PRD document [writing]
├── Task 7: Patch architecture document [writing]
├── Task 8: Patch spec document [writing]
├── Task 9: Implement LiteLLM provider (depends: 5) [deep]
├── Task 10: Integrate LLM provider into runtime (depends: 5, 9) [unspecified-high]

Wave 3 (After Wave 2 — KB + CoSTEER):
├── Task 11: Implement minimal Knowledge Base (depends: 9) [deep]
├── Task 12: Implement CoSTEER multi-round evolution (depends: 9, 11) [deep]

Wave 4 (After Wave 3 — integration + verification):
├── Task 13: Integration test: full loop with real LLM mock (depends: 10, 11, 12) [deep]
├── Task 14: Update main.py to use app/runtime (depends: 1, 10) [quick]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 5 → Task 9 → Task 11 → Task 12 → Task 13 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 3, 14 |
| 2 | — | 3 |
| 3 | 1, 2 | 13 |
| 4 | — | — |
| 5 | — | 9, 10 |
| 6 | — | — |
| 7 | — | — |
| 8 | — | — |
| 9 | 5 | 10, 11, 12 |
| 10 | 5, 9 | 13, 14 |
| 11 | 9 | 12, 13 |
| 12 | 9, 11 | 13 |
| 13 | 10, 11, 12 | F1-F4 |
| 14 | 1, 10 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 5 tasks — T1→`quick`, T2→`quick`, T3→`quick`, T4→`writing`, T5→`quick`
- **Wave 2**: 5 tasks — T6→`writing`, T7→`writing`, T8→`writing`, T9→`deep`, T10→`unspecified-high`
- **Wave 3**: 2 tasks — T11→`deep`, T12→`deep`
- **Wave 4**: 2 tasks — T13→`deep`, T14→`quick`
- **FINAL**: 4 tasks — F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep`

---

## TODOs

- [ ] 1. 删除死代码文件

  **What to do**:
  - 删除以下文件/目录：
    - `main.py` — 老式入口，使用 OrchestratorRDLoopEngine，与 app/runtime.py 重复
    - `demo_planner_loop.py` — 体系B的 demo 脚本
    - `demo_task_intake_loop.py` — 体系B的 demo 脚本
    - `orchestrator_rd_loop_engine/` — 整个目录（简化版循环引擎，与 core/loop/engine.py 重复）
  - 验证删除后没有 broken imports

  **Must NOT do**:
  - 不删除 System B 的 service 模块（memory_service, planner 等）— 它们是体系A的组件
  - 不修改 app/ 目录下任何文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的文件删除操作，低风险
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: 只是删除文件，不需要复杂 git 操作

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Tasks 3, 14
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `main.py` — 要删除的老式入口，180行，使用 OrchestratorRDLoopEngine
  - `demo_planner_loop.py` — 要删除的 demo，36行
  - `demo_task_intake_loop.py` — 要删除的 demo，217行
  - `orchestrator_rd_loop_engine/service.py` — 要删除的简化版循环引擎，84行

  **WHY Each Reference Matters**:
  - 这些文件都使用 `OrchestratorRDLoopEngine` 而非 `core/loop/engine.py` 的 `LoopEngine`
  - 真正的运行时入口在 `app/runtime.py` 的 `build_runtime()` + `build_run_service()`

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 删除前运行 `python -m pytest tests/ -v`，记录当前通过数（预期部分测试会引用 orchestrator）
  - [ ] Task 3 将处理测试更新

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 验证死代码已删除
    Tool: Bash
    Preconditions: 文件存在于工作区
    Steps:
      1. 运行: rm main.py demo_planner_loop.py demo_task_intake_loop.py
      2. 运行: rm -rf orchestrator_rd_loop_engine/
      3. 运行: grep -r 'orchestrator_rd_loop_engine' --include='*.py' . | grep -v __pycache__ | grep -v .sisyphus
      4. 断言: grep 命令只返回 test_task_01 中的引用（将由 Task 3 处理）
    Expected Result: 4 个文件/目录已删除，grep 只在 test_task_01 中有残留引用
    Failure Indicators: 删除后 app/ 目录下有 broken import
    Evidence: .sisyphus/evidence/task-1-dead-code-removed.txt

  Scenario: 验证 app/runtime.py 不受影响
    Tool: Bash
    Preconditions: 死代码已删除
    Steps:
      1. 运行: python -c "from app.runtime import build_runtime"
      2. 断言: 无 ImportError
    Expected Result: import 成功，退出码 0
    Failure Indicators: ImportError 提到 orchestrator_rd_loop_engine
    Evidence: .sisyphus/evidence/task-1-runtime-intact.txt
  ```

  **Commit**: YES (groups with T2, T3)
  - Message: `refactor(cleanup): remove dead code and duplicate orchestrator`
  - Files: `main.py`, `demo_planner_loop.py`, `demo_task_intake_loop.py`, `orchestrator_rd_loop_engine/`
  - Pre-commit: `python -c "from app.runtime import build_runtime"`

- [ ] 2. 清理 data_models.py 中的死代码

  **What to do**:
  - 分析 `data_models.py` 中每个 dataclass 的使用情况
  - 确认哪些模型只被已删除文件引用（main.py, demo 文件, orchestrator_rd_loop_engine）
  - 注意：大部分 System B 模型（ExplorationGraph, NodeRecord, PlanningContext, Plan, Proposal 等）被 `core/loop/engine.py` 和其他活跃代码引用，不能删除
  - 可能可以删除的候选：`PhaseResultMeta`（检查是否只被 demo 和 orchestrator 使用）
  - 使用 `grep -r "ClassName" --include='*.py'` 验证每个模型的引用

  **Must NOT do**:
  - 不删除被 core/ 或 app/ 引用的模型
  - 不重命名任何模型

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 搜索引用 + 删除未使用代码，逻辑简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `data_models.py:260-431` — 后半部分模型（TaskSpec 到 PhaseResultMeta），这些是清理候选区
  - `core/loop/engine.py:12-23` — LoopEngine 的 imports，确认哪些 data_models 被使用
  - `app/runtime.py` — runtime 的 imports

  **API/Type References**:
  - `data_models.py:298-302` — ExplorationGraph（被 engine.py 使用，不能删）
  - `data_models.py:324-331` — Plan（被 planner/service.py 和 engine.py 使用，不能删）
  - `data_models.py:364-370` — LoopState（被 engine.py 使用，不能删）
  - `data_models.py:425-431` — PhaseResultMeta（需检查：可能只被 demo 使用）

  **WHY Each Reference Matters**:
  - 删除任何被活跃代码引用的模型会导致 ImportError
  - 必须逐一 grep 验证后再删除

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 运行 `grep -r "PhaseResultMeta" --include='*.py' .` 确认引用范围
  - [ ] 如果模型只被已删除文件引用，删除该模型
  - [ ] 运行 `python -c "from data_models import *"` 验证模块仍可导入

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: data_models.py 仍然完整可用
    Tool: Bash
    Preconditions: 清理完成
    Steps:
      1. 运行: python -c "from data_models import RunSession, ExperimentNode, Event, ExplorationGraph, NodeRecord, PlanningContext, LoopState, LoopContext, BudgetLedger, Plan, Proposal, ContextPack"
      2. 断言: 所有核心模型仍可导入
    Expected Result: import 成功，退出码 0
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task-2-models-intact.txt

  Scenario: 无孤立模型引用
    Tool: Bash
    Preconditions: 死代码文件已删除（Task 1）
    Steps:
      1. 对 data_models.py 中每个 class，运行 grep 检查引用
      2. 验证每个剩余的 class 至少被一个非测试文件引用
    Expected Result: 所有保留的模型都有至少一个活跃引用
    Evidence: .sisyphus/evidence/task-2-no-orphan-models.txt
  ```

  **Commit**: YES (groups with T1, T3)
  - Message: `refactor(cleanup): remove dead code and duplicate orchestrator`
  - Files: `data_models.py`
  - Pre-commit: `python -c "from data_models import *"`

- [ ] 3. 更新 test_task_01 测试文件

  **What to do**:
  - 更新 `tests/test_task_01_core_models.py`：
    - 移除 `from orchestrator_rd_loop_engine import ...` (第21行)
    - 移除 `test_orchestrator_uses_run_status_enum` 测试方法（第86-96行）
    - 从 `ModelLayerUsageTests.test_core_services_import_model_layer` 中移除 `"orchestrator_rd_loop_engine/service.py"` (第114行)
    - 如果 data_models.py 中删除了 PhaseResultMeta，检查测试中是否有引用
  - 运行测试确认全部通过

  **Must NOT do**:
  - 不修改其他测试文件
  - 不删除与 System B 服务相关的测试（memory_service, planner 等仍然存在）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的测试文件修改
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (但逻辑上依赖 T1, T2)
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `tests/test_task_01_core_models.py:21` — `from orchestrator_rd_loop_engine import OrchestratorConfig, OrchestratorRDLoopEngine` (要删除的 import)
  - `tests/test_task_01_core_models.py:86-96` — `test_orchestrator_uses_run_status_enum` 方法（要删除）
  - `tests/test_task_01_core_models.py:114` — `"orchestrator_rd_loop_engine/service.py"` 在文件列表中（要删除）

  **WHY Each Reference Matters**:
  - 第21行的 import 会因为 orchestrator_rd_loop_engine 被删除而失败
  - 第86-96行的测试方法测试的是被删除的模块
  - 第114行的文件路径验证会因为文件不存在而失败

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 修改后运行: `python -m pytest tests/test_task_01_core_models.py -v` → 全部 PASS
  - [ ] 运行: `python -m pytest tests/ -v` → 全部 PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 所有测试通过
    Tool: Bash
    Preconditions: Task 1 和 Task 2 已完成
    Steps:
      1. 运行: python -m pytest tests/ -v
      2. 断言: 退出码 0，所有测试 PASS
    Expected Result: 23个测试全部通过（减去删除的1-2个）
    Failure Indicators: 任何 FAIL 或 ERROR
    Evidence: .sisyphus/evidence/task-3-all-tests-pass.txt

  Scenario: test_task_01 不再引用 orchestrator
    Tool: Bash
    Preconditions: 文件已修改
    Steps:
      1. 运行: grep 'orchestrator_rd_loop_engine' tests/test_task_01_core_models.py
      2. 断言: 无匹配
    Expected Result: grep 退出码 1（无匹配）
    Evidence: .sisyphus/evidence/task-3-no-orchestrator-ref.txt
  ```

  **Commit**: YES (groups with T1, T2)
  - Message: `refactor(cleanup): remove dead code and duplicate orchestrator`
  - Files: `tests/test_task_01_core_models.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 4. 添加 ADR (Architecture Decision Records) 文档

  **What to do**:
  - 创建 `dev_doc/adr/` 目录
  - 创建以下 ADR 文件：
    - `001-sqlite-for-mvp.md` — 为什么 MVP 选择 SQLite 而非 PostgreSQL
    - `002-streamlit-ui.md` — 为什么选择 Streamlit 而非 React
    - `003-zip-checkpoint.md` — 为什么 checkpoint 用 zip 而非 git
    - `004-plugin-protocol.md` — 为什么用 Python Protocol 而非 ABC
    - `005-dual-architecture-cleanup.md` — 记录本次清理决策：System B 是组件桩而非独立架构
  - 每个 ADR 遵循标准格式：Title, Status, Context, Decision, Consequences

  **Must NOT do**:
  - 不修改任何代码文件
  - 不添加与架构决策无关的文档

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档写作任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `core/storage/interfaces.py` — SQLite 存储抽象，理解 SQLite 选择原因
  - `ui/trace_ui.py` — Streamlit UI 实现
  - `core/execution/workspace_manager.py` — zip checkpoint 实现
  - `plugins/contracts.py` — Protocol 接口定义

  **External References**:
  - ADR 标准格式: https://adr.github.io/

  **WHY Each Reference Matters**:
  - 需要理解每个技术选择的上下文才能写出准确的 ADR
  - 005 号 ADR 特别重要，记录了本次清理的完整上下文和决策依据

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: ADR 文件存在且格式正确
    Tool: Bash
    Preconditions: 无
    Steps:
      1. 运行: ls dev_doc/adr/
      2. 断言: 至少 5 个 .md 文件
      3. 运行: head -5 dev_doc/adr/001-sqlite-for-mvp.md
      4. 断言: 包含 "# " 标题和 "## Status" section
    Expected Result: 5 个 ADR 文件，格式符合标准
    Failure Indicators: 文件不存在或缺少必要 section
    Evidence: .sisyphus/evidence/task-4-adr-created.txt

  Scenario: ADR 005 记录了双架构清理决策
    Tool: Bash
    Steps:
      1. 运行: cat dev_doc/adr/005-dual-architecture-cleanup.md
      2. 断言: 包含 "orchestrator_rd_loop_engine", "System A", "System B", "component stubs"
    Expected Result: ADR 完整记录了清理上下文和决策
    Evidence: .sisyphus/evidence/task-4-adr-005-content.txt
  ```

  **Commit**: YES (standalone)
  - Message: `docs(adr): add architecture decision records`
  - Files: `dev_doc/adr/*.md`

- [ ] 5. LLM Provider 配置 schema + 环境变量

  **What to do**:
  - 在 `app/config.py` 中添加 LLM provider 配置字段：
    - `llm_provider`: str (default: "mock") — 可选值: "mock", "litellm"
    - `llm_api_key`: Optional[str] — 从环境变量 `RD_AGENT_LLM_API_KEY` 读取
    - `llm_model`: str (default: "gpt-4o-mini") — 默认模型
    - `llm_base_url`: Optional[str] — 可选的 API base URL
  - 更新 `dev_doc/config_env_mapping.md` 添加新的环境变量说明
  - TDD: 先写配置解析测试

  **Must NOT do**:
  - 不实现 LLM provider 本身（Task 9 负责）
  - 不安装任何 pip 包
  - 不硬编码 API key

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的配置扩展
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `app/config.py` — 现有配置模式，理解如何添加新字段
  - `dev_doc/config_env_mapping.md` — 现有环境变量映射文档

  **API/Type References**:
  - `service_contracts.py:16-79` — ModelSelectorConfig，已有的 LLM 配置结构

  **WHY Each Reference Matters**:
  - 必须遵循 app/config.py 的现有模式（dataclass + 环境变量读取）
  - ModelSelectorConfig 已定义了 provider/model/temperature 等字段，新配置需要与之对齐

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_llm_config.py`
  - [ ] 测试: 默认配置 llm_provider="mock"
  - [ ] 测试: 环境变量 RD_AGENT_LLM_API_KEY 被正确读取
  - [ ] 测试: llm_provider="litellm" 时 llm_api_key 为 None 应该报警告

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 默认配置使用 mock provider
    Tool: Bash
    Preconditions: 无 RD_AGENT_LLM_ 环境变量设置
    Steps:
      1. 运行: python -c "from app.config import load_config; c = load_config(); print(c.llm_provider)"
      2. 断言: 输出 "mock"
    Expected Result: "mock"
    Failure Indicators: ImportError 或输出非 "mock"
    Evidence: .sisyphus/evidence/task-5-default-config.txt

  Scenario: 环境变量覆盖配置
    Tool: Bash
    Steps:
      1. 运行: RD_AGENT_LLM_PROVIDER=litellm RD_AGENT_LLM_API_KEY=test123 python -c "from app.config import load_config; c = load_config(); print(c.llm_provider, c.llm_api_key)"
      2. 断言: 输出 "litellm test123"
    Expected Result: "litellm test123"
    Evidence: .sisyphus/evidence/task-5-env-override.txt
  ```

  **Commit**: YES (groups with T9, T10)
  - Message: `feat(llm): add real LLM provider via LiteLLM`
  - Files: `app/config.py`, `tests/test_llm_config.py`, `dev_doc/config_env_mapping.md`

- [ ] 6. 修补 PRD 文档

  **What to do**:
  - 修补 `dev_doc/reverse_engineered_prd.md`：
    - §7.2 V1 Scope：删除 "multiple scenario plugins" 措辞，改为 "two built-in scenario plugins (data_science, synthetic_research)"
    - §FR-016 Knowledge Base：将 "should" 改为 "will be implemented in MVP as minimal failure-case store"（因为本计划会实现）
    - §16 Open Decisions：逐条更新状态，标注哪些已在代码中隐式决策（如 event store 已抽象为 SQLiteMetadataStore）
    - 添加 "Implementation Status" 小节：对每个 FR 标注 ✅ Implemented / 🔧 Partial / ❌ Not Started
    - 修正任何声称 V1 有但实际不存在的功能描述
  - 不改变 PRD 的整体结构和章节编号

  **Must NOT do**:
  - 不重写 PRD 全文
  - 不添加 V2 或 V3 范围
  - 不删除现有 Functional Requirements 编号

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档修补任务，需要准确的文字表达
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不涉及浏览器

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9, 10)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `dev_doc/reverse_engineered_prd.md:220-250` — §7.2 V1 Scope 部分，声称 "multiple scenario plugins"
  - `dev_doc/reverse_engineered_prd.md:340-360` — FR-016 Knowledge Base requirement
  - `dev_doc/reverse_engineered_prd.md:500-537` — §16 Open Decisions 部分

  **API/Type References**:
  - `scenarios/data_science/` — 实际只有 data_science 和 synthetic_research 两个场景
  - `core/storage/interfaces.py` — EventMetadataStore 已抽象（回答了 Open Decision）
  - `memory_service/service.py` — KB 当前是空壳（修补后将注明"实现中"）

  **WHY Each Reference Matters**:
  - 需要对照实际代码验证 PRD 声明的准确性
  - Open Decisions 需要逐条与代码对比来确定是否已决策

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PRD 中不再有虚假声明
    Tool: Bash
    Steps:
      1. 运行: grep -n "multiple scenario plugins" dev_doc/reverse_engineered_prd.md
      2. 断言: 无匹配（已修正为 "two built-in"）
      3. 运行: grep -c "Implementation Status" dev_doc/reverse_engineered_prd.md
      4. 断言: 至少 1 个匹配
    Expected Result: 虚假声明已修正，Implementation Status section 存在
    Failure Indicators: grep 仍能找到 "multiple scenario plugins"
    Evidence: .sisyphus/evidence/task-6-prd-patched.txt

  Scenario: Open Decisions 已有更新状态
    Tool: Bash
    Steps:
      1. 运行: grep -A2 "Open Decision" dev_doc/reverse_engineered_prd.md | grep -c "decided\|resolved\|implemented"
      2. 断言: 至少 2 个匹配（至少两个 OD 已标注解决）
    Expected Result: Open Decisions 不再全是 "open" 状态
    Evidence: .sisyphus/evidence/task-6-open-decisions-updated.txt
  ```

  **Commit**: YES (groups with T7, T8)
  - Message: `docs: patch PRD, architecture, and spec to match implementation`
  - Files: `dev_doc/reverse_engineered_prd.md`

- [ ] 7. 修补架构文档

  **What to do**:
  - 修补 `dev_doc/reverse_engineered_architecture.md`：
    - §5（或对应位置）Component Diagram：更新描述，明确 System B 服务模块是 System A 的依赖注入组件，而非独立架构
    - 添加注解说明 `app/runtime.py` 是真正的组装点，注入 planner/exploration_manager/memory_service/evaluation_service
    - §G5 Evolvable：添加注解说明 CoSTEER multi-round 正在本版本实现
    - 修正任何暗示存在"两套独立架构"的描述
    - 添加 "Architecture Reality vs Design" 小节：总结哪些设计已落地，哪些是桩
  - 保持架构文档的整体结构

  **Must NOT do**:
  - 不重写整篇架构文档
  - 不画新的架构图（只修正文字描述）
  - 不删除非目标章节

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档修补任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 8, 9, 10)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `dev_doc/reverse_engineered_architecture.md:1-30` — Design Goals G1-G7
  - `app/runtime.py:48-83` — `build_runtime()` 展示了真实的组装方式：所有 System B 服务被注入
  - `app/runtime.py:86-114` — `build_run_service()` 展示了 LoopEngine 如何使用 planner/exploration_manager/memory_service
  - `core/loop/engine.py:1-30` — LoopEngine 的依赖声明

  **WHY Each Reference Matters**:
  - 架构文档必须反映 `build_runtime()` 中实际的依赖注入关系
  - G5 Evolvable 需要更新，因为 CoSTEER 正在实现

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 架构文档反映真实依赖关系
    Tool: Bash
    Steps:
      1. 运行: grep -c "runtime.py\|build_runtime\|dependency injection" dev_doc/reverse_engineered_architecture.md
      2. 断言: 至少 1 个匹配（提到了真实入口点）
      3. 运行: grep -c "Architecture Reality\|Implementation Status" dev_doc/reverse_engineered_architecture.md
      4. 断言: 至少 1 个匹配（有现实 vs 设计的对照）
    Expected Result: 文档包含对真实架构的描述
    Failure Indicators: 文档仍暗示两套独立架构
    Evidence: .sisyphus/evidence/task-7-arch-patched.txt

  Scenario: 不再暗示 System B 是独立架构
    Tool: Bash
    Steps:
      1. 运行: grep -ci "independent.*architecture\|separate.*system\|dual.*architecture" dev_doc/reverse_engineered_architecture.md
      2. 断言: 0 个匹配
    Expected Result: 不存在暗示双独立架构的措辞
    Evidence: .sisyphus/evidence/task-7-no-dual-arch.txt
  ```

  **Commit**: YES (groups with T6, T8)
  - Message: `docs: patch PRD, architecture, and spec to match implementation`
  - Files: `dev_doc/reverse_engineered_architecture.md`

- [ ] 8. 修补 Spec 文档

  **What to do**:
  - 修补 `dev_doc/reverse_engineered_spec.md`：
    - §6.3（或对应的 CoSTEER 章节）：更新为"正在本版本实现"
    - 添加 "Implementation Mapping" 表格：每个 Spec 功能对应的实际代码文件和状态
    - 修正任何声称已实现但实际未实现的功能描述
    - 更新 LLM 相关描述：明确当前有 MockLLMProvider + 正在添加 LiteLLM
    - 确保测试章节引用正确的测试文件路径和数量
  - 保持 Spec 文档的整体结构和编号

  **Must NOT do**:
  - 不重写 Spec
  - 不添加新的功能规格（只修补现有的）

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档修补任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 9, 10)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `dev_doc/reverse_engineered_spec.md:1-30` — 文档结构和目的
  - `core/loop/step_executor.py:147-173` — coding 阶段当前实现（单次 `coder.develop()`，无 evolve loop）
  - `llm/adapter.py:14-19` — LLMProvider Protocol 定义
  - `llm/adapter.py:21-81` — MockLLMProvider 实现

  **API/Type References**:
  - `plugins/contracts.py:72-81` — Coder Protocol（CoSTEER 将在此基础上扩展）
  - `llm/schemas.py:1-55` — 三个结构化输出 schema

  **WHY Each Reference Matters**:
  - Spec 中描述的 CoSTEER 机制需要与实际代码对照
  - LLM 章节需要准确反映 MockLLMProvider → LiteLLM 的演进

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Spec 包含 Implementation Mapping
    Tool: Bash
    Steps:
      1. 运行: grep -c "Implementation Mapping\|实现映射" dev_doc/reverse_engineered_spec.md
      2. 断言: 至少 1 个匹配
      3. 运行: grep -c "step_executor\|coder.develop\|LoopEngine" dev_doc/reverse_engineered_spec.md
      4. 断言: 至少 2 个匹配（引用了实际代码路径）
    Expected Result: Spec 包含到实际代码的映射
    Failure Indicators: Spec 仍然是纯概念描述，无代码引用
    Evidence: .sisyphus/evidence/task-8-spec-patched.txt

  Scenario: LLM 描述准确
    Tool: Bash
    Steps:
      1. 运行: grep -c "MockLLMProvider\|LiteLLM\|litellm" dev_doc/reverse_engineered_spec.md
      2. 断言: 至少 1 个匹配（提到了 LLM 实现状态）
    Expected Result: Spec 反映 LLM 的真实状态
    Evidence: .sisyphus/evidence/task-8-llm-description.txt
  ```

  **Commit**: YES (groups with T6, T7)
  - Message: `docs: patch PRD, architecture, and spec to match implementation`
  - Files: `dev_doc/reverse_engineered_spec.md`

- [ ] 9. 实现 LiteLLM Provider

  **What to do**:
  - 创建 `llm/providers/` 目录和 `__init__.py`
  - 创建 `llm/providers/litellm_provider.py`：
    - 实现 `LiteLLMProvider` 类，遵循 `LLMProvider` Protocol（`complete(prompt, model_config) -> str`）
    - 使用 `litellm` 库的 `completion()` API
    - 支持参数：`api_key`, `model`（默认 "gpt-4o-mini"）, `base_url`（可选）
    - 从 `model_config: ModelSelectorConfig` 提取 provider/model/temperature/max_tokens
    - 错误处理：API 超时、认证失败、速率限制 — 全部抛出带有明确错误消息的异常
    - 不自行实现重试（LLMAdapter 已有重试机制）
  - 更新 `llm/__init__.py` 导出新 provider
  - TDD: 先写测试（使用 mock 替代真实 API 调用）

  **Must NOT do**:
  - 不硬编码 API key
  - 不实现自己的重试逻辑（LLMAdapter 已有）
  - 不修改 LLMProvider Protocol 签名
  - 不修改 MockLLMProvider

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要正确实现外部 API 集成，理解 LiteLLM 库 API，处理各种错误场景
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不涉及浏览器

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 5 config)
  - **Parallel Group**: Wave 2 (但依赖 Task 5)
  - **Blocks**: Tasks 10, 11, 12
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `llm/adapter.py:14-19` — `LLMProvider` Protocol 定义：`complete(prompt, model_config) -> str`。新 provider 必须严格实现此签名
  - `llm/adapter.py:21-81` — `MockLLMProvider` 实现：展示了如何处理 `model_config` 参数和不同 prompt 前缀
  - `llm/adapter.py:91-120` — `LLMAdapter.generate_structured()`：展示了 provider 如何被调用，返回值如何被解析

  **API/Type References**:
  - `service_contracts.py:16-79` — `ModelSelectorConfig` 定义：provider, model, temperature, max_tokens, max_retries 字段
  - `llm/schemas.py:1-55` — ProposalDraft, CodeDraft, FeedbackDraft：LLM 返回的 JSON 必须可被解析为这些结构

  **External References**:
  - LiteLLM 官方文档: `https://docs.litellm.ai/docs/` — completion() API, 支持的 providers, 错误处理
  - LiteLLM GitHub: `https://github.com/BerriAI/litellm` — 参考实际使用方式

  **WHY Each Reference Matters**:
  - `LLMProvider` Protocol 是必须遵循的接口契约，签名不能偏离
  - `ModelSelectorConfig` 是配置传递方式，需要正确从中提取 model/temperature 等参数
  - LiteLLM 文档是实现的权威来源，特别是 `completion()` 函数签名和参数映射

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_litellm_provider.py`
  - [ ] RED: 测试 `LiteLLMProvider` 实现 `LLMProvider` Protocol
  - [ ] RED: 测试 `complete()` 调用 litellm.completion() 并返回 content
  - [ ] RED: 测试 API 错误抛出有意义的异常
  - [ ] RED: 测试 `model_config` 参数正确传递给 litellm
  - [ ] GREEN: 所有测试通过
  - [ ] `python -m pytest tests/test_litellm_provider.py -v` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: LiteLLMProvider 遵循 LLMProvider Protocol
    Tool: Bash
    Preconditions: litellm 已安装 (pip install litellm)
    Steps:
      1. 运行: python -c "from llm.providers.litellm_provider import LiteLLMProvider; from llm.adapter import LLMProvider; assert isinstance(LiteLLMProvider(api_key='test'), LLMProvider); print('Protocol OK')"
      2. 断言: 输出 "Protocol OK"
    Expected Result: LiteLLMProvider 满足 LLMProvider Protocol
    Failure Indicators: isinstance 返回 False 或 ImportError
    Evidence: .sisyphus/evidence/task-9-protocol-check.txt

  Scenario: LiteLLMProvider 与 LLMAdapter 集成
    Tool: Bash
    Preconditions: 使用 unittest.mock 替代真实 API
    Steps:
      1. 运行: python -c "
      from unittest.mock import patch, MagicMock
      from llm.providers.litellm_provider import LiteLLMProvider
      from llm.adapter import LLMAdapter
      from llm.schemas import ProposalDraft
      mock_response = MagicMock()
      mock_response.choices = [MagicMock()]
      mock_response.choices[0].message.content = '{\"summary\": \"test\", \"constraints\": [], \"virtual_score\": 0.5}'
      with patch('litellm.completion', return_value=mock_response):
          provider = LiteLLMProvider(api_key='test')
          adapter = LLMAdapter(provider)
          result = adapter.generate_structured('proposal: test', ProposalDraft)
          print(f'summary={result.summary}')
      "
      2. 断言: 输出 "summary=test"
    Expected Result: Provider + Adapter 链路工作正常
    Failure Indicators: JSON parse error 或 AttributeError
    Evidence: .sisyphus/evidence/task-9-adapter-integration.txt

  Scenario: API 错误产生有意义的异常
    Tool: Bash
    Steps:
      1. 运行: python -c "
      from unittest.mock import patch
      from llm.providers.litellm_provider import LiteLLMProvider
      import litellm
      with patch('litellm.completion', side_effect=litellm.AuthenticationError(message='bad key', model='gpt-4o-mini', llm_provider='openai')):
          provider = LiteLLMProvider(api_key='bad')
          try:
              provider.complete('test')
              print('FAIL: no exception')
          except Exception as e:
              print(f'OK: {type(e).__name__}')
      "
      2. 断言: 输出包含 "OK:" 且有异常类型名
    Expected Result: 认证错误被正确传播
    Evidence: .sisyphus/evidence/task-9-error-handling.txt
  ```

  **Commit**: YES (groups with T5, T10)
  - Message: `feat(llm): add real LLM provider via LiteLLM`
  - Files: `llm/providers/__init__.py`, `llm/providers/litellm_provider.py`, `llm/__init__.py`, `tests/test_litellm_provider.py`
  - Pre-commit: `python -m pytest tests/test_litellm_provider.py -v`

- [ ] 10. 将 LLM Provider 集成到 Runtime

  **What to do**:
  - 修改 `app/runtime.py` 的 `build_runtime()`：
    - 读取 `config.llm_provider`（来自 Task 5）
    - 如果 `llm_provider == "mock"`：使用 `MockLLMProvider()`
    - 如果 `llm_provider == "litellm"`：使用 `LiteLLMProvider(api_key=config.llm_api_key, model=config.llm_model, base_url=config.llm_base_url)`
    - 创建 `LLMAdapter(provider)` 并存入 `RuntimeContext`
  - 扩展 `RuntimeContext` dataclass 添加 `llm_adapter: LLMAdapter` 字段
  - 修改 `build_run_service()` 将 `llm_adapter` 传递给需要它的组件
  - 确保现有测试不受影响（默认仍使用 mock）
  - TDD: 先写测试验证 provider 选择逻辑

  **Must NOT do**:
  - 不修改 LLMAdapter 类本身
  - 不修改 PluginBundle 的 Protocol 签名
  - 不在 runtime.py 中硬编码 API key
  - 不改变 build_runtime() 的无参调用签名（默认行为不变）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 修改核心运行时组装逻辑，需要理解依赖注入关系
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (depends on T5, T9)
  - **Blocks**: Tasks 13, 14
  - **Blocked By**: Tasks 5, 9

  **References**:

  **Pattern References**:
  - `app/runtime.py:48-83` — `build_runtime()` 当前实现：所有服务的组装点。新的 LLM provider 选择逻辑加在 config 读取之后
  - `app/runtime.py:32-45` — `RuntimeContext` dataclass：需要添加 `llm_adapter` 字段
  - `app/runtime.py:86-114` — `build_run_service()`：如果 scenario plugins 需要 LLM，在这里传递

  **API/Type References**:
  - `app/config.py` — 扩展后将包含 `llm_provider`, `llm_api_key`, `llm_model`, `llm_base_url` 字段（Task 5 产出）
  - `llm/adapter.py:84-120` — `LLMAdapter` 构造函数：接受 `LLMProvider` + optional `LLMAdapterConfig`
  - `llm/adapter.py:14-19` — `LLMProvider` Protocol

  **WHY Each Reference Matters**:
  - `build_runtime()` 是唯一的组装点，所有新依赖必须在这里注入
  - `RuntimeContext` 是运行时上下文的容器，`llm_adapter` 必须成为其成员
  - 需要确保默认行为（无环境变量时）仍然使用 MockLLMProvider

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_runtime_llm.py`
  - [ ] RED: 测试默认配置 → RuntimeContext.llm_adapter 使用 MockLLMProvider
  - [ ] RED: 测试 llm_provider="litellm" → RuntimeContext.llm_adapter 使用 LiteLLMProvider
  - [ ] GREEN: 所有测试通过
  - [ ] 现有 `python -m pytest tests/ -v` 全部 PASS（回归验证）

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 默认 runtime 仍使用 MockLLMProvider
    Tool: Bash
    Preconditions: 无 RD_AGENT_LLM_ 环境变量
    Steps:
      1. 运行: python -c "from app.runtime import build_runtime; r = build_runtime(); print(type(r.llm_adapter._provider).__name__)"
      2. 断言: 输出 "MockLLMProvider"
    Expected Result: 默认行为不变
    Failure Indicators: 输出非 MockLLMProvider 或 AttributeError
    Evidence: .sisyphus/evidence/task-10-default-mock.txt

  Scenario: 配置 litellm 时使用 LiteLLMProvider
    Tool: Bash
    Steps:
      1. 运行: RD_AGENT_LLM_PROVIDER=litellm RD_AGENT_LLM_API_KEY=test123 python -c "from app.runtime import build_runtime; r = build_runtime(); print(type(r.llm_adapter._provider).__name__)"
      2. 断言: 输出 "LiteLLMProvider"
    Expected Result: LiteLLM provider 正确创建
    Failure Indicators: 输出非 LiteLLMProvider 或 ImportError
    Evidence: .sisyphus/evidence/task-10-litellm-selected.txt

  Scenario: 所有现有测试仍通过
    Tool: Bash
    Steps:
      1. 运行: python -m pytest tests/ -v
      2. 断言: 退出码 0，无 FAIL
    Expected Result: 回归测试全部通过
    Failure Indicators: 任何 FAIL 或 ERROR
    Evidence: .sisyphus/evidence/task-10-regression.txt
  ```

  **Commit**: YES (groups with T5, T9)
  - Message: `feat(llm): add real LLM provider via LiteLLM`
  - Files: `app/runtime.py`, `tests/test_runtime_llm.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 11. 实现最小 Knowledge Base（失败案例存储）

  **What to do**:
  - 重写 `memory_service/service.py`（当前是空壳，74行）：
    - 保持 `MemoryServiceConfig` 和 `MemoryService` 的类名和公共接口不变
    - 添加 `db_path: str` 到 `MemoryServiceConfig`（默认 `:memory:` 用于测试，实际使用 `config.sqlite_path` 同库）
    - `__init__`: 创建 SQLite 连接，建表 `failure_cases`（id, item TEXT, metadata JSON, created_at TIMESTAMP）
    - `write_memory(item, metadata)`: INSERT 到 failure_cases 表
    - `query_context(query)`: SELECT 匹配 metadata 的记录，返回 `ContextPack(items=[...], highlights=[...])`
      - 匹配策略：简单的 JSON 键值匹配（WHERE metadata LIKE '%key%' AND metadata LIKE '%value%'）
      - 限制返回数量为 `config.max_context_items`
    - `get_memory_stats()`: 返回 `{"items": count}`
  - 更新 `memory_service/__init__.py` 确保导出正确
  - TDD: 先写测试覆盖写入、查询、空查询、统计

  **Must NOT do**:
  - 不实现完整的 RAG 管道（只做 SQLite 键值匹配）
  - 不引入向量数据库或 embedding
  - 不修改 `ContextPack` dataclass 定义
  - 不修改 `MemoryService` 的公共方法签名（向后兼容）
  - 不引入新的 ORM（直接用 sqlite3 标准库）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要正确实现 SQLite 存储逻辑，处理 JSON 序列化/查询，确保线程安全
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T9)
  - **Parallel Group**: Wave 3 (with Task 12)
  - **Blocks**: Tasks 12, 13
  - **Blocked By**: Task 9 (需要 LLM provider 存在才能组装完整链路)

  **References**:

  **Pattern References**:
  - `memory_service/service.py:1-74` — 当前空壳实现，保持接口签名一致
  - `core/storage/interfaces.py` — SQLite 存储的现有模式，参考如何使用 sqlite3 连接和事务管理
  - `core/storage/__init__.py` — 现有的 SQLiteMetadataStore，参考建表和查询模式

  **API/Type References**:
  - `data_models.py:398-403` — `ContextPack(items: List[str], highlights: List[str])` — 必须返回此结构
  - `memory_service/service.py:12-16` — `MemoryServiceConfig(max_context_items=10, index_backend="in_memory")` — 保持兼容，添加 db_path
  - `app/runtime.py:67` — `MemoryService(MemoryServiceConfig())` — build_runtime 中的调用方式，默认参数必须仍然可用

  **WHY Each Reference Matters**:
  - 空壳的接口签名是契约，不能破坏
  - `ContextPack` 是下游消费者（LoopEngine/StepExecutor）期望的类型
  - `build_runtime()` 使用默认参数创建 MemoryService，默认行为必须正常工作

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_memory_service.py`
  - [ ] RED: 测试 `write_memory` 后 `get_memory_stats()` 返回 `{"items": 1}`
  - [ ] RED: 测试 `write_memory` + `query_context` 返回包含该 item 的 ContextPack
  - [ ] RED: 测试空数据库 `query_context` 返回空 ContextPack
  - [ ] RED: 测试 `max_context_items` 限制生效
  - [ ] GREEN: 所有测试通过
  - [ ] `python -m pytest tests/test_memory_service.py -v` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 写入和查询失败案例
    Tool: Bash
    Preconditions: 无
    Steps:
      1. 运行: python -c "
      from memory_service import MemoryService, MemoryServiceConfig
      m = MemoryService(MemoryServiceConfig(db_path=':memory:'))
      m.write_memory('LLM timeout on large prompt', {'scenario': 'data_science', 'step': 'coding', 'error_type': 'timeout'})
      m.write_memory('Docker sandbox OOM', {'scenario': 'data_science', 'step': 'running', 'error_type': 'oom'})
      result = m.query_context({'error_type': 'timeout'})
      print(f'items={len(result.items)}, first={result.items[0] if result.items else None}')
      stats = m.get_memory_stats()
      print(f'total={stats[\"items\"]}')
      "
      2. 断言: 输出 items=1（只匹配 timeout）, total=2（写入了2条）
    Expected Result: items=1, first 包含 "LLM timeout", total=2
    Failure Indicators: items=0 或 items=2（查询未过滤）或 total!=2
    Evidence: .sisyphus/evidence/task-11-write-query.txt

  Scenario: 默认配置向后兼容
    Tool: Bash
    Steps:
      1. 运行: python -c "
      from memory_service import MemoryService, MemoryServiceConfig
      m = MemoryService(MemoryServiceConfig())
      result = m.query_context({'key': 'value'})
      print(f'items={len(result.items)}, highlights={len(result.highlights)}')
      stats = m.get_memory_stats()
      print(f'total={stats[\"items\"]}')
      "
      2. 断言: 空数据库返回空 ContextPack，stats 返回 items=0
    Expected Result: items=0, highlights=0, total=0
    Failure Indicators: 异常或非空返回
    Evidence: .sisyphus/evidence/task-11-backward-compat.txt

  Scenario: build_runtime() 仍然正常工作
    Tool: Bash
    Steps:
      1. 运行: python -c "from app.runtime import build_runtime; r = build_runtime(); r.memory_service.write_memory('test', {'k':'v'}); print(r.memory_service.get_memory_stats())"
      2. 断言: 无异常，stats 显示 items=1
    Expected Result: runtime 集成正常
    Failure Indicators: ImportError 或 AttributeError
    Evidence: .sisyphus/evidence/task-11-runtime-integration.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(kb): implement minimal knowledge base with failure case store`
  - Files: `memory_service/service.py`, `memory_service/__init__.py`, `tests/test_memory_service.py`
  - Pre-commit: `python -m pytest tests/test_memory_service.py -v`

- [ ] 12. 实现 CoSTEER 多轮代码演化

  **What to do**:
  - 核心目标：在 coding 阶段支持多轮代码改进（不只是单次 `coder.develop()`）
  - 实现方式：在 `step_executor.py` 的 coding 阶段添加 evolve loop，或创建新的 wrapper
  - 具体步骤：
    1. 创建 `core/loop/costeer.py`：
       - `CoSTEEREvolver` 类：
         - 构造参数：`coder: Coder`, `runner: Runner`, `feedback_analyzer: FeedbackAnalyzer`, `max_rounds: int = 3`
         - `evolve(experiment, proposal, scenario) -> CodeArtifact`：
           - Round 1: 调用 `coder.develop()` 生成初始代码
           - Round 2+: 调用 `runner.run()` + `feedback_analyzer.summarize()` 获取反馈
           - 如果 feedback.acceptable == True → 提前退出
           - 如果 feedback.acceptable == False → 将 feedback 注入 experiment.hypothesis 作为上下文，再次调用 `coder.develop()`
           - 最多 `max_rounds` 轮
           - 返回最后一轮的 CodeArtifact
    2. 修改 `core/loop/step_executor.py`：
       - 在 `execute_iteration()` 的 coding 阶段，检查配置是否启用 CoSTEER
       - 如果启用：使用 `CoSTEEREvolver.evolve()` 替代直接 `coder.develop()`
       - 如果未启用：保持原有单次调用（向后兼容）
    3. 在 `app/config.py` 添加 `costeer_max_rounds: int = 1`（默认1=不启用多轮）
  - TDD: 先写测试，使用 mock coder/runner/feedback

  **Must NOT do**:
  - 不修改 `Coder` Protocol 签名（向后兼容）
  - 不修改 `Runner` 或 `FeedbackAnalyzer` Protocol 签名
  - 不在 evolve loop 中调用真实 LLM（测试使用 mock）
  - 不添加超过 3 轮的默认值（避免不可控的 LLM 调用）
  - 不修改 PluginBundle 的结构

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 这是计划中最复杂的任务，需要理解整个 6 阶段执行流程，正确注入 evolve loop，处理反馈回传机制
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T9, T11)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 9, 11

  **References**:

  **Pattern References**:
  - `core/loop/step_executor.py:147-173` — coding 阶段当前实现：单次 `coder.develop()` → artifact。CoSTEER 要替换这一段
  - `core/loop/step_executor.py:175-191` — running 阶段：展示 `runner.run(artifact, scenario)` 调用方式
  - `core/loop/step_executor.py:196-218` — feedback 阶段：展示 `feedback_analyzer.summarize()` 调用方式和返回值
  - `core/loop/step_executor.py:59-68` — `execute_iteration()` 方法签名和参数

  **API/Type References**:
  - `plugins/contracts.py:72-81` — `Coder` Protocol：`develop(experiment, proposal, scenario) -> CodeArtifact`
  - `plugins/contracts.py:84-89` — `Runner` Protocol：`run(artifact, scenario) -> ExecutionResult`
  - `plugins/contracts.py:92-102` — `FeedbackAnalyzer` Protocol：`summarize(experiment, result, score) -> FeedbackRecord`
  - `data_models.py:167-186` — `ExperimentNode` dataclass：hypothesis 字段用于传递上下文给 coder
  - `data_models.py:188-195` — `FeedbackRecord` dataclass：acceptable 字段决定是否继续演化
  - `data_models.py:197-210` — `CodeArtifact` dataclass

  **WHY Each Reference Matters**:
  - step_executor 147-173 是要修改的核心位置，必须精确理解上下游
  - Coder/Runner/FeedbackAnalyzer 的 Protocol 是不可变的约束
  - ExperimentNode.hypothesis 是向 coder 传递反馈上下文的机制
  - FeedbackRecord.acceptable 是 evolve loop 的终止条件

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_costeer.py`
  - [ ] RED: 测试单轮模式（max_rounds=1）→ 行为与原来一致
  - [ ] RED: 测试多轮 acceptable=False → 继续演化直到 acceptable=True
  - [ ] RED: 测试达到 max_rounds 后即使 unacceptable 也停止
  - [ ] RED: 测试第一轮就 acceptable → 直接返回，不进入第二轮
  - [ ] GREEN: 所有测试通过
  - [ ] `python -m pytest tests/test_costeer.py -v` → PASS
  - [ ] 回归: `python -m pytest tests/ -v` → ALL PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CoSTEER 多轮演化 — 2轮后成功
    Tool: Bash
    Steps:
      1. 运行: python -c "
      from unittest.mock import MagicMock
      from core.loop.costeer import CoSTEEREvolver
      from data_models import CodeArtifact, ExecutionResult, FeedbackRecord, ExperimentNode, Proposal, Score
      from plugins.contracts import ScenarioContext
      
      coder = MagicMock()
      runner = MagicMock()
      feedback = MagicMock()
      
      art1 = CodeArtifact(artifact_id='v1', description='first', location='/tmp/v1')
      art2 = CodeArtifact(artifact_id='v2', description='improved', location='/tmp/v2')
      coder.develop.side_effect = [art1, art2]
      
      exec_result = ExecutionResult(run_id='r1', exit_code=0, logs_ref='', artifacts_ref='')
      runner.run.return_value = exec_result
      
      fb_bad = FeedbackRecord(feedback_id='fb1', acceptable=False, reason='poor quality')
      fb_good = FeedbackRecord(feedback_id='fb2', acceptable=True, reason='looks good')
      feedback.summarize.side_effect = [fb_bad, fb_good]
      
      evolver = CoSTEEREvolver(coder=coder, runner=runner, feedback_analyzer=feedback, max_rounds=3)
      exp = ExperimentNode(node_id='n1', hypothesis={})
      prop = Proposal(proposal_id='p1', summary='test')
      scenario = ScenarioContext(run_id='r1', scenario_name='test', input_payload={})
      
      result = evolver.evolve(exp, prop, scenario)
      print(f'artifact={result.artifact_id}, rounds={coder.develop.call_count}')
      "
      2. 断言: 输出 "artifact=v2, rounds=2"
    Expected Result: 2轮后成功，返回第二版 artifact
    Failure Indicators: rounds!=2 或 artifact_id 不是 v2
    Evidence: .sisyphus/evidence/task-12-costeer-2rounds.txt

  Scenario: CoSTEER 单轮模式（向后兼容）
    Tool: Bash
    Steps:
      1. 运行: python -c "
      from unittest.mock import MagicMock
      from core.loop.costeer import CoSTEEREvolver
      from data_models import CodeArtifact, ExperimentNode, Proposal
      from plugins.contracts import ScenarioContext
      
      coder = MagicMock()
      art = CodeArtifact(artifact_id='v1', description='only', location='/tmp/v1')
      coder.develop.return_value = art
      
      evolver = CoSTEEREvolver(coder=coder, runner=MagicMock(), feedback_analyzer=MagicMock(), max_rounds=1)
      exp = ExperimentNode(node_id='n1', hypothesis={})
      prop = Proposal(proposal_id='p1', summary='test')
      scenario = ScenarioContext(run_id='r1', scenario_name='test', input_payload={})
      
      result = evolver.evolve(exp, prop, scenario)
      print(f'artifact={result.artifact_id}, rounds={coder.develop.call_count}')
      "
      2. 断言: 输出 "artifact=v1, rounds=1"
    Expected Result: 单轮模式，只调用一次 coder.develop()
    Failure Indicators: rounds!=1
    Evidence: .sisyphus/evidence/task-12-costeer-single-round.txt

  Scenario: step_executor 默认行为不变
    Tool: Bash
    Steps:
      1. 运行: python -m pytest tests/ -v
      2. 断言: 所有现有测试通过（默认 costeer_max_rounds=1 = 无 evolve）
    Expected Result: 回归测试全部通过
    Evidence: .sisyphus/evidence/task-12-regression.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(costeer): add multi-round code evolution`
  - Files: `core/loop/costeer.py`, `core/loop/step_executor.py`, `app/config.py`, `tests/test_costeer.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 13. 集成测试：完整循环验证

  **What to do**:
  - 创建 `tests/test_integration_full_loop.py`：
    - 测试1: **完整 6 阶段单步执行** — 使用 MockLLMProvider，验证 propose → experiment → coding → running → feedback → record 全流程
    - 测试2: **CoSTEER 多轮 + KB 写入** — 模拟 2 轮 coding 演化，验证 feedback 被写入 memory_service
    - 测试3: **KB 跨步骤查询** — 写入失败案例后，在下一步的 propose 中 query_context 能返回该案例
    - 测试4: **LLM provider 切换** — 验证 mock 和 litellm provider 都能正确创建（litellm 用 mock patch）
  - 使用 `build_runtime()` 和 `build_run_service()` 组装真实的依赖链
  - 所有外部依赖（LLM API, Docker）使用 mock/patch

  **Must NOT do**:
  - 不调用真实 LLM API
  - 不启动 Docker 容器
  - 不修改任何 production 代码
  - 不添加新的外部依赖

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解全部组件的交互方式，编写覆盖多模块的集成测试
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all implementation tasks)
  - **Parallel Group**: Wave 4 (with Task 14)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 10, 11, 12

  **References**:

  **Pattern References**:
  - `app/runtime.py:48-83` — `build_runtime()` 完整组装逻辑
  - `app/runtime.py:86-114` — `build_run_service()` 创建 RunService 含 LoopEngine
  - `core/loop/engine.py` — LoopEngine.run_loop() 是循环入口
  - `core/loop/step_executor.py:59-68` — execute_iteration() 是单步执行入口

  **API/Type References**:
  - `core/loop/run_service.py` — RunService.start_run() 是最顶层的调用入口
  - `data_models.py:1-50` — RunSession, RunStatus 等核心模型
  - `data_models.py:398-403` — ContextPack（KB 返回的类型）

  **Test References**:
  - `tests/test_task_01_core_models.py` — 现有测试模式：unittest.TestCase, setUp/tearDown
  - 其他 test_task_*.py 文件 — 参考 mock 和 fixture 模式

  **WHY Each Reference Matters**:
  - 集成测试必须使用真实的组装方式（build_runtime/build_run_service）才能验证各模块真正协作
  - LoopEngine.run_loop() 调用 step_executor.execute_iteration()，后者现在会使用 CoSTEER evolve
  - ContextPack 是 KB 查询的返回类型，验证其 items 非空证明 KB 工作正常

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_integration_full_loop.py`
  - [ ] `python -m pytest tests/test_integration_full_loop.py -v` → PASS (4 tests)
  - [ ] `python -m pytest tests/ -v` → ALL PASS (包含所有新旧测试)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: 全部测试通过
    Tool: Bash
    Steps:
      1. 运行: python -m pytest tests/ -v --tb=short 2>&1 | tail -20
      2. 断言: 退出码 0，所有测试 PASSED
      3. 运行: python -m pytest tests/ -v --tb=short 2>&1 | grep -c "PASSED"
      4. 断言: 数量 ≥ 25（23 existing + ≥2 new integration）
    Expected Result: 所有测试通过，总数增长
    Failure Indicators: 任何 FAIL 或 ERROR
    Evidence: .sisyphus/evidence/task-13-all-tests.txt

  Scenario: 集成测试覆盖完整链路
    Tool: Bash
    Steps:
      1. 运行: python -m pytest tests/test_integration_full_loop.py -v --tb=long
      2. 断言: 4 个测试全部 PASSED
      3. 确认测试名包含: test_full_loop, test_costeer_kb, test_kb_cross_step, test_llm_provider_switch
    Expected Result: 4个集成测试全部通过
    Failure Indicators: 任何测试失败或缺失
    Evidence: .sisyphus/evidence/task-13-integration-detail.txt
  ```

  **Commit**: YES (groups with T14)
  - Message: `test(integration): add full loop integration test + update entry point`
  - Files: `tests/test_integration_full_loop.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 14. 创建新的 CLI 入口脚本

  **What to do**:
  - 创建 `cli.py`（或 `run.py`）作为替代已删除 `main.py` 的新入口点：
    - 使用 `app/runtime.py` 的 `build_runtime()` + `build_run_service()` 
    - 支持命令行参数：
      - `--scenario`: 选择场景（默认 "data_science"）
      - `--task`: 任务描述字符串
      - `--max-steps`: 最大迭代步数（默认 5）
      - `--dry-run`: 只初始化不运行（验证配置）
    - 使用 `argparse`（标准库，不引入额外依赖）
    - 打印启动信息（scenario, llm_provider, costeer_max_rounds）
    - 调用 `RunService.start_run()` 启动循环
  - 更新 `README.md`（如果存在）中的运行命令
  - TDD: 测试 argparse 解析和 dry-run 模式

  **Must NOT do**:
  - 不使用 Click 或 Typer 等外部 CLI 库
  - 不实现复杂的子命令系统（只要一个 run 命令）
  - 不在 CLI 中硬编码任何配置值

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的 argparse 入口脚本，逻辑直接
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T1 deletion of old main.py, T10 runtime integration)
  - **Parallel Group**: Wave 4 (with Task 13)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 1, 10

  **References**:

  **Pattern References**:
  - `app/runtime.py:48-114` — `build_runtime()` 和 `build_run_service()` — 新 CLI 的核心调用
  - 已删除的 `main.py`（在 Task 1 中）— 旧入口点用 OrchestratorRDLoopEngine，新的应使用 app/runtime

  **API/Type References**:
  - `core/loop/run_service.py` — `RunService.start_run(task_summary, input_payload, max_steps)` — CLI 调用的最终 API
  - `app/config.py` — 配置从环境变量加载，CLI 不需要重复配置逻辑

  **WHY Each Reference Matters**:
  - build_runtime()/build_run_service() 是正确的组装方式，CLI 只是调用入口
  - RunService.start_run() 是 CLI 最终要调用的方法

  **Acceptance Criteria**:

  **If TDD:**
  - [ ] 测试文件: `tests/test_cli.py`
  - [ ] RED: 测试 `--dry-run` 模式只初始化不运行
  - [ ] RED: 测试 `--scenario synthetic_research` 正确传递
  - [ ] GREEN: 所有测试通过

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CLI dry-run 模式
    Tool: Bash
    Steps:
      1. 运行: python cli.py --dry-run --scenario data_science --task "test task"
      2. 断言: 输出包含 "scenario: data_science", "llm_provider: mock"（默认配置）
      3. 断言: 退出码 0，不启动实际循环
    Expected Result: dry-run 打印配置信息后退出
    Failure Indicators: 异常或启动了实际循环
    Evidence: .sisyphus/evidence/task-14-cli-dryrun.txt

  Scenario: CLI help 信息完整
    Tool: Bash
    Steps:
      1. 运行: python cli.py --help
      2. 断言: 输出包含 "--scenario", "--task", "--max-steps", "--dry-run"
    Expected Result: 所有参数都在 help 中列出
    Failure Indicators: 缺少参数说明
    Evidence: .sisyphus/evidence/task-14-cli-help.txt

  Scenario: 旧 main.py 不存在
    Tool: Bash
    Steps:
      1. 运行: test -f main.py && echo "EXISTS" || echo "DELETED"
      2. 断言: 输出 "DELETED"
      3. 运行: test -f cli.py && echo "EXISTS" || echo "MISSING"
      4. 断言: 输出 "EXISTS"
    Expected Result: 旧入口已删除，新入口已创建
    Evidence: .sisyphus/evidence/task-14-entry-point.txt
  ```

  **Commit**: YES (groups with T13)
  - Message: `test(integration): add full loop integration test + update entry point`
  - Files: `cli.py`, `tests/test_cli.py`
  - Pre-commit: `python -m pytest tests/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/ -v` + check for `as any`/`@ts-ignore` equivalents, empty catches, print() in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Commit Group | Tasks | Message | Pre-commit Check |
|---|---|---|---|
| 1 | T1, T2, T3 | `refactor(cleanup): remove dead code and duplicate orchestrator` | `python -m pytest tests/ -v` |
| 2 | T4 | `docs(adr): add architecture decision records` | — |
| 3 | T5, T9, T10 | `feat(llm): add real LLM provider via LiteLLM` | `python -m pytest tests/ -v` |
| 4 | T6, T7, T8 | `docs: patch PRD, architecture, and spec to match implementation` | — |
| 5 | T11 | `feat(kb): implement minimal knowledge base with failure case store` | `python -m pytest tests/ -v` |
| 6 | T12 | `feat(costeer): add multi-round code evolution` | `python -m pytest tests/ -v` |
| 7 | T13, T14 | `test(integration): add full loop integration test + update entry point` | `python -m pytest tests/ -v` |

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -v  # Expected: ALL tests pass (23 existing + new)
python -c "from app.runtime import build_runtime; r = build_runtime(); print('OK')"  # Expected: OK
python -c "from llm.adapter import LLMAdapter; from llm.providers.litellm_provider import LiteLLMProvider; print('import OK')"  # Expected: import OK
python -c "from memory_service import MemoryService, MemoryServiceConfig; m = MemoryService(MemoryServiceConfig()); m.write_memory('test', {'k': 'v'}); print(m.query_context({'k': 'v'}))"  # Expected: non-empty ContextPack
grep -r 'orchestrator_rd_loop_engine' --include='*.py' .  # Expected: no matches (deleted)
grep -r 'demo_planner_loop\|demo_task_intake' --include='*.py' .  # Expected: no matches (deleted)
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (existing + new)
- [ ] No references to deleted modules
- [ ] LLM provider switchable between mock and real
- [ ] KB stores and retrieves failure cases
- [ ] CoSTEER does ≥2 rounds of code evolution
