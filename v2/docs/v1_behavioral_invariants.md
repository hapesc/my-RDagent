# V1 Behavioral Invariants (Acceptance Baseline for V2 LangGraph Refactor)

本文档基于 V1 源码行为（而非理想设计）提炼“不可回归”的行为不变量，用作 V2 迁移验收基线。

## State Transitions

### StepExecutor 六阶段主流程（`StepExecutor.execute_iteration()`）

V1 在单个方法中内联执行阶段逻辑（非私有子方法拆分）：

`PROPOSING -> EXPERIMENT_READY -> CODING -> RUNNING -> FEEDBACK -> RECORDED -> COMPLETED`

对应源码语义（`core/loop/step_executor.py`）如下：

1. **PROPOSING**
   - 入口条件：workspace 已创建，scenario context 已构造，`proposal_engine.propose(...)` 可调用。
   - 行为：调用 ProposalEngine 生成 `Proposal`，写入 `trace/proposal_{iteration}.txt`，创建 checkpoint `loop-####-propose`，追加 `hypothesis.generated` 事件。
   - 退出条件：获得有效 `proposal`。

2. **EXPERIMENT_READY**
   - 入口条件：已存在 `proposal`。
   - 行为：`experiment_generator.generate(...)` 生成 `ExperimentNode`；设置 `branch_id/parent_node_id/workspace_ref`；写入 `trace/experiment_{iteration}.json`；checkpoint `loop-####-experiment`；追加 `experiment.generated` 事件。
   - 退出条件：`experiment` 可用于编码执行。

3. **CODING**
   - 入口条件：`experiment` 就绪。
   - 行为：
     - `costeer_max_rounds > 1`：走 `CoSTEEREvolver.evolve(...)`。
     - 否则：直接 `coder.develop(...)`。
   - 输出：`CodeArtifact`；写入 `trace/coding_{iteration}.json`；checkpoint `loop-####-coding`；追加 `coding.round` 事件。
   - 退出条件：artifact 生成成功。

4. **RUNNING**
   - 入口条件：artifact 存在。
   - 行为：`runner.run(...)` 执行；`CommonUsefulnessGate.evaluate(...)` 计算 `ExecutionOutcomeContract` 与 gate signal；写入 `trace/execution_{iteration}.txt`；checkpoint `loop-####-running`；追加 `execution.finished` 事件（含 timeout 来源、process/artifact/usefulness 状态）。
   - 退出条件：得到 `execution_result` 与 `execution_outcome`。

5. **FEEDBACK**
   - 入口条件：运行结果可评估。
   - 行为：`evaluation_service.evaluate_run(...)` 产出 Score；`feedback_analyzer.summarize(...)` 产出 FeedbackRecord；反馈决策会被 usefulness gate 二次收紧（`decision/acceptable &= usefulness_eligible`）；若 reason 命中负面 marker（synthetic/placeholder/template-only/...）则强制 `acceptable=False`。
   - 输出：写入 `trace/feedback_{iteration}.txt`；checkpoint `loop-####-feedback`；追加 `feedback.generated` 事件。
   - 退出条件：feedback 完成。

6. **RECORDED**
   - 入口条件：feedback 已产出。
   - 行为：checkpoint `loop-####-record`；终态 `terminal_step_state = RECORDED if execution_outcome.process_succeeded else FAILED`；更新 experiment 的 `step_state/result_ref/feedback_ref`；可选写入 branch store；追加 `trace.recorded` 事件。
   - 退出条件：`StepExecutionResult` 返回。

### 终态与 COMPLETED 关系

- `StepExecutor` 返回的 step 终态是 `RECORDED` 或 `FAILED`，并不直接写 `COMPLETED`。
- `COMPLETED` 发生在 run 级别：`LoopEngine.run(...)` 在达到 loop 上限且未触发“真实 provider + usefulness reject”失败条件时将 `RunStatus` 标为 `COMPLETED`。

### 关键枚举不变量（`data_models.py`）

- `RunStatus`: `CREATED`, `RUNNING`, `PAUSED`, `STOPPED`, `COMPLETED`, `FAILED`
- `StepState`: `CREATED`, `PROPOSING`, `EXPERIMENT_READY`, `CODING`, `RUNNING`, `FEEDBACK`, `RECORDED`, `FAILED`, `PAUSED`, `COMPLETED`, `STOPPED`
- `BranchState`: `ACTIVE`, `PRUNED`, `MERGED`

## CoSTEER Loop

### 触发条件与入口

- 在 `StepExecutor.execute_iteration()` 中，只有当 `costeer_max_rounds > 1` 才进入 `CoSTEEREvolver.evolve(...)`；否则只执行一次 `coder.develop(...)`。
- `max_rounds` 来源：运行时配置 `runtime.config.costeer_max_rounds` 注入 StepExecutor。

### 内层循环行为（`core/loop/costeer.py`）

