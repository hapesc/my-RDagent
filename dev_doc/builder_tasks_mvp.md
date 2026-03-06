# Builder Task List (MVP, Data Science First)

> 状态约定：`todo` / `doing` / `done` / `blocked`  
> 执行约束：严格顺序执行；未完成前置任务不得进入后续任务。

## Task-01 冻结核心数据模型

- 状态：`done`
- 指令：定义并冻结 `RunSession / ExperimentNode / WorkspaceSnapshot / FeedbackRecord / Event` 以及运行状态枚举。
- 交付物：统一模型模块、类型注释、schema 示例。
- 验收：所有核心子系统仅依赖该模型层传递数据。
- 前置：无。

## Task-02 冻结插件契约

- 状态：`done`
- 指令：定义 `ScenarioPlugin / ProposalEngine / ExperimentGenerator / Coder / Runner / FeedbackAnalyzer` 接口与注册机制。
- 交付物：插件协议定义、插件注册表、最小可加载示例插件。
- 验收：主引擎不包含场景分支 if/else 逻辑。
- 前置：Task-01。

## Task-03 冻结 CLI 合约

- 状态：`done`
- 指令：定义并实现 MVP CLI 命令接口：`run/resume/pause/stop/trace/ui/health-check`。
- 交付物：CLI 参数定义、返回码约定、帮助文档。
- 验收：命令帮助文本与错误码稳定可测试。
- 前置：Task-01。

## Task-04 冻结事件协议

- 状态：`done`
- 指令：定义事件公共字段与事件类型：`run.created` 到 `trace.recorded`。
- 交付物：事件模型、事件序列化协议、示例 payload。
- 验收：Trace 存储与 UI 使用同一事件模型。
- 前置：Task-01。

## Task-05 工程脚手架与配置层

- 状态：`done`
- 指令：建立 `core/loop/plugins/storage/execution/scenarios/app/ui/tests` 结构并接入配置加载。
- 交付物：目录结构、配置对象、环境变量映射。
- 验收：最小启动命令可读取并打印有效配置。
- 前置：Task-01~04。

## Task-06 持久化底座

- 状态：`done`
- 指令：实现 `SQLite` 元数据与事件存储、文件系统 artifact/checkpoint 存储。
- 交付物：存储抽象、SQLite 实现、文件存储实现。
- 验收：支持 run 创建/查询、事件追加读取、checkpoint CRUD。
- 前置：Task-05。

## Task-07 WorkspaceManager

- 状态：`done`
- 指令：实现工作区创建、复制、文件注入、checkpoint 打包与恢复。
- 交付物：workspace 管理模块与 API。
- 验收：任一步骤异常后可恢复到最近 checkpoint 并继续执行。
- 前置：Task-06。

## Task-08 ExecutionBackend

- 状态：`done`
- 指令：实现 Docker 优先执行后端，包含 timeout、退出码、stdout、产物收集。
- 交付物：执行后端抽象与 Docker 实现，失败语义标准化。
- 验收：超时任务被终止，失败事件写入 trace。
- 前置：Task-07。

## Task-09 LoopEngine + StepExecutor

- 状态：`done`
- 指令：实现六阶段循环与 step 级 checkpoint，支持停止条件与异常归档。
- 交付物：loop 引擎、step 执行器、状态机流转。
- 验收：单线程可完成至少一轮完整闭环并持久化。
- 前置：Task-02, Task-04, Task-06~08。

## Task-10 RunService 控制逻辑

- 状态：`done`
- 指令：实现 run 创建、状态流转、pause/resume/stop、resume manager。
- 交付物：运行控制服务与恢复入口。
- 验收：进程重启后可从最近 checkpoint 恢复。
- 前置：Task-09。

## Task-11 TraceStore 与分支基础模型

- 状态：`done`
- 指令：实现 DAG 父子关系、branch head、`fork_branch=true` 历史续跑策略。
- 交付物：branch 管理与 trace 查询能力。
- 验收：同一 run 下可存在主分支与至少一个 fork 分支。
- 前置：Task-06, Task-09。

## Task-12 LLMAdapter

- 状态：`done`
- 指令：实现结构化输出、重试、provider 抽象，并接入 proposal/coding/feedback。
- 交付物：LLM 适配层与调用封装。
- 验收：在 mock provider 下可稳定返回结构化对象。
- 前置：Task-02, Task-09。

## Task-13 Data Science 场景插件 v1

- 状态：`done`
- 指令：实现场景上下文构建、实验生成、代码演化、执行、反馈判定。
- 交付物：Data Science 插件全链路实现。
- 验收：真实输入可端到端跑通至少一轮并落盘结果。
- 前置：Task-02, Task-08~12。

## Task-14 CLI 入口打通

- 状态：`done`
- 指令：将 CLI 与 RunService、trace 查询、artifact 列表、health-check 全部串联。
- 交付物：可执行 CLI 入口与命令实现。
- 验收：`run -> trace -> pause/resume -> stop -> health-check` 可完整演示。
- 前置：Task-03, Task-10~13。

## Task-15 基础 Trace UI

- 状态：`done`
- 指令：实现时间线、step 详情、日志/指标/artifact 查看、增量刷新。
- 交付物：基础 Web UI（Streamlit）。
- 验收：可查看单次 run 的完整事件流与关键产物。
- 前置：Task-04, Task-11, Task-14。

## Task-16 可观测与安全基线

- 状态：`done`
- 指令：实现结构化日志、关键指标、异常上下文、trace 脱敏。
- 交付物：日志/指标规范与脱敏策略实现。
- 验收：异常事件具备 run_id/step 上下文，敏感字段不落 trace 明文。
- 前置：Task-09~15。

## Task-17 测试与交付文档

- 状态：`done`
- 指令：补齐单元/集成/E2E 验收，并输出运行手册与最小部署文档。
- 交付物：测试套件、验收脚本、README/运行文档。
- 验收：
  - A1 End-to-End 通过
  - A2 Resume 通过
  - A4 Sandbox 通过
  - Plugin Contract Test 通过
  - Reliability Test 通过
  - Reproducibility Test 通过
- 前置：Task-01~16。

## Task-18 V1 Backlog（本线程不执行）

- 状态：`todo`
- 指令：REST API、分支对比视图、多场景插件、按 step 模型路由。
- 交付物：V1 需求列表即可，不在 MVP 线程内实现。
- 验收：无（deferred）。
- 前置：Task-17。
