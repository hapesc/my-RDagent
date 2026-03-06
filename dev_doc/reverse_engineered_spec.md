# RD-Agent 逆向 Spec

> 版本：基于仓库当前实现逆向整理  
> 日期：2026-03-06  
> 性质：非官方产品文档；以代码、CLI、现有文档为依据，补充少量明确标注的推断

相关补充文档：

- [正式架构设计](./reverse_engineered_architecture.md)
- [面向实现的 PRD](./reverse_engineered_prd.md)

## 1. 文档目的

本文试图回答三个问题：

1. `RD-Agent` 当前到底是什么产品。
2. 它对外暴露了哪些稳定能力、输入、输出与运行约束。
3. 如果把它当作一个“可交付系统”，其核心规格应该如何描述。

本文以当前仓库实现为准，不追求覆盖论文或宣传材料中的全部愿景。

## 2. 产品定义

`RD-Agent` 是一个以 Python 为核心、面向 Linux 运行环境的“研发闭环自动化框架”。  
它把一次研发活动抽象成以下循环：

`提出假设 -> 生成实验/任务 -> 编码实现 -> 运行验证 -> 反馈总结 -> 进入下一轮`

系统当前聚焦于数据驱动研发，尤其是三类场景：

- 数据科学 / Kaggle / MLE-bench 风格任务
- 量化金融因子、模型与因子-模型协同优化
- 从 PDF 论文或报告中抽取模型并尝试实现

## 3. 产品目标

从代码实现反推，系统的主要目标是：

- 把 LLM 从“回答问题”提升为“能持续迭代代码与实验的研发代理”
- 用统一工作流承载不同场景的研发循环
- 在受控执行环境中自动运行生成代码并收集指标
- 保存全过程 trace，使任务可回放、可续跑、可并发探索
- 允许开发者通过配置和组件替换扩展新的场景与策略

## 4. 核心用户

- 直接使用 CLI 运行场景的研究者/工程师
- 准备数据集、报告、Qlib 环境的领域用户
- 需要定制提案器、编码器、运行器、反馈器的框架开发者
- 通过 UI 或服务端 API 查看执行轨迹的观察者

## 5. 核心术语与对象模型

以下概念由代码直接定义，属于当前实现的真实领域模型：

- `Scenario`
  - 提供场景背景、数据说明、运行环境说明、富文本描述。
  - 负责告诉代理“这是一个什么问题”。
- `Hypothesis`
  - 一轮研发的研究假设，包含假设本身、理由、观察摘要、知识摘要等。
- `Task`
  - 可被开发器实现的具体任务描述。
- `Experiment`
  - 假设落地后的实验载体，包含子任务、实验工作区、结果、计划、用户指令等。
- `Workspace` / `FBWorkspace`
  - 任务代码与输出文件所在的工作区；支持注入文件、执行、复制、创建/恢复 checkpoint。
- `Developer`
  - 对实验进行“开发”的抽象接口。当前 coder 和 runner 都是 `Developer`。
- `ExperimentFeedback` / `HypothesisFeedback`
  - 运行后得到的反馈，包含是否接受、理由、代码变更摘要、异常等。
- `Trace`
  - 记录实验历史与 DAG 父子关系，支持 checkpoint 选择、祖先检索、最佳实验检索。
- `LoopBase` / `RDLoop`
  - 承载完整工作流执行、并发、持久化、续跑的循环引擎。

## 6. 统一执行模型

### 6.1 标准工作流步骤

大多数场景最终会收敛到下面这套 step 序列：

1. `direct_exp_gen`
   - 基于当前 `Trace`、`Scenario` 和配置生成新实验。
2. `coding`
   - coder 负责产出或修改代码工作区。
3. `running`
   - runner 负责执行代码、收集结果、补充最终实验输出。
4. `feedback`
   - summarizer 根据结果与历史对本轮实验给出反馈。
5. `record`
   - 将实验与反馈写入 trace，并同步 DAG 父子关系。

对于基础 `RDLoop`，前置动作还可以拆成：

- `_propose`：生成假设
- `_exp_gen`：把假设转换成实验

### 6.2 循环运行特性

系统具备以下执行语义：

- 支持无限循环，或按 `step_n` / `loop_n` / 总时长停止
- 支持并发 loop，但 `feedback` 和 `record` 会被强制串行，以避免 trace 竞争
- 每个 step 完成后会将整个 loop 状态 pickle 到 `__session__`，用于断点续跑
- 支持从指定 step 恢复，也支持“回退上一轮”重新继续
- 当 step 在 subprocess 中执行且全局超时触发时，系统会主动终止残留子进程

### 6.3 代码生成与演化机制