1. 首先做一轮初始 `coder.develop(...)` 得到 artifact。
2. 若 `max_rounds <= 1` 直接返回。
3. 否则 for `round_idx in range(1, max_rounds)`：
   - `runner.run(artifact, scenario)`
   - `feedback_analyzer.summarize(...)`（score 使用 costeer round placeholder）
   - `outcome = execution_result.resolve_outcome()`
   - 定义 `is_useful_round = process_succeeded and artifacts_verified and usefulness_eligible`
   - `feedback.acceptable` 与 `feedback.decision` 被 `is_useful_round` 收紧
   - 尝试 `_save_knowledge(...)`（失败仅 warning，不中断）
   - 若 `feedback.acceptable`，提前终止
   - 否则把反馈写入 hypothesis（结构化或文本）后再次 `coder.develop(...)`

### 终止条件

- **提前终止**：`feedback.acceptable == True`
- **上限终止**：达到 `max_rounds` 轮次

### 关于“improvement threshold”

- V1 源码中没有显式数值型 improvement threshold；提前终止条件是 `feedback.acceptable`（并被 usefulness gate 约束），属于布尔可接受性门控，而非分数阈值。

## Lifecycle Management

### RunService 生命周期状态机（`core/loop/run_service.py`）

文档约束路径：`CREATED -> RUNNING -> PAUSED -> STOPPED -> COMPLETED -> FAILED`。

V1 实际允许的转换与前置条件：

1. **create_run()**
   - 结果：新建 `RunSession(status=CREATED)` 并持久化。

2. **start_run(run_id, ...)**
   - 前置：当前状态不在 `{COMPLETED, STOPPED}`；否则抛 `RuntimeError`。
   - 行为：恢复 checkpoint（如可用）后调用 `LoopEngine.run(...)`。
   - 结果：由 LoopEngine 决定最终状态（RUNNING/COMPLETED/FAILED）。

3. **pause_run(run_id)**
   - 前置：状态必须是 `RUNNING`；否则 `RuntimeError`。
   - 结果：状态置为 `PAUSED`。

4. **resume_run(run_id, ...)**
   - 前置：状态必须在 `{PAUSED, RUNNING, FAILED}`；否则 `RuntimeError`。
   - 行为：先置 `RUNNING` 并持久化，再委托 `start_run(...)`。

5. **stop_run(run_id)**
   - 前置：仅要求 run 存在。
   - 结果：无条件置为 `STOPPED`。

6. **fork_branch(run_id, parent_node_id?)**
   - 前置：branch store 已配置；parent branch head 节点存在。
   - 结果：切换 active branch，写入 fork 所需 checkpoint 元信息，状态置 `PAUSED`。

### LoopEngine 终态判定补充

- 迭代达到上限后：
  - 默认 `COMPLETED`
  - 若 `uses_real_llm_provider=True` 且任一 iteration 命中 usefulness reject，则整 run 置 `FAILED`，并写 `last_error`。
- iteration 内异常：
  - `SkipIterationError`：归档异常后跳过当前 iteration，不直接 fail run。
  - 其他异常：调用 `_mark_iteration_failed(...)`，run 进入 `FAILED`。

## Checkpoint Semantics

### 命名规则与创建时机

- checkpoint id 规则：`loop-####-{step}`（四位 iteration + step 名）。
- 由 `StepExecutor` 在阶段末调用 `workspace_manager.create_checkpoint(...)` 创建：
  - `loop-####-propose`
  - `loop-####-experiment`
  - `loop-####-coding`
  - `loop-####-running`
  - `loop-####-feedback`
  - `loop-####-record`

### 存储语义（`FileCheckpointStore` + `WorkspaceManager`）

- `WorkspaceManager.create_checkpoint` 会 zip 当前 workspace 并写入 `FileCheckpointStore.save_checkpoint(...)`。
- 文件命名：`<checkpoint_id>.ckpt`，目录：`<checkpoint_root>/<run_id>/`。
- `FileCheckpointStore.list_checkpoints(run_id)` 返回 stem 排序列表。

### 恢复语义（`ResumeManager`）

- checkpoint 正则：`^loop-(\d+)-([a-z_]+)$`
- 步骤顺序：`propose(0) < experiment(1) < coding(2) < running(3) < feedback(4) < record(5)`
- `latest_checkpoint` 依据 `(loop_index, step_order)` 最大值。
- `next_iteration`：
  - latest step == `record` -> 下一轮 `loop_index + 1`
  - 否则在当前 `loop_index` 恢复。

### blob 归档时机

- V1 checkpoint payload（zip blob）在每个 checkpoint 创建时立即写入 `.ckpt` 文件（无延迟批量归档）。

## Exploration Strategy (DAG Scheduling)

### V1 调用顺序与职责边界

在 LoopEngine/ExplorationManager 协作下，V1 关键调用顺序可抽象为：

`select_parents() -> register_node() -> observe_feedback() -> prune_branches()`

细节说明：

- 单分支路径（`scheduler is None`）
  - `select_parents` -> `step_executor.execute_iteration`
  - `register_node`
  - 仅在当前路径未显式调用 `observe_feedback`
  - `prune_branches`

- 多分支/MCTS 路径（`scheduler is not None`）
  - scheduler 选 node 后执行 step
  - `register_node`
  - `prune_branches`
  - 之后对每个 branch `observe_feedback`（内部触发 backpropagate）

