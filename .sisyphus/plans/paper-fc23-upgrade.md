# FC-2/FC-3 完整实现升级（论文精确复现）

## TL;DR

> **Quick Summary**: 将 FC-2 (Exploration/MCTS) 和 FC-3 (Reasoning/CoSTEER) 从"早期版本"升级到论文完整实现。FC-2 重写 MCTSScheduler（完整 PUCT + 回传 + Reward + Layer-0 多样性），FC-3 增强 trace 持久化和反馈闭环。
> 
> **Deliverables**:
> - 重写后的 MCTSScheduler（含 backpropagation、先验概率 PUCT、reward 计算）
> - Layer-0 Diversity 通过 VirtualEvaluator 集成
> - 完整的树结构维护（edges、depth tracking）
> - FC-3 Trace 持久化到 trace_store
> - FC-3 结构化反馈闭环（三维反馈）
> - FC-3 知识自生成（复用 FC-4 MemoryService）
> - 全面的 TDD 测试覆盖
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1 → T4 → T7 → T10 → T13 → T14 → Final

---

## Context

### Original Request
用户说："FC2和FC3好像不是完全实现版，只是早期版，请完整实现"。要求论文精确复现，TDD 测试驱动，保守稳妥方案。

### Interview Summary
**Key Discussions**:
- FC-2 Scheduler: 用户选择**重写**（非增量升级）— 现有架构差距太大
- FC-3 知识自生成: **复用 FC-4 MemoryService** — 不新建知识库
- Layer-0 Diversity: **复用 VirtualEvaluator** — 用 N 候选→K 选择生成多样化根节点
- 测试策略: **TDD (RED-GREEN-REFACTOR)** — 先写测试再实现

**Research Findings**:
- 官方 RDAgent 实现使用 PUCT（含先验概率 P via softmax(potential)）、完整回传（叶→root更新所有祖先）、tanh归一化reward
- 官方 CoSTEER 使用 RAGEvoAgent.multistep_evolve() + CoSTEERSingleFeedback（execution + return_checking + code 三维反馈）+ knowledge_self_gen
- FC-2 消融实验显示移除后性能下降 28%（6个FC中最大）
- 现有 12 个 scheduler 测试 + 4 个 e2e 测试需要随 scheduler 重写而更新
- FC-3 的 8 个 pipeline 测试 + 10 个场景集成测试应保持兼容

### Self-Review (Metis unavailable — self-conducted)
**自识别的潜在问题**（已处理）:
- Scheduler 重写时旧测试怎么办 → 新测试先写，旧测试迁移或替换
- VirtualEvaluator 集成到 Layer-0 是否引入循环依赖 → 通过 LoopEngine 层面调用，不直接依赖
- FC-3 trace 持久化需要 trace_store 接口扩展 → 评估 BranchTraceStore 是否可复用
- CoSTEEREvolver 反馈增强是否影响现有 Coder/Runner 接口 → 不改 Protocol，在 CoSTEEREvolver 内部增强

---

## Work Objectives

### Core Objective
将 FC-2 和 FC-3 从早期版本升级到论文完整实现，使 my-RDagent 的全部 6 个 Framework Components 都达到论文级别。

### Concrete Deliverables
- 重写的 `exploration_manager/scheduler.py` — 完整 PUCT + backprop + reward
- 新增 `exploration_manager/reward.py` — Reward 计算模块
- 升级的 `exploration_manager/service.py` — 树结构维护 + layer-0 diversity 集成
- 升级的 `core/loop/engine.py` — select→expand→backprop 完整流程
- 升级的 `data_models.py` — 新增 MCTS 统计字段
- 升级的 `core/reasoning/pipeline.py` — trace 持久化
- 升级的 `core/loop/costeer.py` — 结构化反馈闭环 + 知识自生成
- 新增/升级的 `llm/schemas.py` — 新 schema（如 StructuredFeedback）
- 全面更新的测试文件

### Definition of Done
- [ ] 所有新功能通过 TDD 测试（新测试 + 旧测试迁移）
- [ ] 现有非 FC-2/FC-3 测试全部通过（429 - FC2/FC3相关测试 = ~390+ 测试不变）
- [ ] `bun test` 或 `python -m pytest tests/` 全部通过，0 failures
- [ ] MCTSScheduler 实现完整 PUCT 公式（含先验概率 P）
- [ ] Backpropagation 从叶节点沿父链更新所有祖先统计
- [ ] Layer-0 diversity 通过 VirtualEvaluator 生成多样化根节点
- [ ] FC-3 reasoning trace 被持久化到 trace_store
- [ ] CoSTEER 反馈循环使用结构化三维反馈
- [ ] plugins/contracts.py 6 个 Protocol 签名未被修改

### Must Have
- PUCT 公式包含先验概率 P（`U = Q + c_puct * P * sqrt(N_total) / (1 + N_node)`）
- Backpropagation 沿 parent_ids 链路传播 reward 并更新 value_sum/visit_count
- Reward 计算支持 score-based（tanh 归一化）和 decision-based 两种模式
- Layer-0 diversity 在图为空时生成 N 个多样化根节点
- Trace 持久化到已有的 trace_store 或 branch_trace_store
- 结构化反馈含 execution + return_checking + code 三个维度
- 知识自生成通过 FC-4 MemoryService.store() 实现

### Must NOT Have (Guardrails)
- **不得修改** `plugins/contracts.py` 中的 6 个 Protocol 签名
- **不得引入** asyncio / concurrent 并行执行（Phase 2 工作）
- **不得引入** NetworkX 或任何新的图库依赖
- **不得引入** 外部 embedding 库
- **不得破坏** 非 FC-2/FC-3 的现有测试
- **不得过度抽象** — 保持代码直接、可读
- **不得添加** 超过必要的注释/文档（避免 AI slop）
- **不得修改** FC-1/FC-4/FC-5/FC-6 的核心实现逻辑

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES（pytest 已配置，429 个测试通过）
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest
- **TDD flow**: 每个 task 先写 failing test → 实现使其 pass → refactor

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Unit tests**: `python -m pytest tests/test_*.py -v` — assert specific behaviors
- **Integration**: `python -m pytest tests/ -v` — full suite passes, 0 failures
- **Regression**: 非 FC-2/FC-3 测试数量不减少

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — data models + schemas + reward module):
├── Task 1: 扩展 data_models.py MCTS 统计字段 [quick]
├── Task 2: 新增 StructuredFeedback schema + FC-3 trace schema [quick]
├── Task 3: 新增 exploration_manager/reward.py (Reward 计算模块) [quick]
└── Task 4: 新增 backprop/PUCT/reward 相关 prompts (如需 LLM 辅助) [quick]

Wave 2 (Core Rewrite — scheduler + FC-3 trace + feedback):
├── Task 5: 重写 MCTSScheduler (完整 PUCT + backprop) [deep]
├── Task 6: FC-3 ReasoningPipeline trace 持久化 [unspecified-high]
├── Task 7: FC-3 CoSTEER 结构化反馈闭环增强 [unspecified-high]
└── Task 8: FC-3 知识自生成 via MemoryService [quick]

Wave 3 (Integration — engine + service + layer-0 diversity):
├── Task 9: 升级 ExplorationManager (树结构维护 + 新 scheduler API) [unspecified-high]
├── Task 10: 升级 LoopEngine (select→expand→backprop 完整流程) [deep]
├── Task 11: Layer-0 Diversity via VirtualEvaluator [unspecified-high]
└── Task 12: 升级 app/runtime.py wiring + config [quick]

Wave 4 (E2E Integration Tests + Regression):
├── Task 13: E2E 集成测试 — FC-2 完整 MCTS 循环 [deep]
├── Task 14: E2E 集成测试 — FC-3 CoSTEER 完整循环 [deep]
└── Task 15: 回归测试 + gap analysis 文档更新 [unspecified-high]