当前实现的主要编码内核是 `CoSTEER`：

- 输入：任务描述、已有代码、先前反馈、检索知识
- 机制：`RAGEvoAgent` 多轮 evolve + evaluate
- 特点：
  - 可迭代多轮修改代码
  - 可使用知识库 / 失败案例 / 先前 trace 做 RAG
  - 会保留“可接受的最佳 fallback 版本”，而不是盲目提交最后一轮结果

## 7. 对外能力边界

### 7.1 CLI 能力

当前对外公开的主要命令为：

- `rdagent fin_factor`
- `rdagent fin_model`
- `rdagent fin_quant`
- `rdagent fin_factor_report`
- `rdagent general_model`
- `rdagent data_science`
- `rdagent grade_summary`
- `rdagent ui`
- `rdagent server_ui`
- `rdagent health_check`
- `rdagent collect_info`
- `rdagent ds_user_interact`

其中前六个是主要业务能力，后面的是运维和可视化能力。

### 7.2 配置能力

系统大量采用 `pydantic-settings` 与环境变量驱动配置，意味着以下内容可替换：

- 场景类
- 假设生成器
- 假设到实验的转换器
- coder / runner / summarizer
- 执行环境类型（docker / conda / local）
- 并发度、超时、缓存、知识库路径

这说明本项目本质上是“框架 + 若干预置场景”，而不是单一固定产品。

## 8. 场景级规格

### 8.1 Data Science Agent

#### 目标

自动完成面向数据科学任务的研发闭环，覆盖：

- 数据加载
- 特征工程
- 模型实现
- 集成
- 工作流拼装
- 必要时的整条 pipeline 演化

#### 输入要求

至少需要：

- 一个 `competition` 标识
- 对应的数据目录 `DS_LOCAL_DATA_PATH/<competition>`
- 描述文件 `description.md` 或等价 JSON

可选但强烈建议：

- `sample.py` 用于构建 debug 数据
- `eval/<competition>/valid.py`
- `eval/<competition>/grade.py`
- `sample_submission.csv`

最小自定义数据集结构可概括为：

```text
ds_data/
  <competition>/
    train/
    test/
    description.md
  source_data/
    <competition>/
```

#### 场景理解方式

系统会同时读取：

- 原始描述文件
- 已处理数据目录结构与统计信息

然后用 LLM 解析出：

- 任务类型
- 数据类型
- 数据集摘要
- 提交格式
- 评估指标名
- 指标方向（越高越好或越低越好）
- 是否需要更长超时

#### 组件链

Data Science trace 中存在明确的完成顺序：

`DataLoadSpec -> FeatureEng -> Model -> Ensemble -> Workflow`

此外代码还支持 `Pipeline` 组件，说明系统允许直接处理更粗粒度的整链任务。

#### 输出要求

当实验进入可运行状态时，工作区中应至少存在：

- `main.py`

runner 成功后应产出：

- `scores.csv`
- 可能的 `submission.csv`
- 可选的 `EDA.md`
- 若启用 MLE-bench 校验，还会生成格式检查输出

#### 特殊能力

Data Science 是当前最复杂的场景，额外支持：

- 多分支 trace / DAG 式探索
- checkpoint 选择与 SOTA 选择
- 交互器插入用户反馈
- 知识库积累
- 文档开发 `DocDev`
- notebook 转换
- MLE-bench 自动数据获取与评分

### 8.2 Finance Factor Agent

#### 目标

在 Qlib 环境中自动提出、实现、验证和筛选量化因子。

#### 典型语义

- 基于 Qlib 预置模板创建实验工作区
- 生成因子代码
- 用 Alpha158 加新因子做回测
- 根据反馈决定是否保留当前因子实现

#### 运行前提

- 需要可用的 Qlib 数据与运行环境
- 默认依赖本地 conda 环境执行因子相关代码

### 8.3 Finance Model Agent

#### 目标

在给定因子与 Qlib 模板条件下自动实现和迭代量化模型。

#### 典型语义

- 生成模型结构或超参数方案
- 在 Qlib 模板中落地模型代码
- 执行训练、验证、回测
- 依据指标决定是否替换最佳版本

### 8.4 Finance Quant Agent

#### 目标

联合优化“因子 + 模型”，而不是单独优化其中一侧。

#### 关键特征

- 假设生成阶段会先决定当前动作是 `factor` 还是 `model`
- 后续编码、运行、反馈使用对应分支的组件
- 动作选择支持 bandit / LLM / random

这说明 `fin_quant` 是一个多代理协同场景，而不是简单串联 `fin_factor + fin_model`。

### 8.5 Finance Factor Report Copilot

#### 目标

从金融研究报告 PDF 中抽取因子想法，自动实现并回测。