结论：V1 的“反馈观察->反向传播”是 scheduler 维度行为，service 只负责转发。

### MCTSScheduler PUCT 行为（`exploration_manager/scheduler.py`）

- `select_node`：
  - 仅在 `BranchState.ACTIVE` 节点中选择
  - 若存在 `visits==0` 的节点，优先选择未访问节点（进一步偏向 `score is None`）
  - 否则使用 PUCT：
    - `node.avg_value + c_puct * prior(node) * sqrt(total_visits) / (1 + node.visits)`
  - `prior(node)` 由节点潜力分数 softmax 归一化计算

- `observe_feedback`：
  - 用 RewardCalculator 将 `(score, decision)` 转 reward
  - 调用 `backpropagate` 递归更新叶子及祖先 `visits/total_value/avg_value`

### 关键位置不变量

- `backpropagate` 定义在 `exploration_manager/scheduler.py` 的 `MCTSScheduler`，**不在** `exploration_manager/service.py`。

### V2 替换方向说明（记录为迁移目标，不是 V1 现状）

- V2 计划以 DAG-native 调度（拓扑排序 + 优先队列）替换 V1 MCTS/PUCT；迁移验收需保证状态语义与可恢复性不退化。

## Guardrails

### REAL_PROVIDER_SAFE_PROFILE 精确值

定义于 `app/config.py`：

- `layer0_n_candidates = 1`
- `layer0_k_forward = 1`
- `costeer_max_rounds = 1`
- `sandbox_timeout_sec = 120`
- `max_retries = 1`

### 应用时机

- 在 `build_runtime()` 调用链中先执行 `load_config()`。
- `load_config()` 内 `_apply_real_provider_defaults(...)`：当 `llm_provider` 是真实 provider（例如 `litellm`）且对应字段来源仍是默认值时，自动收敛到 `REAL_PROVIDER_SAFE_PROFILE`。
- `validate_runtime_guardrails(...)` 继续对越界配置发出 warning（并校验 `layer0_k_forward <= layer0_n_candidates`）。

### 执行层守护补充

- `LoopEngine._effective_layer0_width(...)` 读取 runtime snapshot 与 safe profile，对 real-provider run 做 width 收紧。
- `LoopEngine._effective_branches_per_iteration(...)` 在 real-provider run 下强制单分支（返回 1）。

## Error Recovery

### LoopEngine 异常处理

1. `SkipIterationError`
   - 记录 warning
   - `_archive_exception(run_id, loop_index, exc)` 写入 `<artifact_root>/<run_id>/exceptions/loop-####.log`
   - 当前 iteration 记账后继续下一轮（不直接 fail run）

2. 普通 Exception（iteration 执行时）
   - `_mark_iteration_failed(...)`：run 状态置 `FAILED`，写 `last_error`，追加 `trace.recorded` 失败事件
   - `_archive_exception(...)`
   - 立即返回 loop_context

3. fatal step result（例如 `step_state=FAILED` 或 outcome 显示 process/artifact 失败）
   - `_mark_iteration_failed(...)`
   - run 置 `FAILED`

### RunService 恢复与失败处理

- checkpoint 恢复异常：
  - `start_run` 捕获异常，构造错误消息写入 `entry_input.last_error`
  - run 置 `FAILED` 并持久化
  - 重新抛出 `RuntimeError`

### RunSupervisor 崩溃恢复与控制信号

`app/run_supervisor.py` 的后台线程监督器（182 行）是 V1 关键恢复机制：

- 控制信号：`"run" / "pause" / "stop"`
- 后台 worker：`_worker_loop(...)`
  - `stop` -> 调用 `run_service.stop_run`
  - `pause`（非首次循环）-> `_mark_paused`
  - 正常执行：首次 `start_run`，后续 `resume_run`
  - run 进入 `{COMPLETED, STOPPED, FAILED}` 时退出 worker
- `finally` 块确保清理 `_workers/_controls`
- 启动时 `_recover_inflight_runs()`：将遗留 `RUNNING` 任务统一回写为 `PAUSED`，并标记 `recovery_required=True`

## LoopEngine.run() Call Sequence (Required Supplemental)

每次 iteration 的主调用链可归纳为：

1. `planner.generate_plan(planning_context)`
2. `memory_service.query_context(...)`
3. `exploration`：`select_parents`（或 scheduler `select_node`）
4. `step_executor.execute_iteration(...)`
5. 回写 graph：`register_node`、（MCTS 路径下）`observe_feedback`、`prune_branches`
6. 更新时间预算与 iteration 计数，持久化 run

## Plugin Interface Contracts (Required Supplemental)

来自 `plugins/contracts.py` 的关键协议签名：

- `Coder.develop(experiment: ExperimentNode, proposal: Proposal, scenario: ScenarioContext) -> CodeArtifact`
- `Runner.run(artifact: CodeArtifact, scenario: ScenarioContext) -> ExecutionResult`
- `FeedbackAnalyzer.summarize(experiment: ExperimentNode, result: ExecutionResult, score: Score | None = None) -> FeedbackRecord`

这些协议是场景插件可替换的边界，V2 必须保持调用语义兼容（输入输出契约和时序语义）。
