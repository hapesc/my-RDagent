# Data Science Plugin v1 (Task-13)

实现目录：`scenarios/data_science/`

- `DataScienceScenarioPlugin`: 构建场景上下文（含输入数据）
- `DataScienceProposalEngine`: LLM 结构化 proposal
- `DataScienceExperimentGenerator`: 生成实验节点与工作区引用
- `DataScienceCoder`: 生成可执行 `pipeline.py`
- `DataScienceRunner`: 使用 `DockerExecutionBackend` 执行（docker 优先，自动回退）
- `DataScienceFeedbackAnalyzer`: 结构化反馈判定

默认注册：`plugins.build_default_registry()` 中 `data_science` 指向该 v1 插件。

## End-to-End Acceptance

`tests/test_task_13_data_science_plugin_v1.py` 使用真实 CSV 输入完成一轮闭环，校验：

- run 完成状态持久化
- trace 事件落库
- checkpoint 落盘
- `metrics.json` 产物落盘