Wave FINAL (Independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — functional verification (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T5 → T9 → T10 → T13 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| T1   | —         | T5, T9, T10 | 1 |
| T2   | —         | T7 | 1 |
| T3   | —         | T5 | 1 |
| T4   | —         | T5 | 1 |
| T5   | T1, T3, T4 | T9, T10, T13 | 2 |
| T6   | —         | T14 | 2 |
| T7   | T2        | T14 | 2 |
| T8   | —         | T14 | 2 |
| T9   | T5        | T10, T11 | 3 |
| T10  | T5, T9    | T13 | 3 |
| T11  | T9        | T13 | 3 |
| T12  | T5, T9    | T13, T14 | 3 |
| T13  | T10, T11, T12 | F1-F4 | 4 |
| T14  | T6, T7, T8, T12 | F1-F4 | 4 |
| T15  | T13, T14  | F1-F4 | 4 |
| F1-F4| T15       | — | FINAL |

### Agent Dispatch Summary

- **Wave 1** (4 tasks): T1→`quick`, T2→`quick`, T3→`quick`, T4→`quick`
- **Wave 2** (4 tasks): T5→`deep`, T6→`unspecified-high`, T7→`unspecified-high`, T8→`quick`
- **Wave 3** (4 tasks): T9→`unspecified-high`, T10→`deep`, T11→`unspecified-high`, T12→`quick`
- **Wave 4** (3 tasks): T13→`deep`, T14→`deep`, T15→`unspecified-high`
- **FINAL** (4 tasks): F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [ ] 1. 扩展 data_models.py MCTS 统计字段

  **What to do**:
  - 在 `NodeRecord` 数据类中添加 MCTS 必需字段：`visits: int = 0`, `total_value: float = 0.0`, `avg_value: float = 0.0`
  - 在 `ExplorationGraph` 中确保 `edges` 字段的 `GraphEdge` 类型包含 `parent_id` 和 `child_id`，如已有则验证即可
  - 新增 `NodeRecord.update_stats(reward: float)` 方法：`self.visits += 1; self.total_value += reward; self.avg_value = self.total_value / self.visits`
  - 确保现有 `visit_counts` dict 与新字段不冲突（迁移策略：新代码使用 NodeRecord 内部字段，旧 visit_counts 标记 deprecated）
  - TDD: 先写测试验证 NodeRecord 新字段初始值、update_stats 计算正确性、序列化/反序列化

  **Must NOT do**:
  - 不改 ExplorationGraph 的整体结构（仅添加字段）
  - 不引入新依赖
  - 不修改 plugins/contracts.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件数据模型字段扩展，改动小且明确
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 非 UI 任务
    - `git-master`: 不涉及 git 操作

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 5, 9, 10
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `data_models.py` — 现有 NodeRecord、ExplorationGraph、GraphEdge 定义。需要在 NodeRecord 中添加新字段并保持 dataclass 风格一致
  - `data_models.py:NodeRecord` — 现有字段: node_id, parent_ids, proposal_id, artifact_id, score_id, score, branch_state。在这些后面添加 MCTS 统计字段

  **API/Type References**:
  - 官方 RDAgent `trace_scheduler.py` 使用 `node_value_sum[id]` 和 `node_visit_count[id]` 字典。我们将这些作为 NodeRecord 的内部字段而非外部字典

  **Test References**:
  - `tests/test_scheduler_mcts.py` — 现有测试创建 NodeRecord 的方式，确保新字段不破坏现有构造

  **WHY Each Reference Matters**:
  - data_models.py 是所有 FC 共享的数据层，改动必须向后兼容

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_data_models_mcts.py
  - [ ] `python -m pytest tests/test_data_models_mcts.py -v` → PASS

  **QA Scenarios:**

  ```
  Scenario: NodeRecord 新字段默认值正确
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from data_models import NodeRecord; n = NodeRecord(node_id='test'); print(n.visits, n.total_value, n.avg_value)"
      2. Assert output is "0 0.0 0.0"
    Expected Result: 三个新字段均为零默认值
    Failure Indicators: ImportError 或字段不存在
    Evidence: .sisyphus/evidence/task-1-noderecord-defaults.txt

  Scenario: update_stats 计算正确性
    Tool: Bash (python)
    Preconditions: NodeRecord 已有 update_stats 方法
    Steps:
      1. python -c "from data_models import NodeRecord; n = NodeRecord(node_id='test'); n.update_stats(0.5); n.update_stats(0.3); print(n.visits, round(n.total_value,1), round(n.avg_value,2))"
      2. Assert output is "2 0.8 0.40"
    Expected Result: visits=2, total_value=0.8, avg_value=0.40
    Failure Indicators: 计算错误或方法不存在
    Evidence: .sisyphus/evidence/task-1-update-stats.txt

  Scenario: 旧代码构造 NodeRecord 不报错
    Tool: Bash (python)
    Preconditions: 新字段有默认值
    Steps:
      1. python -m pytest tests/ -v -k "not test_data_models_mcts" --tb=short 2>&1 | tail -5
      2. Assert "passed" in output, 0 failures
    Expected Result: 所有非新测试仍然通过
    Failure Indicators: 任何现有测试失败
    Evidence: .sisyphus/evidence/task-1-regression.txt
  ```

  **Commit**: YES (groups with T2, T3, T4 — Wave 1)
  - Message: `feat(data-models): 扩展MCTS统计字段(visits/total_value/avg_value)`
  - Files: `data_models.py`, `tests/test_data_models_mcts.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 2. 新增 StructuredFeedback schema + FC-3 trace schema

  **What to do**:
  - 在 `llm/schemas.py` 中新增 `StructuredFeedback` dataclass，包含字段: `execution: str`, `return_checking: Optional[str]`, `code: str`, `final_decision: Optional[bool]`, `reasoning: str`。实现 `from_dict()` classmethod
  - 新增 `ReasoningTrace` dataclass，包含字段: `trace_id: str`, `stages: Dict[str, Any]`（各阶段输出），`timestamp: str`, `metadata: Dict[str, Any]`。实现 `from_dict()`
  - 为 MockLLMProvider 在 `llm/adapter.py` 中添加对新 schema 关键词的 mock 响应检测
  - TDD: 先写测试验证 from_dict、字段类型、mock 检测

  **Must NOT do**:
  - 不修改现有 schema（AnalysisResult 等）
  - 不修改 plugins/contracts.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Schema 定义和 mock 添加，模式固定
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `llm/schemas.py` — 现有 schema 模式（AnalysisResult, ExperimentDesign 等），都使用 `@dataclass` + `from_dict()` classmethod 模式。新 schema 必须遵循相同模式
  - `llm/adapter.py:MockLLMProvider.complete()` — 现有 mock 检测顺序（根据 prompt 中的关键词判断返回哪个 mock JSON）。新增的 mock 应插入到合适位置

  **API/Type References**:
  - 官方 RDAgent `CoSTEERSingleFeedback`: 包含 execution, return_checking, code, final_decision, raw_execution, source_feedback

  **Test References**:
  - `tests/test_schemas_fc3.py` — 现有 schema 测试模式（test_from_dict_empty, test_from_dict_full_fields 等）

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_schemas_structured_feedback.py
  - [ ] `python -m pytest tests/test_schemas_structured_feedback.py -v` → PASS

  **QA Scenarios:**

  ```
  Scenario: StructuredFeedback.from_dict 正确解析
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from llm.schemas import StructuredFeedback; f = StructuredFeedback.from_dict({'execution': 'ok', 'code': 'good', 'reasoning': 'clean'}); print(f.execution, f.code, f.final_decision)"
      2. Assert output contains "ok good None"
    Expected Result: from_dict 正确填充字段，Optional 字段默认 None
    Failure Indicators: ImportError 或 AttributeError
    Evidence: .sisyphus/evidence/task-2-structured-feedback.txt

  Scenario: MockLLMProvider 识别新 schema 关键词
    Tool: Bash (python)
    Preconditions: adapter.py 已添加 mock 检测
    Steps:
      1. python -c "from llm.adapter import MockLLMProvider; m = MockLLMProvider(); r = m.complete('Please provide structured feedback with execution status'); print('execution' in r or 'feedback' in r.lower())"
      2. Assert output is "True"
    Expected Result: Mock 返回包含 execution/code 字段的 JSON
    Failure Indicators: Mock 返回不相关的 JSON
    Evidence: .sisyphus/evidence/task-2-mock-detection.txt
  ```

  **Commit**: YES (groups with T1, T3, T4 — Wave 1)
  - Message: `feat(schemas): 新增StructuredFeedback和ReasoningTrace schema`
  - Files: `llm/schemas.py`, `llm/adapter.py`, `tests/test_schemas_structured_feedback.py`

- [ ] 3. 新增 exploration_manager/reward.py (Reward 计算模块)

  **What to do**:
  - 创建 `exploration_manager/reward.py`，实现 `RewardCalculator` 类
  - 支持两种模式: `score_based`（`reward = tanh(score) * direction`，direction=1 for bigger_is_better, -1 otherwise）和 `decision_based`（`reward = 1.0 if decision else 0.0`）
  - 构造参数: `mode: str = "score_based"`, `direction: int = 1`（bigger_is_better 时为 1，否则为 -1）
  - 方法: `calculate(score: Optional[float], decision: Optional[bool]) -> float`
  - 处理边界: score=None 时回退到 decision_based；两个都 None 返回 0.0
  - TDD: 测试两种模式、边界条件、tanh 归一化

  **Must NOT do**:
  - 不引入新依赖（math.tanh 已内置）
  - 不在此 task 中集成到 scheduler（T5 做）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 独立的计算模块，纯函数逻辑，无外部依赖
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - 官方 RDAgent `trace_scheduler.py:observe_feedback()` 中的 reward 计算: `reward = math.tanh(re.result.loc["ensemble"].iloc[0].round(3)) * (1 if bigger_is_better else -1)` 或 `reward = 1.0 if decision else 0.0`

  **API/Type References**:
  - `data_models.py:NodeRecord` — score 字段是 `Optional[float]`，reward 计算需处理 None

  **Test References**:
  - 项目中的纯逻辑测试模式，如 `tests/test_scheduler_mcts.py` 的结构

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_reward.py
  - [ ] `python -m pytest tests/test_reward.py -v` → PASS (≥6 tests)

  **QA Scenarios:**

  ```
  Scenario: Score-based reward 正向 (bigger_is_better)
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from exploration_manager.reward import RewardCalculator; r = RewardCalculator(mode='score_based', direction=1); print(round(r.calculate(score=0.8, decision=None), 4))"
      2. Assert output is approximately "0.6640" (tanh(0.8) ≈ 0.6640)
    Expected Result: tanh(0.8) * 1 ≈ 0.6640
    Failure Indicators: 计算错误或不使用 tanh
    Evidence: .sisyphus/evidence/task-3-score-reward-positive.txt

  Scenario: Decision-based reward fallback
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from exploration_manager.reward import RewardCalculator; r = RewardCalculator(mode='decision_based'); print(r.calculate(score=None, decision=True), r.calculate(score=None, decision=False))"
      2. Assert output is "1.0 0.0"
    Expected Result: True→1.0, False→0.0
    Failure Indicators: 返回非数值或不区分 True/False
    Evidence: .sisyphus/evidence/task-3-decision-reward.txt

  Scenario: Both None 返回 0.0
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from exploration_manager.reward import RewardCalculator; r = RewardCalculator(); print(r.calculate(score=None, decision=None))"
      2. Assert output is "0.0"
    Expected Result: 安全默认值 0.0
    Evidence: .sisyphus/evidence/task-3-none-fallback.txt
  ```

  **Commit**: YES (groups with T1, T2, T4 — Wave 1)
  - Message: `feat(fc2): 新增RewardCalculator模块(score_based+decision_based)`
  - Files: `exploration_manager/reward.py`, `tests/test_reward.py`

- [ ] 4. 更新 prompts.py — 新增 potential 评分 prompt（如需 LLM 辅助先验概率）

  **What to do**:
  - 评估是否需要 LLM 来计算 PUCT 的先验概率 P（potential function）。官方实现通过 `calculate_potential(trace, leaf)` → softmax 得到先验
  - **保守方案**: 不新增 LLM prompt，使用纯启发式的 potential function（基于 score history 或 uniform prior）
  - 如果纯启发式足够，本 task 仅需：在 `llm/prompts.py` 中新增 `structured_feedback_prompt()` 函数，用于 FC-3 结构化反馈生成
  - 新增 `knowledge_extraction_prompt()` 函数，用于 FC-3 知识自生成（从 CoSTEER 循环结果中提取可复用知识）
  - TDD: 测试 prompt 函数返回字符串、包含必需节（如 Output Fields）

  **Must NOT do**:
  - 不修改现有 prompt 函数
  - 不引入复杂的 LLM-driven potential function（保守方案 = 纯启发式）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 新增 prompt 模板函数，遵循现有模式
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 5 (potential function 决策), Task 7 (feedback prompt)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `llm/prompts.py` — 现有 prompt 模式：每个函数返回 f-string，使用 `_build_schema_hint()` 生成 Output Fields 段，接受 context/history 等参数

  **API/Type References**:
  - 官方 RDAgent Appendix E.2/E.3 的 prompt 结构

  **Test References**:
  - `tests/test_prompts_fc3.py` — 现有 prompt 测试模式（验证返回 str、包含关键词、包含 schema hint）

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to tests/test_prompts_fc3.py or new file
  - [ ] `python -m pytest tests/test_prompts_fc3.py -v` → PASS

  **QA Scenarios:**

  ```
  Scenario: structured_feedback_prompt 返回有效 prompt
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from llm.prompts import structured_feedback_prompt; p = structured_feedback_prompt(code='print(1)', execution_output='1', task_description='add two numbers'); print('Output Fields' in p, 'execution' in p.lower())"
      2. Assert output is "True True"
    Expected Result: Prompt 包含 Output Fields 和 execution 关键词
    Evidence: .sisyphus/evidence/task-4-feedback-prompt.txt

  Scenario: knowledge_extraction_prompt 返回有效 prompt
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from llm.prompts import knowledge_extraction_prompt; p = knowledge_extraction_prompt(trace_summary='experiment succeeded with feature X', scenario='data_science'); print(type(p).__name__, len(p) > 50)"
      2. Assert output is "str True"
    Expected Result: 返回非空字符串
    Evidence: .sisyphus/evidence/task-4-knowledge-prompt.txt
  ```

  **Commit**: YES (groups with T1, T2, T3 — Wave 1)
  - Message: `feat(prompts): 新增structured_feedback和knowledge_extraction prompts`
  - Files: `llm/prompts.py`, `tests/test_prompts_fc3.py`

- [ ] 5. 重写 MCTSScheduler（完整 PUCT + Backpropagation + Reward 集成）

  **What to do**:
  - **完全重写** `exploration_manager/scheduler.py` 中的 `MCTSScheduler` 类
  - **PUCT 公式**: `score = Q(node) + c_puct * P(node) * sqrt(N_total) / (1 + N_node)`
    - `Q(node)` = `node.avg_value`（平均累积 reward，非单次 score）
    - `P(node)` = 先验概率，通过 `softmax(potential(node))` 计算。保守方案: potential = node.score if not None else 0.0（不需 LLM）
    - `N_total` = 全局总访问次数
    - `N_node` = 该节点访问次数
  - **新方法 `backpropagate(graph, node_id, reward)`**: 从 node_id 沿 parent_ids 链路到 root，对路径上每个节点调用 `node.update_stats(reward)`
  - **新方法 `observe_feedback(graph, node_id, score, decision)`**: 使用 RewardCalculator 计算 reward，然后调用 backpropagate
  - **保留 `select_node(graph)`**: 重写内部逻辑使用新 PUCT 公式
  - **保留 `get_all_scores(graph)`**: 返回每个节点的 Q + U 明细（调试用）
  - **删除旧的 `update_visit_count`**: 被 backpropagate 替代
  - **同步重写测试** `tests/test_scheduler_mcts.py`: 删除旧测试，写新测试覆盖 PUCT 选择、backprop 传播、reward 集成、边界条件
  - TDD: 先写新测试（全部 RED），然后实现使其 GREEN

  **Must NOT do**:
  - 不引入 asyncio
  - 不在此 task 中修改 LoopEngine（T10 做）
  - 不修改 plugins/contracts.py

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心算法重写，涉及 PUCT 数学、树遍历、多方法协调，需要深度理解和精确实现
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 非 UI 任务

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T6, T7, T8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 9, 10, 13
  - **Blocked By**: Tasks 1, 3 (需要 NodeRecord 新字段和 RewardCalculator)

  **References**:

  **Pattern References**:
  - `exploration_manager/scheduler.py` — 现有 MCTSScheduler（要被完全重写）。保留类名和构造参数风格
  - 官方 RDAgent `trace_scheduler.py:MCTSScheduler` — 完整 PUCT 实现参考：`_get_q()`, `_get_u()`, `select()`, `observe_feedback()` 方法结构

  **API/Type References**:
  - `data_models.py:NodeRecord` — 新字段 visits, total_value, avg_value（T1 添加）
  - `data_models.py:ExplorationGraph` — nodes, edges, visit_counts
  - `exploration_manager/reward.py:RewardCalculator` — calculate(score, decision) → float（T3 创建）

  **Test References**:
  - `tests/test_scheduler_mcts.py` — 要被完全重写的旧测试文件。注意旧测试名和覆盖场景作为参考

  **External References**:
  - PUCT 公式来源: AlphaGo 论文变体，RDAgent paper Algorithm 1

  **WHY Each Reference Matters**:
  - 官方实现是对标标准，确保公式和行为一致
  - NodeRecord 新字段是 backprop 的数据基础
  - RewardCalculator 是 observe_feedback 的计算引擎

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_scheduler_mcts.py (完全重写)
  - [ ] `python -m pytest tests/test_scheduler_mcts.py -v` → PASS (≥15 tests)
  - [ ] 测试覆盖: PUCT 计算、select 行为、backprop 传播、observe_feedback、边界条件

  **QA Scenarios:**

  ```
  Scenario: PUCT 选择偏好未探索节点
    Tool: Bash (python)
    Preconditions: ExplorationGraph 有3个 ACTIVE 节点，2个已访问，1个未访问
    Steps:
      1. 构建 graph，node_a (visits=5, avg_value=0.6), node_b (visits=3, avg_value=0.4), node_c (visits=0)
      2. 调用 scheduler.select_node(graph)
      3. Assert 返回 node_c 的 id（未探索节点优先级最高）
    Expected Result: 返回未探索节点（PUCT 的探索项在 visits=0 时为 inf）
    Failure Indicators: 返回已探索节点
    Evidence: .sisyphus/evidence/task-5-puct-unexplored.txt

  Scenario: Backpropagation 沿父链更新所有祖先
    Tool: Bash (python)
    Preconditions: 树结构: root → child_a → leaf_b
    Steps:
      1. 创建 root (visits=0), child_a (parent_ids=["root"], visits=0), leaf_b (parent_ids=["child_a"], visits=0)
      2. 调用 scheduler.backpropagate(graph, "leaf_b", reward=0.8)
      3. Assert leaf_b.visits=1, leaf_b.avg_value=0.8
      4. Assert child_a.visits=1, child_a.avg_value=0.8
      5. Assert root.visits=1, root.avg_value=0.8
    Expected Result: 所有祖先的 visits 和 total_value 都被更新
    Failure Indicators: 只有叶节点被更新，祖先未变
    Evidence: .sisyphus/evidence/task-5-backprop-chain.txt

  Scenario: observe_feedback 使用 RewardCalculator 并触发 backprop
    Tool: Bash (python)
    Preconditions: 有一个简单的树结构
    Steps:
      1. 创建 scheduler（含 RewardCalculator mode='score_based'）
      2. 调用 observe_feedback(graph, node_id, score=0.7, decision=True)
      3. Assert 节点和祖先的 avg_value 约等于 tanh(0.7) ≈ 0.6044
    Expected Result: reward 通过 tanh 归一化后正确传播
    Evidence: .sisyphus/evidence/task-5-observe-feedback.txt

  Scenario: 先验概率 P 影响选择
    Tool: Bash (python)
    Preconditions: 两个节点，visits 相同但 score 不同
    Steps:
      1. node_a (visits=2, avg_value=0.5, score=0.9), node_b (visits=2, avg_value=0.5, score=0.1)
      2. 调用 select_node — 先验 P(a) 应 > P(b)（因为 score 更高 → potential 更高 → softmax 给更高概率）
      3. Assert 返回 node_a（先验概率加成使其 PUCT 分数更高）
    Expected Result: 高 score 节点因先验概率获得额外探索奖励
    Evidence: .sisyphus/evidence/task-5-prior-probability.txt
  ```

  **Commit**: YES
  - Message: `feat(fc2): 重写MCTSScheduler实现完整PUCT+backprop+reward`
  - Files: `exploration_manager/scheduler.py`, `tests/test_scheduler_mcts.py`
  - Pre-commit: `python -m pytest tests/ -v`

- [ ] 6. FC-3 ReasoningPipeline Trace 持久化

  **What to do**:
  - 修改 `core/reasoning/pipeline.py` 的 `ReasoningPipeline.reason()` 方法
  - 在 reason() 完成4个阶段后，调用 `_build_reasoning_trace()` 构建 trace dict
  - 将 trace 通过注入的 `trace_store` 或 `branch_trace_store` 持久化保存
  - 添加可选的 `trace_store` 参数到 `ReasoningPipeline.__init__()`（默认 None，向后兼容）
  - 如果 trace_store 为 None，trace 仍然构建但不保存（保持现有行为不变）
  - reason() 方法现在返回包含 trace_id 的结果（扩展返回值或在 ExperimentDesign 中添加 trace_id 字段）
  - TDD: 测试 trace_store 注入时保存调用、trace_store 为 None 时无副作用

  **Must NOT do**:
  - 不修改 reason() 的公开签名（添加 Optional 参数是向后兼容的）
  - 不修改 plugins/contracts.py
  - 不改变4阶段推理逻辑本身

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及持久化集成、向后兼容考虑、trace 数据流设计
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T7, T8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 14
  - **Blocked By**: None (不需要 Wave 1 的产出)

  **References**:

  **Pattern References**:
  - `core/reasoning/pipeline.py:_build_reasoning_trace()` — 已有 trace 构建逻辑，只需激活并持久化
  - `core/storage/branch_trace_store.py` — BranchTraceStore 的 record_node / query_nodes 接口，评估是否可用于保存 reasoning trace
  - 官方 RDAgent `evolving_agent.py:RAGEvoAgent` — `self.evolving_trace.append(es)` 模式

  **API/Type References**:
  - `llm/schemas.py:ReasoningTrace` — T2 创建的新 schema

  **Test References**:
  - `tests/test_reasoning_pipeline.py` — 现有 pipeline 测试，确保修改后仍通过

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to tests/test_reasoning_pipeline.py
  - [ ] `python -m pytest tests/test_reasoning_pipeline.py -v` → PASS (新增 ≥3 trace 相关测试)

  **QA Scenarios:**

  ```
  Scenario: Trace 保存到 trace_store
    Tool: Bash (python)
    Preconditions: MockTraceStore 已准备
    Steps:
      1. 创建 MockTraceStore（记录 store() 调用）
      2. 创建 ReasoningPipeline(llm_adapter=MockLLM, trace_store=MockTraceStore)
      3. 调用 pipeline.reason(task_summary="test", context={}, history=[])
      4. Assert MockTraceStore.store() 被调用1次
      5. Assert 保存的 trace 包含 analysis/problem/hypothesis/design 四个键
    Expected Result: Trace 被完整保存
    Failure Indicators: store() 未被调用，或 trace 缺少阶段数据
    Evidence: .sisyphus/evidence/task-6-trace-persistence.txt

  Scenario: trace_store=None 时向后兼容
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. 创建 ReasoningPipeline(llm_adapter=MockLLM)（不传 trace_store）
      2. 调用 pipeline.reason(...)
      3. Assert 无异常，返回结果与之前一致
    Expected Result: 行为不变，不抛异常
    Evidence: .sisyphus/evidence/task-6-backward-compat.txt
  ```

  **Commit**: YES (groups with T7, T8 — FC-3 wave)
  - Message: `feat(fc3): ReasoningPipeline trace持久化到trace_store`
  - Files: `core/reasoning/pipeline.py`, `tests/test_reasoning_pipeline.py`

- [ ] 7. FC-3 CoSTEER 结构化反馈闭环增强

  **What to do**:
  - 升级 `core/loop/costeer.py` 中的 `CoSTEEREvolver`
  - 当前: feedback.reason 被注入到 hypothesis 文本。改为: 使用 `structured_feedback_prompt()` + LLMAdapter 生成 `StructuredFeedback`（含 execution + return_checking + code 三维反馈）
  - 新增方法 `_analyze_feedback(feedback_record: FeedbackRecord, code: str, execution_output: str) -> StructuredFeedback`：调用 LLM 分析反馈并返回结构化结果
  - 在 CoSTEER 循环中：不再简单注入文本，而是将 `StructuredFeedback` 的各维度分别处理:
    - execution 反馈 → 传给 hypothesis 描述执行问题
    - code 反馈 → 传给 coder 描述代码改进方向
    - return_checking → 用于决定是否继续迭代
  - 可选: 在 `__init__` 中添加 `llm_adapter: Optional[LLMAdapter]`（默认 None 回退到旧行为）
  - TDD: 测试新旧行为、结构化反馈生成、三维反馈分离传递

  **Must NOT do**:
  - 不修改 FeedbackAnalyzer Protocol 签名
  - 不修改 Coder Protocol 签名
  - 不破坏旧的 CoSTEEREvolver 行为（llm_adapter=None 时保持原样）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 反馈闭环的重新设计，涉及 LLM 集成和多组件协调
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6, T8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 14
  - **Blocked By**: Task 2 (需要 StructuredFeedback schema)

  **References**:

  **Pattern References**:
  - `core/loop/costeer.py` — 现有 CoSTEEREvolver 实现，理解当前 feedback 注入方式
  - 官方 RDAgent `CoSTEER/evolving_strategy.py` — `last_feedback[index]` 被传给 implement 函数的模式

  **API/Type References**:
  - `llm/schemas.py:StructuredFeedback` — T2 创建的新 schema
  - `llm/prompts.py:structured_feedback_prompt()` — T4 创建的新 prompt

  **Test References**:
  - `tests/test_costeer.py` — 现有 CoSTEER 测试

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests updated in tests/test_costeer.py
  - [ ] `python -m pytest tests/test_costeer.py -v` → PASS (新增 ≥4 结构化反馈测试)

  **QA Scenarios:**

  ```
  Scenario: 结构化反馈生成包含三个维度
    Tool: Bash (python)
    Preconditions: MockLLMProvider 已支持 structured_feedback 关键词
    Steps:
      1. 创建 CoSTEEREvolver(coder=mock, runner=mock, feedback_analyzer=mock, llm_adapter=MockLLMAdapter)
      2. 模拟一轮循环：coder.develop → runner.run → feedback_analyzer.summarize → _analyze_feedback
      3. Assert _analyze_feedback 返回 StructuredFeedback 对象
      4. Assert feedback.execution 非空
      5. Assert feedback.code 非空
    Expected Result: 结构化反馈含有效的 execution 和 code 分析
    Failure Indicators: 返回 None 或缺少字段
    Evidence: .sisyphus/evidence/task-7-structured-feedback.txt

  Scenario: llm_adapter=None 回退到旧行为
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. 创建 CoSTEEREvolver(coder=mock, runner=mock, feedback_analyzer=mock)（不传 llm_adapter）
      2. 执行一轮循环
      3. Assert 行为与之前完全一致（feedback.reason 被注入 hypothesis）
    Expected Result: 向后兼容
    Evidence: .sisyphus/evidence/task-7-backward-compat.txt
  ```

  **Commit**: YES (groups with T6, T8 — FC-3 wave)
  - Message: `feat(fc3): CoSTEER结构化三维反馈闭环(execution+code+return_checking)`
  - Files: `core/loop/costeer.py`, `tests/test_costeer.py`

- [ ] 8. FC-3 知识自生成 via MemoryService

  **What to do**:
  - 在 `core/loop/costeer.py` 的 CoSTEEREvolver 循环末尾，每轮成功完成后调用 `memory_service.write_memory(item, metadata)`
  - 从当前轮的 hypothesis + experiment + feedback 中提取知识摘要（用 `knowledge_extraction_prompt()` + LLMAdapter），得到一段 `item: str` 文本
  - 构造 `metadata: Dict[str, str]`，包含 `{"source": "costeer_knowledge_gen", "round": str(round_idx), "scenario": scenario_name}`
  - 调用 `memory_service.write_memory(item=知识摘要文本, metadata=metadata)` 将知识持久化
  - 添加可选参数 `memory_service: Optional[MemoryService]`（默认 None，向后兼容）
  - 只在 feedback 判定为"成功"（acceptable）时保存知识（失败的实验不保存）
  - TDD: 测试知识提取、write_memory 调用、失败时不保存

  **Must NOT do**:
  - 不修改 MemoryService 的现有接口（`write_memory`, `query_context` 等）
  - 不创建新的知识库模块
  - 不新增不存在的类型（如 MemoryRecord）— 直接使用 `write_memory(item: str, metadata: Dict[str, str])` 已有接口
  - 不在非成功轮次保存知识（避免保存错误信息）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 在现有循环中添加一个条件调用，逻辑简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6, T7)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 14
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `core/loop/costeer.py` — CoSTEEREvolver 的循环结构，在何处插入知识提取
  - `memory_service/service.py:MemoryService` — FC-4 MemoryService 的实际接口。公开方法: `write_memory(item: str, metadata: Dict[str, str]) -> None`（line 94-113）和 `query_context(query: Dict[str, str]) -> ContextPack`（line 115-153）。存储到 SQLite `failure_cases` 表
  - 官方 RDAgent `evolving_agent.py` — `self.rag.generate_knowledge(self.evolving_trace); self.rag.dump_knowledge_base()` 模式

  **API/Type References**:
  - `llm/prompts.py:knowledge_extraction_prompt()` — T4 创建的 prompt
  - `memory_service/service.py:write_memory()` — 签名: `write_memory(self, item: str, metadata: Dict[str, str]) -> None`。item 是人类可读摘要字符串，metadata 是键值对索引

  **Test References**:
  - `tests/test_costeer.py` — 在此添加知识自生成测试

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to tests/test_costeer.py
  - [ ] `python -m pytest tests/test_costeer.py -v` → PASS (新增 ≥3 知识自生成测试)

  **QA Scenarios:**

  ```
  Scenario: 成功轮次触发知识保存
    Tool: Bash (python)
    Preconditions: MockMemoryService（继承或 mock MemoryService，记录 write_memory() 调用）
    Steps:
      1. 创建 CoSTEEREvolver(memory_service=MockMemoryService, llm_adapter=MockLLM, ...)
      2. 模拟一轮成功循环（feedback.acceptable = True）
      3. Assert MockMemoryService.write_memory() 被调用1次
      4. Assert 调用参数: item 是非空字符串, metadata 包含 "source": "costeer_knowledge_gen"
    Expected Result: 成功轮次保存知识到 write_memory
    Evidence: .sisyphus/evidence/task-8-knowledge-save.txt

  Scenario: 失败轮次不保存知识
    Tool: Bash (python)
    Preconditions: 同上
    Steps:
      1. 模拟一轮失败循环（feedback.acceptable = False）
      2. Assert MockMemoryService.write_memory() 未被调用
    Expected Result: 失败轮次跳过知识保存
    Evidence: .sisyphus/evidence/task-8-no-save-on-failure.txt

  Scenario: memory_service=None 时无副作用
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. 创建 CoSTEEREvolver(memory_service=None, ...)
      2. 执行完整循环
      3. Assert 无异常
    Expected Result: 向后兼容
    Evidence: .sisyphus/evidence/task-8-no-memory-service.txt
  ```

  **Commit**: YES (groups with T6, T7 — FC-3 wave)
  - Message: `feat(fc3): CoSTEER知识自生成via FC-4 MemoryService.write_memory()`
  - Files: `core/loop/costeer.py`, `tests/test_costeer.py`

- [ ] 9. 升级 ExplorationManager（树结构维护 + 新 scheduler API 集成）

  **What to do**:
  - 修改 `exploration_manager/service.py` 中的 `ExplorationManager`
  - **升级 `register_node()`**: 除了 `graph.nodes.append(node)` 外，还需维护 `graph.edges`：为每个 `parent_id in node.parent_ids` 添加 `GraphEdge(parent_id=pid, child_id=node.node_id)`。同时维护节点的深度追踪（`depth = max(parent.depth for parent in parents) + 1`，root depth=0）
  - **新增 `get_node_depth(graph, node_id) -> int`**: 通过 parent_ids 链计算节点深度（不递归，用 edges 或 parent_ids 查找）
  - **新增 `get_children(graph, node_id) -> List[str]`**: 从 graph.edges 中查找指定节点的子节点列表
  - **新增 `get_path_to_root(graph, node_id) -> List[str]`**: 返回从 node_id 到 root 的路径（用于 backprop 验证）
  - **升级 `select_parents()`**: 使用新 scheduler 的 `select_node()` 方法（接口不变，只是内部调用更新后的 scheduler）
  - **新增 `observe_feedback(graph, node_id, score, decision)`**: 委托给 scheduler.observe_feedback()，在 service 层提供统一入口
  - 确保 `prune_branches()` 和 `merge_traces()` 不受影响
  - TDD: 先写测试验证 edge 维护、depth 计算、children 查询、path_to_root

  **Must NOT do**:
  - 不修改 ExplorationManager 的构造参数签名（只在内部方法新增）
  - 不修改 plugins/contracts.py
  - 不在此 task 中修改 LoopEngine（T10 做）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及图结构维护、边关系管理、多个新方法实现，需要理解数据模型关系
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO（T10, T11 依赖此 task）
  - **Parallel Group**: Wave 3 (first task)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: Task 5 (需要新 scheduler API)

  **References**:

  **Pattern References**:
  - `exploration_manager/service.py` — 现有 ExplorationManager 实现（121行），`register_node()` 在 line 67-82 只做 `graph.nodes.append(node)`，需要增加 edges 维护
  - `data_models.py:GraphEdge` — 现有 GraphEdge 数据类（含 parent_id, child_id 字段），用于构建边
  - `data_models.py:ExplorationGraph` — 包含 `edges: List[GraphEdge]` 字段，目前未被主动维护

  **API/Type References**:
  - `exploration_manager/scheduler.py:MCTSScheduler` — 重写后的 scheduler（T5 产出），包含 `select_node()`, `observe_feedback()`, `backpropagate()` 方法
  - `data_models.py:NodeRecord` — 新增的 `visits`, `total_value`, `avg_value` 字段（T1 产出）

  **Test References**:
  - 目前 `exploration_manager/service.py` 没有独立测试文件。需新建 `tests/test_exploration_manager.py`

  **WHY Each Reference Matters**:
  - service.py 是 LoopEngine 调用 scheduler 的中间层，必须正确委托新 API
  - GraphEdge 和 ExplorationGraph.edges 是已有但未利用的数据结构，需要激活

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_exploration_manager.py
  - [ ] `python -m pytest tests/test_exploration_manager.py -v` → PASS (≥8 tests)

  **QA Scenarios:**

  ```
  Scenario: register_node 自动维护 edges
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. 创建 ExplorationManager, graph, root node (no parents)
      2. register_node(graph, root) → edges 应为空（root 无 parent）
      3. 创建 child node (parent_ids=["root"])
      4. register_node(graph, child) → graph.edges 应包含 GraphEdge(parent_id="root", child_id=child.node_id)
      5. Assert len(graph.edges) == 1
    Expected Result: edges 随 register_node 自动维护
    Failure Indicators: edges 为空或不包含正确的 GraphEdge
    Evidence: .sisyphus/evidence/task-9-edges-maintenance.txt

  Scenario: get_path_to_root 返回正确路径
    Tool: Bash (python)
    Preconditions: 三层树结构 root → A → B
    Steps:
      1. 构建 graph: root (depth=0), A (parent=root, depth=1), B (parent=A, depth=2)
      2. 调用 get_path_to_root(graph, "B")
      3. Assert 返回 ["B", "A", "root"]
    Expected Result: 完整的叶→root 路径
    Failure Indicators: 路径不完整或顺序错误
    Evidence: .sisyphus/evidence/task-9-path-to-root.txt

  Scenario: observe_feedback 正确委托给 scheduler
    Tool: Bash (python)
    Preconditions: ExplorationManager 已注入新 MCTSScheduler
    Steps:
      1. 创建 graph with root + child nodes
      2. 调用 exploration_manager.observe_feedback(graph, "child", score=0.7, decision=True)
      3. Assert child node 的 visits >= 1（说明 backprop 被触发）
    Expected Result: observe_feedback 通过 scheduler 触发 backprop
    Evidence: .sisyphus/evidence/task-9-observe-feedback.txt
  ```

  **Commit**: YES (groups with T10, T11, T12 — Wave 3)
  - Message: `feat(fc2): ExplorationManager树结构维护+observe_feedback委托`
  - Files: `exploration_manager/service.py`, `tests/test_exploration_manager.py`

- [ ] 10. 升级 LoopEngine（select→expand→evaluate→backprop 完整 MCTS 流程）

  **What to do**:
  - 修改 `core/loop/engine.py` 中的 `LoopEngine.run()` 方法的 scheduler 分支（`else` 块，line 146-207）
  - **当前问题**: scheduler 分支只调用 `select_node` → `execute_iteration` → `register_node` → `update_visit_count`。缺少 backpropagation 和 reward 计算
  - **升级为完整 MCTS 流程**:
    1. `select`: `scheduler.select_node(graph)` → 选择最优节点
    2. `expand`: `step_executor.execute_iteration(...)` → 执行迭代产生新节点
    3. `register`: `exploration_manager.register_node(graph, node)` → 注册节点（包含 edge 维护，T9 产出）
    4. `evaluate`: 从 `step_result.score.value` 获取评估分数（或从 `step_result.feedback` 获取 decision）
    5. `backprop`: `exploration_manager.observe_feedback(graph, node.node_id, score, decision)` → 通过 ExplorationManager 触发 backprop
  - **删除** `scheduler.update_visit_count(graph, node.node_id)` 调用（line 207）— 被 backprop 替代
  - **Layer-0 初始化**: 当 `graph.nodes` 为空且 scheduler 存在时，调用 Layer-0 Diversity（T11）生成多样化初始节点，而非单个 "root" 节点
  - **保留** non-scheduler 分支（`if self._scheduler is None`）不变
  - TDD: 先写测试验证完整 MCTS 流程，包括 backprop 被调用

  **Must NOT do**:
  - 不修改 non-scheduler 分支（`if self._scheduler is None` 块）
  - 不引入 asyncio
  - 不修改 LoopEngine 构造参数签名
  - 不修改 plugins/contracts.py

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心循环升级，涉及多组件协调（scheduler + exploration_manager + step_executor），需要精确理解执行流程和状态转换
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after T9)
  - **Blocks**: Tasks 13
  - **Blocked By**: Tasks 5, 9 (需要新 scheduler 和升级后的 ExplorationManager)

  **References**:

  **Pattern References**:
  - `core/loop/engine.py:146-207` — 现有 scheduler 分支代码，需要升级。关键行：line 148 select_node, line 159 execute_iteration, line 203 register_node, line 207 update_visit_count（要删除）
  - `core/loop/engine.py:81-82` — Layer-0 初始化：当前只添加一个 "root" NodeRecord。需要替换为 Layer-0 Diversity 调用

  **API/Type References**:
  - `exploration_manager/service.py:ExplorationManager` — 升级后（T9）的 `register_node()` 和 `observe_feedback()` 方法
  - `exploration_manager/scheduler.py:MCTSScheduler` — 重写后（T5）的 `select_node()` 和 `backpropagate()` 方法
  - `data_models.py:StepResult` — `step_result.score.value` 是评估分数来源

  **Test References**:
  - `tests/test_e2e_fc2_fc3.py:test_full_loop_with_reasoning_and_branches` — 现有 E2E 测试通过 build_runtime 运行完整循环。需要确保升级后此测试仍能通过（或适配新行为）

  **WHY Each Reference Matters**:
  - engine.py 是 MCTS 循环的控制中心，升级必须保持与 scheduler、exploration_manager、step_executor 的正确交互
  - 现有 E2E 测试是最重要的回归检查

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests updated/added in tests/test_e2e_fc2_fc3.py or new tests/test_loop_engine_mcts.py
  - [ ] `python -m pytest tests/test_loop_engine_mcts.py -v` → PASS (≥5 tests)

  **QA Scenarios:**

  ```
  Scenario: 完整 MCTS 循环 — select→expand→backprop
    Tool: Bash (python)
    Preconditions: Mock 所有外部依赖（planner, step_executor, memory_service, stores）
    Steps:
      1. 创建 LoopEngine with scheduler + exploration_manager
      2. 配置 step_executor mock 返回 score=0.8 的 step_result
      3. 调用 engine.run(run_session, task_summary, max_loops=2)
      4. Assert scheduler.select_node 被调用 ≥2 次
      5. Assert exploration_manager.observe_feedback 被调用（而非旧的 update_visit_count）
      6. Assert 注册的节点有 visits > 0（backprop 生效）
    Expected Result: 完整 MCTS 流程运行，backprop 传播 reward
    Failure Indicators: update_visit_count 仍被调用，或 observe_feedback 未被调用
    Evidence: .sisyphus/evidence/task-10-mcts-loop.txt

  Scenario: Layer-0 初始化调用 diversity 生成
    Tool: Bash (python)
    Preconditions: graph 初始为空
    Steps:
      1. 创建 LoopEngine with scheduler + layer0_diversity 组件
      2. 调用 engine.run(...)
      3. Assert 初始 graph.nodes 中有 > 1 个节点（多样化根节点）
      4. 或 Assert layer0 diversity 方法被调用
    Expected Result: 不再是单个 "root" 节点，而是多个多样化初始节点
    Failure Indicators: 只有一个 "root" 节点
    Evidence: .sisyphus/evidence/task-10-layer0-init.txt

  Scenario: 旧代码中的 update_visit_count 不再存在
    Tool: Bash (grep)
    Preconditions: None
    Steps:
      1. grep -n "update_visit_count" core/loop/engine.py
      2. Assert 无匹配结果（该调用已被删除）
    Expected Result: engine.py 中不再调用 update_visit_count
    Evidence: .sisyphus/evidence/task-10-no-update-visit-count.txt
  ```

  **Commit**: YES (groups with T9, T11, T12 — Wave 3)
  - Message: `feat(fc2): LoopEngine完整MCTS循环(select→expand→backprop)`
  - Files: `core/loop/engine.py`, `tests/test_loop_engine_mcts.py`

- [ ] 11. Layer-0 Diversity via VirtualEvaluator

  **What to do**:
  - **在 `exploration_manager/service.py` 中新增方法 `generate_diverse_roots(graph, task_summary, scenario_name, n_candidates, k_forward) -> ExplorationGraph`**
  - 此方法在图为空时被调用（由 LoopEngine T10 集成）
  - 内部调用 `VirtualEvaluator.evaluate()` 生成 N 个候选 → 选择 K 个
  - 将选中的 K 个 ExperimentDesign 转换为 K 个 NodeRecord 作为 root 层节点（parent_ids=[], depth=0）
  - 每个 root 节点的 `proposal_id` 来自 ExperimentDesign.summary 的哈希
  - 可选: 在 `ExplorationManager.__init__` 中添加 `virtual_evaluator: Optional[VirtualEvaluator]` 参数（默认 None）
  - 当 virtual_evaluator 为 None 时，fallback 到单个 "root" 节点（保守/向后兼容）
  - TDD: 测试 diverse root 生成、fallback 行为、节点属性

  **Must NOT do**:
  - 不修改 VirtualEvaluator 本身（T11 只是调用它）
  - 不在此 task 中修改 LoopEngine（T10 做集成）
  - 不引入新依赖

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要协调 VirtualEvaluator 和 ExplorationManager，理解 ExperimentDesign → NodeRecord 的映射
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T10, T12 — 但 T10 依赖 T9，T11 也依赖 T9)
  - **Parallel Group**: Wave 3 (after T9, parallel with T10/T12)
  - **Blocks**: Task 13
  - **Blocked By**: Task 9 (需要升级后的 ExplorationManager)

  **References**:

  **Pattern References**:
  - `core/reasoning/virtual_eval.py:VirtualEvaluator` — `evaluate()` 方法签名: `evaluate(task_summary, scenario_name, iteration, previous_results, current_scores, ...) -> List[ExperimentDesign]`
  - `exploration_manager/service.py:ExplorationManager` — 需要在此类中新增 `generate_diverse_roots()` 方法
  - 论文 Layer-0 Diversity: 第一层需最大化 solution 多样性。VirtualEvaluator 的 `_diversify_prompt()` 已有 diversity hint 机制

  **API/Type References**:
  - `llm/schemas.py:ExperimentDesign` — summary, rationale, experiment_plan, virtual_score 字段
  - `data_models.py:NodeRecord` — 需要从 ExperimentDesign 映射: node_id=uuid, parent_ids=[], proposal_id=hash(summary), score=virtual_score

  **Test References**:
  - `tests/test_e2e_fc2_fc3.py:test_virtual_eval_produces_multiple_candidates` — VirtualEvaluator 的现有测试，验证 N=3/K=2 输出2个 ExperimentDesign

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to tests/test_exploration_manager.py
  - [ ] `python -m pytest tests/test_exploration_manager.py -v -k "diversity"` → PASS (≥3 tests)

  **QA Scenarios:**

  ```
  Scenario: Layer-0 生成多个多样化根节点
    Tool: Bash (python)
    Preconditions: MockLLMAdapter, VirtualEvaluator(n=3, k=2)
    Steps:
      1. 创建 ExplorationManager with virtual_evaluator=VirtualEvaluator(mock_llm, n=3, k=2)
      2. 调用 generate_diverse_roots(empty_graph, "classify images", "data_science", n=3, k=2)
      3. Assert graph.nodes 中有 2 个节点
      4. Assert 所有节点 parent_ids == []
      5. Assert 所有节点 node_id 不同
    Expected Result: 2 个多样化根节点被创建
    Failure Indicators: 只有1个节点，或 parent_ids 不为空
    Evidence: .sisyphus/evidence/task-11-diverse-roots.txt

  Scenario: virtual_evaluator=None 时 fallback 到单个 root
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. 创建 ExplorationManager(virtual_evaluator=None)
      2. 调用 generate_diverse_roots(empty_graph, ...)
      3. Assert graph.nodes 中有 1 个节点
      4. Assert 节点 node_id == "root"
    Expected Result: 保守 fallback 行为
    Evidence: .sisyphus/evidence/task-11-fallback-single-root.txt
  ```

  **Commit**: YES (groups with T9, T10, T12 — Wave 3)
  - Message: `feat(fc2): Layer-0 Diversity通过VirtualEvaluator生成多样化根节点`
  - Files: `exploration_manager/service.py`, `tests/test_exploration_manager.py`

- [ ] 12. 升级 app/runtime.py wiring + AppConfig

  **What to do**:
  - **修改 `app/config.py:AppConfig`**: 新增配置字段（都必须有默认值，因为 frozen=True dataclass）:
    - `mcts_c_puct: float = 1.41` — PUCT 的探索系数（替代或兼容 `mcts_exploration_weight`）
    - `mcts_reward_mode: str = "score_based"` — reward 计算模式
    - `layer0_n_candidates: int = 5` — Layer-0 候选数
    - `layer0_k_forward: int = 2` — Layer-0 前进数
  - **修改 `app/runtime.py:build_runtime()`**: 更新 MCTSScheduler 构造调用以传入 RewardCalculator
  - 更新 LoopEngine 构造以传入升级后的 scheduler
  - 可选: 如果 LoopEngine 现在需要 VirtualEvaluator（for Layer-0），在 `build_run_service()` 中注入
  - **修改 `app/runtime.py:build_run_service()`**: 更新 LoopEngine 构造，确保所有新依赖正确注入
  - 修改 `load_config()` 以读取新环境变量
  - TDD: 测试 build_runtime 成功、新 config 字段默认值、scheduler 正确接收 RewardCalculator

  **Must NOT do**:
  - 不修改 plugins/contracts.py
  - 不修改 AppConfig 的 frozen=True 约束
  - 不移除现有的 `mcts_exploration_weight` 字段（保持向后兼容，新字段可以是别名）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 配置和 wiring 更新，模式固定，改动明确
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T10, T11 — 但要在 T5 和 T9 之后)
  - **Parallel Group**: Wave 3 (parallel with T10, T11)
  - **Blocks**: Tasks 13, 14
  - **Blocked By**: Tasks 5, 9 (需要新 scheduler 和升级后的 ExplorationManager)

  **References**:

  **Pattern References**:
  - `app/config.py:AppConfig` — frozen=True dataclass，所有字段有默认值或在 load_config() 中赋值。新字段必须遵循此模式
  - `app/config.py:load_config()` — 从 env_map 读取环境变量，使用 `_get_int`/`_get_bool`/`float()` 解析
  - `app/runtime.py:build_runtime()` — 当前 MCTSScheduler 构造: `MCTSScheduler(exploration_weight=config.mcts_exploration_weight)`。需要更新为传入 RewardCalculator
  - `app/runtime.py:build_run_service()` — LoopEngine 构造: line 143-152。需要确保新依赖正确传入

  **API/Type References**:
  - `exploration_manager/scheduler.py:MCTSScheduler` — 重写后（T5）的构造参数
  - `exploration_manager/reward.py:RewardCalculator` — T3 创建的 RewardCalculator 构造参数
  - `core/reasoning/virtual_eval.py:VirtualEvaluator` — 可能需要在 runtime 中创建实例

  **Test References**:
  - 项目中涉及 `build_runtime()` 的测试（如 `test_e2e_fc2_fc3.py:setUp` 中调用 `build_runtime()`），确保修改后不报错

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests: 在现有 runtime 相关测试中验证或新建 tests/test_runtime_wiring.py
  - [ ] `python -m pytest tests/ -v -k "runtime or build_runtime"` → PASS

  **QA Scenarios:**

  ```
  Scenario: build_runtime 成功构建且 scheduler 有 RewardCalculator
    Tool: Bash (python)
    Preconditions: 环境变量设置为 mock provider
    Steps:
      1. 设置环境变量 RD_AGENT_LLM_PROVIDER=mock
      2. python -c "import os; os.environ['RD_AGENT_LLM_PROVIDER']='mock'; from app.runtime import build_runtime; rt = build_runtime(); print(type(rt.scheduler).__name__, hasattr(rt.scheduler, 'backpropagate'))"
      3. Assert output contains "MCTSScheduler True"
    Expected Result: scheduler 是新 MCTSScheduler，有 backpropagate 方法
    Failure Indicators: ImportError 或 scheduler 缺少新方法
    Evidence: .sisyphus/evidence/task-12-runtime-wiring.txt

  Scenario: 新 config 字段有正确默认值
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -c "from app.config import load_config; c = load_config({}); print(c.mcts_c_puct, c.mcts_reward_mode, c.layer0_n_candidates, c.layer0_k_forward)"
      2. Assert output is "1.41 score_based 5 2"
    Expected Result: 所有新字段有合理默认值
    Evidence: .sisyphus/evidence/task-12-config-defaults.txt

  Scenario: 全部现有 E2E 测试在新 wiring 下通过
    Tool: Bash (python)
    Preconditions: None
    Steps:
      1. python -m pytest tests/test_e2e_fc2_fc3.py -v 2>&1 | tail -10
      2. Assert "passed" in output, 0 failures
    Expected Result: 旧 E2E 测试完全兼容新 wiring
    Failure Indicators: 任何测试失败
    Evidence: .sisyphus/evidence/task-12-e2e-compat.txt
  ```

  **Commit**: YES (groups with T9, T10, T11 — Wave 3)
  - Message: `feat(config): 更新AppConfig和runtime wiring支持完整MCTS配置`
  - Files: `app/config.py`, `app/runtime.py`, `tests/test_runtime_wiring.py`

- [ ] 13. E2E 集成测试 — FC-2 完整 MCTS 循环

  **What to do**:
  - **重写** `tests/test_e2e_fc2_fc3.py` 中的 FC-2 相关测试（`test_mcts_selection_with_multiple_nodes` 已过时）
  - **新增测试**: `test_mcts_full_cycle_select_expand_backprop` — 验证完整 MCTS 循环:
    1. 构建一个 3 层树（root → 2 children → 4 leaves）
    2. 运行 select → expand → evaluate → backprop 完整流程
    3. Assert backprop 后所有祖先的 visits/total_value 正确更新
    4. Assert 再次 select 时 PUCT 考虑了更新后的 Q 和 P 值
  - **新增测试**: `test_layer0_diversity_creates_multiple_roots` — 验证 Layer-0 diversity 通过 build_runtime 生成多样化根节点
  - **新增测试**: `test_full_loop_with_backprop_integration` — 通过 `build_run_service` 运行 2 轮循环，验证:
    1. 节点的 visits > 0（backprop 生效）
    2. 至少 2 个不同节点被选择过（探索有效）
    3. edges 被正确维护
  - **保留/适配**: `test_prune_then_merge_pipeline` — 此测试独立于 scheduler，应保持兼容
  - **适配**: `test_full_loop_with_reasoning_and_branches` — 确保在新 MCTS 流程下仍然通过
  - TDD: 先写新测试（RED），确保现有通过的测试不被破坏

  **Must NOT do**:
  - 不修改 FC-3 相关测试（T14 做）
  - 不修改任何非测试源代码
  - 不删除 `test_prune_then_merge_pipeline`（它独立于 scheduler 改动）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: E2E 集成测试需要理解完整 MCTS 流程中多组件的交互，构造复杂的测试场景
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T14, T15)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 10, 11, 12 (需要完整的 Wave 3 产出)

  **References**:

  **Pattern References**:
  - `tests/test_e2e_fc2_fc3.py` — 现有 E2E 测试文件（153行），setUp 使用 tempdir + env patch + build_runtime
  - `tests/test_e2e_fc2_fc3.py:test_mcts_selection_with_multiple_nodes` (line 86-115) — 要被重写的旧测试，使用 `update_visit_count` API 已过时
  - `tests/test_e2e_fc2_fc3.py:test_full_loop_with_reasoning_and_branches` (line 39-71) — 要保持兼容/适配的集成测试

  **API/Type References**:
  - `exploration_manager/scheduler.py:MCTSScheduler` — 新 API: `select_node()`, `observe_feedback()`, `backpropagate()`
  - `exploration_manager/service.py:ExplorationManager` — 新 API: `observe_feedback()`, `generate_diverse_roots()`
  - `data_models.py:NodeRecord` — 新字段: visits, total_value, avg_value

  **Test References**:
  - `tests/test_scheduler_mcts.py` — 单元测试层面已验证 PUCT + backprop，E2E 验证集成
  - `tests/test_exploration_manager.py` — 单元测试层面已验证 ExplorationManager，E2E 验证端到端

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: tests/test_e2e_fc2_fc3.py (updated)
  - [ ] `python -m pytest tests/test_e2e_fc2_fc3.py -v` → PASS (≥5 tests, including 3 new)

  **QA Scenarios:**

  ```
  Scenario: 完整 MCTS E2E — 2 轮循环后节点有 backprop 数据
    Tool: Bash (python -m pytest)
    Preconditions: All Wave 1-3 changes committed
    Steps:
      1. python -m pytest tests/test_e2e_fc2_fc3.py::TestFC2FC3Integration::test_full_loop_with_backprop_integration -v
      2. Assert test PASSED
      3. Inspect test output: 验证至少有节点 visits > 0
    Expected Result: 新 E2E 测试通过，证明 backprop 在真实循环中生效
    Failure Indicators: 测试失败或 visits 全为 0
    Evidence: .sisyphus/evidence/task-13-e2e-mcts.txt

  Scenario: 旧 E2E 测试兼容新实现
    Tool: Bash (python -m pytest)
    Preconditions: None
    Steps:
      1. python -m pytest tests/test_e2e_fc2_fc3.py::TestFC2FC3Integration::test_full_loop_with_reasoning_and_branches -v
      2. Assert test PASSED
    Expected Result: 旧测试在新 MCTS 实现下仍然通过
    Failure Indicators: 测试失败
    Evidence: .sisyphus/evidence/task-13-e2e-compat.txt
  ```

  **Commit**: YES (groups with T14, T15 — Wave 4)
  - Message: `test(fc2): E2E集成测试覆盖完整MCTS循环+backprop+layer-0`
  - Files: `tests/test_e2e_fc2_fc3.py`

- [ ] 14. E2E 集成测试 — FC-3 CoSTEER 完整循环

  **What to do**:
  - **新增/扩展** FC-3 相关的 E2E 测试，验证升级后的 CoSTEER 完整循环
  - **新增测试**: `test_costeer_structured_feedback_e2e` — 通过 mock 环境验证:
    1. CoSTEEREvolver 在有 llm_adapter 时生成 StructuredFeedback
    2. StructuredFeedback 的三个维度（execution, return_checking, code）被正确传递
    3. 反馈信息影响下一轮的 hypothesis 生成
  - **新增测试**: `test_costeer_knowledge_self_gen_e2e` — 验证:
    1. 成功轮次后 MemoryService.store() 被调用
    2. 存储的 MemoryRecord 包含有意义的知识摘要
    3. 失败轮次不触发 store()
  - **新增测试**: `test_reasoning_trace_persisted_e2e` — 验证:
    1. ReasoningPipeline 在有 trace_store 时保存 trace
    2. trace 包含 analysis/problem/hypothesis/design 四个阶段数据
  - **新增测试**: `test_fc3_full_loop_with_trace_and_feedback` — 通过 build_run_service 运行完整循环:
    1. ReasoningPipeline 生成 trace
    2. CoSTEER 产生结构化反馈
    3. 知识被存储到 MemoryService
    4. 所有组件协调工作无异常
  - TDD: 先写测试，验证新功能集成

  **Must NOT do**:
  - 不修改 FC-2 相关测试（T13 做）
  - 不修改任何非测试源代码

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: FC-3 E2E 测试需要协调 ReasoningPipeline, CoSTEEREvolver, MemoryService 多组件
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T13, T15)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 6, 7, 8, 12 (需要 FC-3 升级和新 wiring)

  **References**:

  **Pattern References**:
  - `tests/test_e2e_fc2_fc3.py` — 现有 E2E 测试模式（setUp with tempdir + env patch）
  - `tests/test_costeer.py` — 单元测试层面的 CoSTEER 测试
  - `tests/test_reasoning_pipeline.py` — 单元测试层面的 pipeline 测试
  - `tests/test_scenario_fc3_integration.py` — 现有场景集成测试（262行，10 tests），模式参考

  **API/Type References**:
  - `core/loop/costeer.py:CoSTEEREvolver` — 升级后（T7/T8）的 evolve() 方法
  - `core/reasoning/pipeline.py:ReasoningPipeline` — 升级后（T6）带 trace_store 参数
  - `llm/schemas.py:StructuredFeedback` — T2 创建的反馈 schema
  - `memory_service:MemoryService` — FC-4 的 store() 接口

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to tests/test_e2e_fc2_fc3.py or new tests/test_e2e_fc3.py
  - [ ] `python -m pytest tests/test_e2e_fc3.py -v` → PASS (≥4 tests)

  **QA Scenarios:**

  ```
  Scenario: CoSTEER 结构化反馈 E2E 流程
    Tool: Bash (python -m pytest)
    Preconditions: All FC-3 upgrades (T6, T7, T8) complete
    Steps:
      1. python -m pytest tests/test_e2e_fc3.py::test_costeer_structured_feedback_e2e -v
      2. Assert test PASSED
    Expected Result: 结构化反馈在 E2E 环境中生成并传递
    Failure Indicators: 测试失败或反馈缺少维度
    Evidence: .sisyphus/evidence/task-14-e2e-feedback.txt

  Scenario: FC-3 完整循环 — trace + feedback + knowledge
    Tool: Bash (python -m pytest)
    Preconditions: None
    Steps:
      1. python -m pytest tests/test_e2e_fc3.py::test_fc3_full_loop_with_trace_and_feedback -v
      2. Assert test PASSED
    Expected Result: 所有 FC-3 组件在完整循环中协调工作
    Evidence: .sisyphus/evidence/task-14-e2e-full-loop.txt
  ```

  **Commit**: YES (groups with T13, T15 — Wave 4)
  - Message: `test(fc3): E2E集成测试覆盖结构化反馈+trace持久化+知识自生成`
  - Files: `tests/test_e2e_fc3.py`

- [ ] 15. 回归测试 + gap analysis 文档更新

  **What to do**:
  - **回归测试**: 运行完整测试套件 `python -m pytest tests/ -v`，确保:
    1. 所有新测试通过
    2. 所有旧测试仍然通过（或被正确迁移）
    3. 总测试数量 > 429（原始数量）
    4. 0 failures, 0 errors
  - **文档更新**: 修改 `dev_doc/paper_gap_analysis.md`，将 FC-2 和 FC-3 的状态从"早期版本"更新为"完整实现":
    - FC-2: 标记 backpropagation, PUCT, reward, layer-0 diversity 为已实现
    - FC-3: 标记 trace 持久化, 结构化反馈, 知识自生成为已实现
    - 更新剩余差距（如有）
  - **测试计数对账**: 记录最终测试数量和分布（per test file）
  - TDD: 本 task 不需要新测试，只是运行和验证

  **Must NOT do**:
  - 不修改任何源代码
  - 不跳过任何测试
  - 不修改 plugins/contracts.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要全面运行测试套件并分析结果，同时更新文档
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (需要 T13 和 T14 都完成)
  - **Parallel Group**: Wave 4 (after T13, T14)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 13, 14

  **References**:

  **Pattern References**:
  - `dev_doc/paper_gap_analysis.md` — 现有 gap analysis 文档，包含每个 FC 的状态和剩余差距

  **Test References**:
  - `tests/` — 完整测试目录

  **Acceptance Criteria**:

  **TDD:**
  - [ ] `python -m pytest tests/ -v` → ALL PASS, 0 failures
  - [ ] 测试总数 > 429

  **QA Scenarios:**

  ```
  Scenario: 完整回归测试通过
    Tool: Bash (python -m pytest)
    Preconditions: All T1-T14 complete
    Steps:
      1. python -m pytest tests/ -v 2>&1 | tail -20
      2. Assert "passed" in output
      3. Assert "0 failed" or no "failed" in output
      4. Record total test count
    Expected Result: 所有测试通过，总数 > 429
    Failure Indicators: 任何测试失败
    Evidence: .sisyphus/evidence/task-15-regression.txt

  Scenario: Gap analysis 文档正确更新
    Tool: Bash (grep)
    Preconditions: dev_doc/paper_gap_analysis.md 已更新
    Steps:
      1. grep -i "完整实现\|fully implemented\|backprop\|PUCT\|layer-0" dev_doc/paper_gap_analysis.md
      2. Assert FC-2 和 FC-3 被标记为完整实现
    Expected Result: 文档准确反映当前实现状态
    Evidence: .sisyphus/evidence/task-15-gap-doc.txt

  Scenario: plugins/contracts.py 未被修改
    Tool: Bash (git diff)
    Preconditions: None
    Steps:
      1. git diff HEAD -- plugins/contracts.py
      2. Assert 输出为空（无改动）
    Expected Result: Protocol 签名完全不变
    Evidence: .sisyphus/evidence/task-15-contracts-unchanged.txt
  ```

  **Commit**: YES
  - Message: `test(fc2-fc3): 回归验证通过+gap analysis文档更新为完整实现`
  - Files: `dev_doc/paper_gap_analysis.md`
  - Pre-commit: `python -m pytest tests/ -v`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/ -v` + check for `# type: ignore`, empty catches, console prints in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify all new code follows existing patterns in codebase.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — Functional Verification** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (FC-2 scheduler + FC-3 reasoning working together in LoopEngine). Test edge cases: empty graph, single node, all nodes pruned. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Verify plugins/contracts.py is UNCHANGED.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1 complete**: `feat(data-models): 扩展MCTS统计字段和FC-3结构化反馈schema` — data_models.py, llm/schemas.py, exploration_manager/reward.py
- **Wave 2 complete (FC-2)**: `feat(fc2): 重写MCTSScheduler实现完整PUCT+backprop+reward` — exploration_manager/scheduler.py, tests/
- **Wave 2 complete (FC-3)**: `feat(fc3): 增强trace持久化+结构化反馈闭环+知识自生成` — core/reasoning/, core/loop/costeer.py, tests/
- **Wave 3 complete**: `feat(fc2): 集成完整MCTS流程到LoopEngine+Layer-0多样性` — exploration_manager/service.py, core/loop/engine.py, app/
- **Wave 4 complete**: `test(fc2-fc3): E2E集成测试+回归验证+gap分析文档更新` — tests/, dev_doc/

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/ -v  # Expected: ALL tests pass, 0 failures
python -m pytest tests/test_scheduler_mcts.py -v  # Expected: New MCTS tests pass (backprop, PUCT, reward)
python -m pytest tests/test_reasoning_pipeline.py -v  # Expected: Trace persistence tests pass
python -m pytest tests/test_costeer.py -v  # Expected: Structured feedback tests pass
python -m pytest tests/test_e2e_fc2_fc3.py -v  # Expected: End-to-end integration passes
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (total count should increase from 429)
- [ ] plugins/contracts.py unchanged (git diff shows no changes)
- [ ] FC-2 ablation-critical features implemented (backprop, PUCT, layer-0 diversity)
- [ ] FC-3 trace persistence functional
- [ ] FC-3 structured feedback loop functional
