# Paper Gap Analysis: RDAgent 6 Framework Components

## TL;DR

> **Quick Summary**: 写一份正式的差距分析文档，逐一对照 RDAgent 论文的 6 个 Framework Components (FC) 与当前 my-RDagent 实现之间的差距，给出基于消融实验数据的优先级排序和可操作的实施路线图。
> 
> **Deliverables**:
> - `dev_doc/paper_gap_analysis.md` — 完整的差距分析文档
> - 一个 git commit
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO — 单任务
> **Critical Path**: Task 1 → Done

---

## Context

### Original Request
用户要求阅读 RDAgent 原版论文，对比目前版本与论文想要达到的效果差距多少。论文已全部读完（33页），所有6个FC组件、Algorithm 1、消融实验数据、完整 prompt 模板（Appendix E）均已提取。当前实现已逐文件审读。现在需要将分析结果写成正式文档。

### Interview Summary
**Key Discussions**:
- 论文定义了 2 个阶段（Research + Development）和 6 个 FC 组件
- 消融实验显示 Exploration Path 影响最大（移除后下降28%），Memory Context 影响最小（9%）
- 当前实现是单链顺序执行，缺乏并行分支、多步推理、时间感知规划等核心能力
- 用户偏好务实方法——文档要可操作，不要学术化

**Research Findings**:
- 论文 Algorithm 1：时间预算循环 + DAG探索 + 跨分支记忆 + 虚拟评估
- 当前实现：顺序单链循环 + 简单迭代策略 + SQLite失败案例存储
- 论文 Appendix E 包含所有 6 个组件的完整 prompt，可作为未来实现参考

### Metis Review
**Identified Gaps** (addressed):
- **目标读者未定义**: 默认为项目维护者自用技术文档
- **ablation 数据适用性**: 文档中加 caveat section 声明论文消融数据的局限性
- **"设计选择"vs"能力缺失"区分**: 只标记能力缺失为 gap，不同的工程选择不算 gap
- **Roadmap 膨胀风险**: 每个 gap 的 action items 限制 3-5 个 bullet，只写 what 不写 how
- **severity 评级标准**: 文档开头必须定义 CRITICAL/MAJOR/MINOR 的具体含义

---

## Work Objectives

### Core Objective
产出一份结构化的差距分析文档，让项目维护者清楚知道：论文要什么、我们有什么、差在哪里、先做什么。

### Concrete Deliverables
- `dev_doc/paper_gap_analysis.md` — 包含 6 个 FC 组件对照、严重性评级、优先级路线图

### Definition of Done
- [ ] 文件 `dev_doc/paper_gap_analysis.md` 存在且 markdown 格式正确
- [ ] 6 个 FC 组件全部覆盖（每个有 Paper Vision / Current State / Gap Rating）
- [ ] 评级标准有明确定义
- [ ] 有 Methodology & Caveats section
- [ ] 有 Prioritized Roadmap section
- [ ] 文档字数 2000-6000 词
- [ ] 无 placeholder 文本（TODO/TBD/FIXME）
- [ ] git commit 成功

### Must Have
- 6 个 FC 组件的完整对照分析
- 明确的 severity rating 定义标准
- 基于消融实验数据的优先级排序
- Methodology & Caveats section 声明分析局限性
- 总结对照表（一目了然）

### Must NOT Have (Guardrails)
- 不包含任何实现代码或伪代码
- 不做任何新的代码探索——完全基于已有分析结果
- 不产出 `paper_gap_analysis.md` 以外的任何文件
- 不把"不同的设计选择"标记为 gap——只有"能力缺失"才是 gap
- 不在 roadmap 中给出时间估算
- 不评价论文方法的优劣（这是差距分析，不是论文评审）
- 不在 roadmap 中写设计方案（what not how，每项不超过 5 个 bullet）
- 不修改任何已有文件

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: None (文档任务无需单元测试)
- **Framework**: N/A

### QA Policy
Agent 必须执行以下验证命令并保存证据。

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Single Task):
└── Task 1: Write gap analysis document and commit [writing]

Wave FINAL (After Task 1):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Document quality review (unspecified-high)
└── Task F3: Scope fidelity check (deep)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | None | F1, F2, F3 |
| F1 | 1 | — |
| F2 | 1 | — |
| F3 | 1 | — |

### Agent Dispatch Summary

