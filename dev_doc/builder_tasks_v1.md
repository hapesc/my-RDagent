# Builder Task List (PRD V1 Completion)

> 状态约定：`todo` / `doing` / `done` / `blocked`  
> 执行约束：严格顺序执行；未完成前置任务不得进入后续任务。  
> 基线说明：`Task-01 ~ Task-17` 已在 MVP 阶段完成，本文件从 `Task-18` 开始补齐到 `PRD V1 Definition of Done`。

## Task-18 冻结 V1 服务契约与配置扩展

- 状态：`done`
- 指令：定义并冻结 V1 控制面 DTO、错误码、分页查询契约、场景能力清单与 step override 模型。
- 交付物：
  - `RunCreateRequest`
  - `RunSummaryResponse`
  - `RunControlResponse`
  - `RunEventPageResponse`
  - `ArtifactListResponse`
  - `BranchListResponse`
  - `ScenarioManifest`
  - `StepOverrideConfig`
  - 配套错误码与 OpenAPI 结构草案
- 验收：
  - `RunSession` 持久化 `config_snapshot`
  - `step_overrides` 支持 `proposal/coding/running/feedback`
  - CLI / UI / API 共用同一套场景能力描述
  - 非法参数返回结构化错误
- 前置：`Task-17`

## Task-19 正式化第二场景插件 `synthetic_research`

- 状态：`done`
- 指令：将当前最小插件从“示例/测试夹具”提升为正式支持场景 `synthetic_research`。
- 交付物：
  - 正式场景 bundle 与 manifest
  - 注册表与启动配置接入
  - CLI / API 场景列表暴露
  - 最小运行说明文档
- 验收：
  - `data_science` 与 `synthetic_research` 都能通过同一 loop engine 运行
  - 核心引擎不存在场景条件分支
  - `A5 Plugin Swap` 对第二场景具备正式产品入口，而不是仅测试内部调用
- 前置：`Task-18`

## Task-20 打通 per-step 配置链路

- 状态：`done`
- 指令：实现“场景默认值 + run 级覆盖”的 per-step 模型与 timeout 配置链路。
- 交付物：
  - 配置层扩展
  - `LLMAdapter` 对 `proposal/coding/feedback` 模型配置的消费
  - `ExecutionBackend` 对 `running.timeout_sec` 的消费
  - 生效配置快照落盘与查询接口
- 验收：
  - 未传覆盖时稳定回退到场景默认值
  - 传入覆盖后 proposal/coding/feedback/running 均按配置执行
  - trace / API / UI 可审计本次 run 的最终生效配置
- 前置：`Task-18`

## Task-21 实现 FastAPI 控制面与 `RunSupervisor`

- 状态：`done`
- 指令：新增单机、单进程的 FastAPI 控制面，并以 `RunSupervisor` 管理后台执行与控制信号。
- 交付物：
  - FastAPI 应用入口
  - `RunSupervisor`
  - 控制面端点：
    - `POST /runs`
    - `GET /runs/{run_id}`
    - `POST /runs/{run_id}/pause`
    - `POST /runs/{run_id}/resume`
    - `POST /runs/{run_id}/stop`
    - `GET /runs/{run_id}/events`
    - `GET /runs/{run_id}/artifacts`
    - `GET /runs/{run_id}/branches`
    - `GET /scenarios`
    - `GET /health`
- 验收：
  - `POST /runs` 立即返回，loop 在后台继续执行
  - `pause/resume/stop` 可驱动后台任务生命周期
  - 服务重启后进行中的 run 不自动续跑，而是进入可恢复状态并支持显式 `resume`
  - `health` 同时检查 SQLite、artifact root、execution backend、LLM adapter
- 前置：`Task-18`, `Task-20`

## Task-22 补齐 branch/artifact 服务与 branch-aware UI

- 状态：`done`
- 指令：补齐分支查询、artifact manifest 与 branch-aware Streamlit UI，且保持未来自定义前端可复用同一 DTO。
- 交付物：
  - branch 列表与 branch head 查询服务
  - artifact manifest 服务
  - Streamlit UI 增强：
    - run overview
    - branch selector
    - branch head table
    - artifact browser
    - control actions
    - 基础比较摘要
- 验收：
  - 主分支与 fork 分支都能在 UI 中直观看到
  - UI 通过 API 形状一致的 DTO 取数
  - 事件采用 `cursor + limit` 轮询刷新，不引入 SSE/WebSocket
  - artifact 可按 run / branch 查看
- 前置：`Task-18`, `Task-21`

## Task-23 V1 验收与硬化

- 状态：`done`
- 指令：补齐 V1 验收矩阵、服务化运行文档、性能 smoke 与安全回归，形成可交付 PRD V1 的收口版本。
- 交付物：
  - `A3 Branch` 验收
  - `A5 Plugin Swap` 验收
  - API contract tests
  - UI branch-aware tests
  - per-step override 审计测试
  - 服务启动 / 运行 / 运维文档
- 验收：
  - 远程客户端无需直接进程访问即可创建、控制、监控 run
  - 第二场景以正式产品能力暴露
  - branch-aware trace view 可用
  - per-step model / timeout config 生效且可审计
  - 本地 smoke 满足 metadata < 2s、UI 首屏加载 < 5s 的基线
- 前置：`Task-18 ~ Task-22`

## V1 结束判定

- 满足 `PRD V1 Definition of Done`
- `A3 Branch` 通过
- `A5 Plugin Swap` 通过
- 远程 API 可完整执行 create / inspect / pause / resume / stop / events / artifacts / health
- Streamlit UI 具备 branch-aware 能力

## 明确延期（本线程不执行）

- `FR-012 Human Instructions`
- `FR-016 Knowledge Base`
- 真实量化 / 论文场景
- 多 worker 调度
- 审批流、分支合并、产物对比仪表盘
