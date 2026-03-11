# Agent Loop Self-Correction

## Overview

当前 `main` 分支已经具备一部分 self-correction 基础设施，但还没有把“失败后跳过当前 iteration 并继续下一轮”完整接入主执行链路。

更准确地说，当前实现属于：

- 已有可复用的纠错元件
- 已有失败可见性与结构化反馈字段
- 但主 loop 仍以 fail-fast 为主

## What Is Actually Implemented

### 1. Exception hierarchy exists

`core/correction/exceptions.py` 定义了：

- `SkipIterationError`
- `CoderError`
- `RunnerError`

这些类型已经落地，但当前 `LoopEngine` 主流程还没有专门按 `SkipIterationError` 做 continue-routing。

### 2. Shared feedback enricher exists

`core/correction/feedback_enricher.py` 提供了 `enrich_feedback_context()`，能够读取：

- `_costeer_feedback`
- `_costeer_feedback_execution`
- `_costeer_feedback_code`
- `_costeer_feedback_return`
- `_code_source`

当前状态是：

- 工具函数已存在
- 场景 coder 目前还没有统一切到它
- 因此它更像是后续接线点，而不是已完全生效的主路径

### 3. CoSTEER writes structured feedback fields

`core/loop/costeer.py` 在多轮 coding 失败后会把结构化反馈写回 `experiment.hypothesis`：

- `_costeer_feedback`
- `_costeer_feedback_execution`
- `_costeer_feedback_code`
- `_costeer_feedback_return`
- `_costeer_round`

同时，在 debug mode 下还会记录 `estimated_full_time_sec`。

### 4. Code-source visibility is implemented

当前各场景已经会把代码来源写进 hypothesis / trace：

- `data_science`: `llm` / `template` / `failed`
- `quant`: `llm` / `failed`
- `synthetic_research`: `llm`

这部分能力已经真实接入场景代码，而不是设计草图。

## What Is Not Fully Wired Yet

### 1. Loop-level skip routing

设计目标里的这条能力尚未完成：

- coder 或 runner 抛出 `SkipIterationError` 子类
- loop engine 归档失败
- 标记该 iteration 失败
- 然后继续后续 iteration

当前 `core/loop/engine.py` 仍主要使用通用 `except Exception` 分支，并在失败时把 run 标记为 `FAILED` 后返回。

### 2. Shared enricher integration

虽然 `enrich_feedback_context()` 已经存在，但当前场景实现还没有统一改为使用它。比如：

- `DataScienceCoder` 仍保留自己的 `_enrich_proposal_with_feedback()`
- quant / synthetic_research 也没有统一切换到共享 enricher

### 3. Failure knowledge persistence

当前 `CoSTEER._save_knowledge()` 只在 `feedback.acceptable` 时写 memory，并不是“失败也无条件入库”。

因此“失败经验自动写入知识库”仍然是设计方向，不是当前主分支事实。

### 4. Degradation-aware feedback decisions

`_code_source` 已经写入 hypothesis，但像 `QuantFeedbackAnalyzer` 这样的反馈分析器目前并没有系统性地基于 `_code_source == "failed"` 做降级判定。

## Practical Interpretation

如果你现在阅读源码，应把 self-correction 理解为：

- 已有结构化反馈采集
- 已有代码来源可见性
- 已有异常分类草图
- 但 loop-level recovery 仍未完全闭环

也就是说，仓库已经具备“往自我纠错演进”的关键积木，但主分支当前还不是一个完整的 skip-and-heal runtime。

## Next Integration Steps

要把这套能力真正闭环，最直接的后续工作是：

1. 在场景 coder / runner 中改为抛出 `CoderError` 和 `RunnerError`
2. 在 `LoopEngine` 中为 `SkipIterationError` 建立单独分支
3. 把 `enrich_feedback_context()` 接到各场景 coder 的 prompt enrichment
4. 决定失败知识是否进入 `MemoryService`
5. 把 `_code_source` 纳入反馈分析和分支选择逻辑