- **Wave 1**: **1** — T1 → `writing` + `git-master`
- **Wave FINAL**: **3** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `deep`

---

## TODOs

- [ ] 1. Write paper gap analysis document and commit

  **What to do**:
  1. 写 `dev_doc/paper_gap_analysis.md`，包含以下结构：
     - **Header**: 标题、日期、基于的 commit hash、文档目的
     - **Methodology & Caveats**:
       - 声明评级为基于论文描述和代码审读的主观判断
       - 声明消融实验数据来自论文的完整系统，直接应用于我们的不完整实现有局限性
       - 声明文件路径基于当前 commit 时的状态，未来可能变更
     - **Severity Rating Definitions**:
       - CRITICAL = 论文核心能力完全缺失，预期对性能有最大影响（消融下降 >20%），是实现论文愿景的阻塞项
       - MAJOR = 显著能力差距，有部分替代方案但效果有限，消融下降 10-20%
       - SIGNIFICANT = 能力存在但不完整，需要增强，消融下降 <10% 或论文未单独测试
       - MINOR = 细节差异，对核心功能影响有限
     - **6 个 FC Component Sections**（每个包含三部分）:
       - **FC-1 Planning (动态时间感知规划)**: Paper Vision / Current State / Gap Rating + Evidence → **MAJOR**
       - **FC-2 Exploration Path Structuring (自适应DAG探索)**: Paper Vision / Current State / Gap Rating + Evidence → **CRITICAL**
       - **FC-3 Reasoning Pipeline (科学多步推理)**: Paper Vision / Current State / Gap Rating + Evidence → **MAJOR**
       - **FC-4 Memory Context (协作跨分支记忆)**: Paper Vision / Current State / Gap Rating + Evidence → **MAJOR**
       - **FC-5 Coding Workflow (高效迭代调试)**: Paper Vision / Current State / Gap Rating + Evidence → **SIGNIFICANT**
       - **FC-6 Evaluation Strategy (自动化评估策略)**: Paper Vision / Current State / Gap Rating + Evidence → **SIGNIFICANT**
     - **Summary Table**: 6 个组件的一览表（组件 | 评级 | 论文关键特性 | 当前状态 | 消融影响）
     - **Prioritized Implementation Roadmap**:
       - 按消融实验影响排序（Exploration Path > Planning/Reasoning/Memory > Coding/Evaluation）
       - 每个 gap 给 3-5 个 bullet point 的 action items（只描述 what，不描述 how）
       - 考虑依赖关系：某些 FC 可能是其他 FC 的前置条件
     - **Appendix**: 论文完整引用信息、相关论文章节索引（Algorithm 1 位置、Appendix E 位置等）

  2. 写文档时必须使用的具体数据来源（全部来自已完成的分析，不需要重新读取）：

     **论文侧数据**:
     - Algorithm 1: 6 步循环（Planning → Exploration → Memory → Reasoning → Coding → Evaluation）
     - FC-1 Planning: 动态时间感知策略，早期限制预算鼓励新颖性，后期允许昂贵方法
     - FC-2 Exploration Path: 自适应 DAG，多并行分支，第一层最大化多样性，贪心利用最优，剪枝次优路径，最终多轨迹合并
     - FC-3 Reasoning Pipeline: 4 步科学推理（分析现有方案→识别关键问题→形成假设→输出可实现想法），包含虚拟评估（LLM评估多个想法只发送最优）
     - FC-4 Memory Context: 3 个假设来源（当前分支hc、全局最优h⋆、概率采样hs），交互核（余弦相似度+分数差+衰减因子），LLM自适应假设选择（Select/Modify/Generate）
     - FC-5 Coding Workflow: Debug 模式（10%数据采样、epoch缩减、时间估算），多阶段评估（执行成功→竞赛对齐→debug合规→提交真实性）
     - FC-6 Evaluation Strategy: 自动化数据分割（90/10分层），标准化评分脚本，ValidationSelector多候选重新验证
     - 消融实验: Exploration Path 移除=28%下降(最大), Memory Context 移除=9%下降(最小)
     - 成本: ~$21/competition with GPT-5, 12h runtime, single V100
     - RAG 负面结果: 总体性能从 35.1% 降到 32.0%

     **实现侧数据**:
     - FC-1: `llm/prompts.py` 中 `_iteration_strategy()` — 简单3层迭代逻辑，无时间预算感知
     - FC-2: 仅单链顺序执行。`BranchTraceStore` 存在于设计文档中但未实现并行分支、合并、剪枝
     - FC-3: 单步 LLM 调用生成提案。无问题识别→假设→虚拟评估管道
     - FC-4: `memory_service/service.py` — SQLite 失败案例存储（145行）。无跨分支通信、交互核、嵌入
     - FC-5: `core/loop/costeer.py` — CoSTEER 多轮代码演化（49行），有迭代但无 debug 模式、10%采样、时间估算
     - FC-6: `EvaluationService` 存在但无自动化 train/test 分割、评分脚本、ValidationSelector
     - 6 阶段 Plugin 管道: build_context → propose → generate → develop → run → summarize
     - LLM 集成: LiteLLM provider, Gemini Flash/Pro 均已验证, prompt 模板已优化

  3. Git commit:
     - Message: `docs: add paper gap analysis for RDAgent 6 FC components`
     - Files: `dev_doc/paper_gap_analysis.md`

  **Must NOT do**:
  - 不写任何实现代码或伪代码
  - 不做新的代码探索或文件读取（所有数据已在上方提供）
  - 不创建 `paper_gap_analysis.md` 以外的文件
  - 不把工程设计选择标记为 gap（例如用 SQLite 而非 in-memory graph 不一定是 gap，但缺乏跨分支通信能力是 gap）
  - 不给出时间估算
  - 不评价论文方法优劣
  - 不修改任何已有文件

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 核心工作是结构化技术写作，需要清晰组织大量信息
  - **Skills**: [`git-master`]
    - `git-master`: 处理最终 commit
  - **Skills Evaluated but Omitted**:
    - `playwright`: 无浏览器操作需求
    - `frontend-ui-ux`: 无 UI 工作

  **Parallelization**:
  - **Can Run In Parallel**: NO（单任务）
  - **Parallel Group**: Wave 1 (solo)
  - **Blocks**: F1, F2, F3
  - **Blocked By**: None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dev_doc/reverse_engineered_prd.md` — 文档风格参考，用类似的 markdown 结构
  - `dev_doc/reverse_engineered_architecture.md` — 架构描述方式参考
  - `dev_doc/adr/` — ADR 格式参考（Decision + Context + Consequences 结构）

  **Implementation References** (for "Current State" sections):
  - `llm/prompts.py` — 当前 prompt 模板，对照 FC-1 Planning 和 FC-3 Reasoning
  - `llm/adapter.py` — LLM 适配层，对照 FC-5 Coding Workflow
  - `core/loop/costeer.py` — CoSTEER 多轮演化，对照 FC-5
  - `core/loop/step_executor.py` — 6 阶段执行流，对照整体架构
  - `memory_service/service.py` — 知识库实现，对照 FC-4 Memory Context
  - `plugins/contracts.py` — 6 个 Protocol 接口，对照整体架构
  - `scenarios/data_science/plugin.py` — 数据科学场景插件，对照 FC-3 和 FC-6
  - `scenarios/synthetic_research/plugin.py` — 合成研究场景插件

  **WHY Each Reference Matters**:
  - `prompts.py` 中的 `_iteration_strategy()` 直接对应 FC-1 Planning 的简化实现
  - `costeer.py` 的 49 行是 FC-5 Coding Workflow 的最小实现
  - `service.py` 的 SQLite 存储与论文的交互核 + 嵌入系统形成最大对比
  - `contracts.py` 定义了 6 个 Protocol 接口——这是论文 2 phase / 6 FC 映射到代码的入口

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Document exists and has correct structure
    Tool: Bash
    Preconditions: Task 1 committed
    Steps:
      1. test -f dev_doc/paper_gap_analysis.md && echo "EXISTS" || echo "MISSING"
         → Assert: "EXISTS"
      2. grep -c "^## " dev_doc/paper_gap_analysis.md
         → Assert: output >= 8 (6 FC sections + Summary + Roadmap + Methodology)
      3. grep -c "^### Paper Vision" dev_doc/paper_gap_analysis.md
         → Assert: output = 6 (one per FC component)
      4. grep -c "^### Current State" dev_doc/paper_gap_analysis.md
         → Assert: output = 6
      5. grep -c "^### Gap" dev_doc/paper_gap_analysis.md
         → Assert: output = 6
    Expected Result: All structure checks pass
    Failure Indicators: Any count below expected
    Evidence: .sisyphus/evidence/task-1-structure-check.txt

  Scenario: No placeholder text and reasonable length
    Tool: Bash
    Preconditions: Document written
    Steps:
      1. grep -ciE "(TODO|TBD|FIXME|\[fill|placeholder)" dev_doc/paper_gap_analysis.md
         → Assert: output = 0
      2. wc -w < dev_doc/paper_gap_analysis.md
         → Assert: output between 2000 and 6000
    Expected Result: No placeholders, word count in range
    Failure Indicators: Placeholder found or word count out of range
    Evidence: .sisyphus/evidence/task-1-quality-check.txt

  Scenario: Git commit successful
    Tool: Bash
    Preconditions: Document written and added to git
    Steps:
      1. git log -1 --oneline
         → Assert: contains "gap analysis" or "gap_analysis"
      2. git diff HEAD~1 --name-only
         → Assert: includes "dev_doc/paper_gap_analysis.md"
      3. git status --porcelain
         → Assert: no modified tracked files (clean working tree except untracked)
    Expected Result: Commit exists with correct file
    Failure Indicators: Commit missing or wrong files
    Evidence: .sisyphus/evidence/task-1-commit-check.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-structure-check.txt — Section count verification
  - [ ] task-1-quality-check.txt — Placeholder + word count check
  - [ ] task-1-commit-check.txt — Git commit verification

  **Commit**: YES
  - Message: `docs: add paper gap analysis for RDAgent 6 FC components`
  - Files: `dev_doc/paper_gap_analysis.md`
  - Pre-commit: None (no code changes)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 3 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, check sections). For each "Must NOT Have": search document for forbidden patterns (code blocks, TODO markers, time estimates, paper judgments). Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [1/1] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Document Quality Review** — `unspecified-high`
  Read `dev_doc/paper_gap_analysis.md` end-to-end. Verify: severity rating definitions present and used consistently, all 6 FC components have Paper Vision / Current State / Gap Rating structure, Summary Table is accurate and consistent with section content, Roadmap items are actionable (what not how) and limited to 3-5 bullets each, Methodology & Caveats section exists and is substantive, no placeholder text, no code blocks, no time estimates, markdown renders correctly.
  Output: `Structure [PASS/FAIL] | Consistency [PASS/FAIL] | Completeness [6/6 FC] | Guardrails [PASS/FAIL] | VERDICT`

- [ ] F3. **Scope Fidelity Check** — `deep`
  Verify ONLY `dev_doc/paper_gap_analysis.md` was created. Verify no other files were modified (git diff). Verify commit message matches plan. Verify document stays within scope — gap analysis only, no implementation proposals beyond what roadmap allows. Check that "design choices" are not incorrectly labeled as "gaps". Verify ablation data caveats are present.
  Output: `Files [1/1 correct] | Scope [CLEAN/CREEP] | Commit [CORRECT/WRONG] | VERDICT`

---

## Commit Strategy

| Order | Message | Files | Pre-commit |
|-------|---------|-------|------------|
| 1 | `docs: add paper gap analysis for RDAgent 6 FC components` | `dev_doc/paper_gap_analysis.md` | None |

---

## Success Criteria

### Verification Commands
```bash
# Document exists
test -f dev_doc/paper_gap_analysis.md && echo "EXISTS"
# Expected: EXISTS

# Has 6 FC sections
grep -c "^### Paper Vision" dev_doc/paper_gap_analysis.md
# Expected: 6

# No placeholders
grep -ciE "(TODO|TBD|FIXME|\[fill|placeholder)" dev_doc/paper_gap_analysis.md
# Expected: 0

# Reasonable length
wc -w < dev_doc/paper_gap_analysis.md
# Expected: 2000-6000

# Commit exists
git log -1 --oneline | grep -i "gap.analysis"
# Expected: non-empty output
```

### Final Checklist
- [ ] 6 个 FC 组件完整对照 ✓
- [ ] Severity rating 有明确定义 ✓
- [ ] Methodology & Caveats section 存在 ✓
- [ ] Summary table 存在且一致 ✓
- [ ] Prioritized roadmap 存在 ✓
- [ ] 无 placeholder 文本 ✓
- [ ] 无代码块 ✓
- [ ] 文档 2000-6000 词 ✓
- [ ] Git commit 成功 ✓
- [ ] 未修改任何已有文件 ✓