#### 输入

支持两种方式：

- 直接指定报告文件夹
- 提供一个 JSON 文件，列出报告 PDF 路径

### 8.6 General Model Copilot

#### 目标

读取 PDF 论文或报告，抽取模型信息，并尝试生成可执行模型代码。

#### 输入

- 单个 PDF 文件路径

#### 当前形态

该能力更像“单次任务驱动的 copilot”，不是长期自循环场景。

## 9. 运行环境规格

以下约束在当前实现中较为明确：

- 官方支持平台：Linux
- Python：`>=3.10`
- 多数场景要求 Docker 可用，且当前用户无需 `sudo` 即可运行
- Data Science 运行环境还要求目标执行环境中存在：
  - `strace`
  - `coverage`
- LLM 侧至少需要：
  - chat completion
  - embedding
  - JSON 输出能力

执行环境抽象层支持：

- Docker
- 本地 conda
- 本地环境

说明系统把“代码生成”和“代码运行”看成高风险动作，因此刻意引入环境隔离。

## 10. 可观测性与运维规格

### 日志与会话

- 每次 step 完成后都会保存 session dump
- 日志可被 UI 与服务端读取
- trace 不只是文本日志，还包含结构化对象与指标

### UI

项目自带 Streamlit UI，用于查看：

- 场景信息
- 每轮 hypothesis
- 演化代码
- 演化反馈
- 关键指标曲线

### 服务端

仓库中存在实时服务端接口文档，支持：

- 上传任务
- 暂停 / 恢复 / 停止
- 拉取尚未消费的 trace 消息

这说明项目不仅支持本地 CLI，也考虑了被前端或控制台集成。

## 11. 非功能性要求

从实现可以明确看出的非功能需求如下：

- 可续跑：session pickle + checkout 机制
- 可回放：完整 trace、日志、UI
- 可并发：按 step 控制 semaphore
- 可隔离：环境抽象与超时控制
- 可配置：大量组件和策略通过环境变量切换
- 可演化：编码过程不是一次性生成，而是多轮演化
- 可恢复：工作区支持 checkpoint 与 fallback

工程质量方面，仓库本身也体现出以下约束：

- `ruff`
- `mypy`
- `pytest`
- 覆盖率阈值 `80%`

## 12. 扩展规格

如果把项目看作框架，新增一个场景至少需要补齐：

1. `Scenario`
2. `HypothesisGen`
3. `Hypothesis2Experiment`
4. `Developer`（coder / runner）
5. `Experiment2Feedback`
6. 相应配置类与环境变量前缀
7. 必要时的工作区模板、prompt、评估器、知识库

也就是说，项目的真正扩展单元不是“prompt 文件”，而是“一整套场景插件”。

## 13. 逆向结论

综合代码与文档，`RD-Agent` 的最准确定位不是“单个 AI Agent”，而是：

> 一个面向研发闭环自动化的多场景代理框架，核心能力是把研究假设、代码实现、运行验证、反馈学习和轨迹持久化组织成可续跑、可并发、可扩展的循环系统。

对外最成熟的落地场景是：

- Data Science / Kaggle / MLE-bench
- Qlib 量化研发
- 报告/论文到代码的半自动实现

## 14. 尚不确定或存在漂移的地方

以下内容在代码和文档间存在一定漂移，后续如要形成正式 spec，建议单独澄清：

- README 中 “Kaggle Agent” 与当前 `data_science` 场景的关系边界
- `collect_info` 等工具命令的正式产品定位
- 实时服务端 API 是否仍与 `rdagent/log/server/README.md` 完全一致
- 部分场景文档使用“research copilot”描述，但代码中是否继续保持长期维护尚不完全明确
- Data Science 中 `spec_enabled` 配置存在，但仓库内面向该场景的显式 spec 产物并不统一

## 15. 主要证据来源

本 spec 主要依据以下实现与文档逆向整理：

- `README.md`
- `pyproject.toml`
- `rdagent/app/cli.py`
- `rdagent/utils/workflow/loop.py`
- `rdagent/components/workflow/rd_loop.py`
- `rdagent/core/scenario.py`
- `rdagent/core/proposal.py`
- `rdagent/core/experiment.py`
- `rdagent/components/coder/CoSTEER/*`
- `rdagent/app/data_science/conf.py`
- `rdagent/scenarios/data_science/*`
- `rdagent/app/qlib_rd_loop/*`
- `rdagent/scenarios/qlib/*`
- `rdagent/app/general_model/general_model.py`
- `docs/scens/*.rst`
- `docs/installation_and_configuration.rst`
- `docs/ui.rst`
- `rdagent/log/server/README.md`
