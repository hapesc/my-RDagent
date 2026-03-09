# FC-4 Memory Context - 完整实现索引

**Date**: 2026-03-09  
**Status**: ✅ Complete Implementation  
**Test Coverage**: 584 tests passing  
**Paper**: R&D-Agent (arXiv 2404.11276)

---

## 📚 文档导航

### 深度分析文档
- **[FC4_MEMORY_CONTEXT_ANALYSIS.md](./FC4_MEMORY_CONTEXT_ANALYSIS.md)** (901行)
  - 完整的实现深度分析
  - Embedding-based retrieval详解
  - Interaction kernel公式与实现对比
  - Algorithm 2自适应选择详解
  - 数据结构与SQLite设计
  - 584测试覆盖分析
  - 论文vs代码完整对比表

### 论文相关文档
- **[dev_doc/paper_gap_analysis.md](./dev_doc/paper_gap_analysis.md)** (第192-250行)
  - FC-4 gap analysis部分
  - 论文vision vs current state对比
  - 测试计数和状态

---

## 🔍 核心代码模块

### 1. interaction_kernel.py (155行)
**位置**: `memory_service/interaction_kernel.py`

#### 数据结构
```python
@dataclass
class HypothesisRecord:
    text: str              # 假设内容
    score: float           # [0, 1]评分
    timestamp: float       # Unix秒
    branch_id: str         # 源分支
```

#### 核心类与函数

**TFIDFVectorizer** (line 16-86)
- `fit_transform(documents: List[str]) -> List[Dict[str, float]]`
  - 纯Python TF-IDF实现
  - 稀疏向量表示
  - 无外部依赖

- `transform(document: str) -> Dict[str, float]`
  - 单文档变换
  - 使用fitted vocabulary

**cosine_similarity** (line 89-111)
```python
def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float
```
- 稀疏向量余弦相似度
- 范围: [0, 1]
- 6个单元测试

**score_delta** (line 114-120)
```python
def score_delta(score_a: float, score_b: float) -> float
```
- 性能对齐分量
- 公式: 1.0 - |score_a - score_b|
- 2个单元测试

**temporal_decay** (line 123-134)
```python
def temporal_decay(timestamp_a: float, timestamp_b: float, half_life: float = 3600.0) -> float
```
- 指数衰减: 0.5^(Δt / half_life)
- 默认半衰期: 3600秒 (1小时)
- 4个单元测试

**InteractionKernel** (line 137-155)
```python
class InteractionKernel:
    def __init__(self, alpha: float = 0.4, beta: float = 0.3, gamma: float = 0.3)
    def compute(self, h_a: HypothesisRecord, h_b: HypothesisRecord) -> float
```
- K(h_i, h_j) = α·cosine + β·score_delta + γ·temporal_decay
- 返回值: [0, 1]
- 5个单元测试

---

### 2. hypothesis_selector.py (121行)
**位置**: `memory_service/hypothesis_selector.py`

#### HypothesisSelector类

**__init__** (line 12-18)
```python
def __init__(self, interaction_kernel: InteractionKernel, llm_adapter=None)
```
- interaction_kernel: 必需，计算相关性
- llm_adapter: 可选，用于modify/generate

**select_hypothesis** (line 20-23)
```python
def select_hypothesis(self, candidates: List[HypothesisRecord], context: str) -> HypothesisRecord
```
- 返回最高评分候选
- 用途: 晚期阶段 (progress ≥ 0.66)

**modify_hypothesis** (line 25-49)
```python
def modify_hypothesis(self, source: HypothesisRecord, context_items: List[str], 
                     task_summary: str, scenario_name: str) -> HypothesisModification
```
- 调用LLM适应假设到上下文
- 无LLM时: 返回源假设不修改
- 用途: 中期阶段 (0.33 ≤ progress < 0.66)

**generate_hypothesis** (line 51-74)
```python
def generate_hypothesis(self, context_items: List[str], task_summary: str, 
                       scenario_name: str) -> HypothesisModification
```
- 从上下文创建新假设
- 无LLM时: 返回空结果
- 用途: 早期阶段 (progress < 0.33)

**adaptive_select** (line 76-111) ⭐ **Algorithm 2**
```python
def adaptive_select(self, candidates: List[HypothesisRecord], iteration: int, 
                   max_iterations: int, context_items: List[str], 
                   task_summary: str, scenario_name: str) -> HypothesisModification
```
- 进度相关的三阶段选择
- progress < 0.33 → generate
- progress ∈ [0.33, 0.66) → modify best
- progress ≥ 0.66 → select best

#### 辅助函数

**rank_by_kernel** (line 114-121)
```python
def rank_by_kernel(target: HypothesisRecord, candidates: List[HypothesisRecord],
                  kernel: InteractionKernel) -> List[Tuple[HypothesisRecord, float]]
```
- 按kernel相关性排序候选
- 返回 (hypothesis, kernel_score) 元组列表

---

### 3. service.py (227行)
**位置**: `memory_service/service.py`

#### MemoryServiceConfig (line 20-27)
```python
@dataclass
class MemoryServiceConfig:
    max_context_items: int = 10
    index_backend: str = "in_memory"
    db_path: str = ":memory:"
    enable_hypothesis_storage: bool = False
```
- `enable_hypothesis_storage`: 启用假设存储 (默认False，向后兼容)

#### MemoryService类

**__init__** (line 33-51)
- 初始化SQLite数据库
- 可选: 接收hypothesis_selector和interaction_kernel

**_initialize** (line 71-96)
- 创建两个表:
  - `failure_cases`: 原始内存项
  - `hypotheses`: 假设存储 (仅当enable_hypothesis_storage=True)

**write_hypothesis** (line 181-194)
```python
def write_hypothesis(self, text: str, score: float, branch_id: str,
                    metadata: Optional[Dict[str, str]] = None) -> None
```
- 存储新假设
- timestamp自动设置为当前时间

**query_hypotheses** (line 196-213)
```python
def query_hypotheses(self, branch_id: Optional[str] = None, limit: int = 10) -> List[HypothesisRecord]
```
- 查询假设（可选branch过滤）
- 排序: id DESC (最新优先)
- 返回: HypothesisRecord列表

**get_cross_branch_hypotheses** (line 215-227) ⭐ **跨分支查询**
```python
def get_cross_branch_hypotheses(self, exclude_branch: str, limit: int = 10) -> List[HypothesisRecord]
```
- 查询其他分支的假设
- WHERE branch_id != exclude_branch
- 排序: score DESC (最高评分优先)
- **关键特点**: 返回OTHER分支的最佳假设

**query_context** (line 119-157)
```python
def query_context(self, query: Dict[str, str]) -> ContextPack
```
- 返回ContextPack，包含:
  - items: 原始memory items
  - highlights: 查询关键词
  - scored_items: [(假设文本, 评分), ...] (仅当启用假设存储)

**get_memory_stats** (line 159-179)
```python
def get_memory_stats(self) -> Dict[str, int]
```
- 返回统计: {"items": count, "hypothesis_count": count}

---

## 🧪 测试模块

### test_fc4_interaction_kernel.py (211行)

| 测试类 | 测试数 | 覆盖 |
|--------|--------|------|
| TestTFIDFVectorizer | 6 | tokenization, fit/transform, edge cases |
| TestCosineSimilarity | 5 | identical, orthogonal, empty, range |
| TestScoreDelta | 2 | equal, different scores |
| TestTemporalDecay | 4 | same time, half-life, multiple decays |
| TestInteractionKernel | 5 | K formula, components, range |

### test_fc4_hypothesis_selector.py (235行)

| 测试方法 | 目的 |
|---------|------|
| test_select_hypothesis_picks_highest_score | select操作 |
| test_modify_hypothesis_without_llm | graceful degradation |
| test_adaptive_select_early_progress_generates | Algorithm 2早期 |
| test_adaptive_select_mid_progress_modifies | Algorithm 2中期 |
| test_adaptive_select_late_progress_selects | Algorithm 2晚期 |
| test_rank_by_kernel_returns_sorted_by_score | 排序助手 |

### test_fc4_memory.py (138行)

| 测试方法 | 目的 |
|---------|------|
| test_write_hypothesis_stores_correctly | 存储 |
| test_query_hypotheses_returns_stored | 单分支查询 |
| test_query_hypotheses_by_branch | 分支过滤 |
| test_get_cross_branch_hypotheses_excludes_current | 跨分支 ⭐ |
| test_query_context_backward_compatible | 向后兼容 |
| test_query_context_with_hypotheses_populates_scored_items | 集成 |
| test_get_memory_stats_includes_hypothesis_count | 统计 |

---

## 📊 数据流

### 写入流程
```
假设 → write_hypothesis() → SQLite hypotheses table
              ↓
           timestamp自动设置为now()
           metadata→JSON序列化
           score范围[0,1]
```

### 查询流程

**分支内查询**
```
query_hypotheses(branch_id="branch-0") 
    ↓
SELECT * WHERE branch_id = "branch-0" 
    ORDER BY id DESC LIMIT 10
    ↓
[HypothesisRecord, ...]  (newest first)
```

**跨分支查询** (Algorithm 2的候选源)
```
get_cross_branch_hypotheses(exclude_branch="branch-0")
    ↓
SELECT * WHERE branch_id != "branch-0"
    ORDER BY score DESC LIMIT 10
    ↓
[HypothesisRecord, ...]  (best scored first)
    ↓
rank_by_kernel(target, candidates) 
    ↓
[(HypothesisRecord, kernel_score), ...]
```

### ContextPack集成
```
query_context({"error_type": "timeout"})
    ↓
    ├─ memory items从failure_cases
    ├─ hypotheses从hypotheses表
    └─ scored_items = [(h.text, h.score), ...]
    ↓
ContextPack(items=[...], scored_items=[...])
```

---

## 🎯 使用示例

### 完整初始化
```python
from memory_service.interaction_kernel import InteractionKernel
from memory_service.hypothesis_selector import HypothesisSelector
from memory_service.service import MemoryService, MemoryServiceConfig
from llm.adapter import LLMAdapter

# 1. 创建交互核
kernel = InteractionKernel(alpha=0.4, beta=0.3, gamma=0.3)

# 2. 创建假设选择器（with LLM）
llm = LLMAdapter(...)  # 可选
selector = HypothesisSelector(kernel, llm_adapter=llm)

# 3. 创建内存服务
config = MemoryServiceConfig(
    enable_hypothesis_storage=True,
    max_context_items=10
)
memory = MemoryService(
    config,
    hypothesis_selector=selector,
    interaction_kernel=kernel
)
```

### 存储假设
```python
memory.write_hypothesis(
    text="use random forest with 100 trees",
    score=0.85,
    branch_id="branch-0",
    metadata={"source": "proposal", "iteration": 5}
)
```

### 查询跨分支假设
```python
# 获取其他分支的最佳假设
candidates = memory.get_cross_branch_hypotheses(
    exclude_branch="branch-0",
    limit=5
)

# 使用Algorithm 2自适应选择
result = selector.adaptive_select(
    candidates=candidates,
    iteration=15,
    max_iterations=50,
    context_items=["accuracy too low"],
    task_summary="iris classification",
    scenario_name="data_science"
)

# result包含:
# - modified_hypothesis: 选中/修改后的假设文本
# - modification_type: "select" | "modify" | "generate"
# - reasoning: 为什么选择这个假设
```

### 获取上下文（用于ProposalEngine）
```python
context = memory.query_context({"error_type": "accuracy"})
# context.items: ["error: low accuracy", ...]
# context.scored_items: [("random forest", 0.85), ("xgboost", 0.72)]
```

---

## 📈 关键指标

| 指标 | 值 | 说明 |
|------|-----|------|
| 总测试数 | 584 | 全部通过 ✓ |
| TF-IDF向量 | Sparse Dict | 内存高效 |
| Kernel公式 | K∈[0,1] | 加权组合 |
| 时间衰减 | 指数(half-life=3600s) | 自然衰减 |
| Algorithm 2 | 三阶段 | progress-aware |
| 跨分支隔离 | WHERE branch_id != | 完全隔离 |
| 向后兼容 | enable_hypothesis_storage=False | Zero overhead |

---

## 🔗 论文映射

| 论文位置 | 内容 | 代码位置 |
|---------|------|--------|
| Section 3.4 | FC-4概念 | memory_service/ |
| Algorithm 2 | 自适应选择 | hypothesis_selector.py:76 |
| Appendix D | 交互核公式 | interaction_kernel.py:137 |
| Eq. 7 | K = α·a + β·b + γ·c | interaction_kernel.py:150 |
| Table 3 | FC-4 impact = -9% | paper_gap_analysis.md |

---

## ✅ 验证清单

- [x] TF-IDF向量化完整实现
- [x] 余弦相似度计算
- [x] 性能对齐分量
- [x] 时间衰减指数函数
- [x] 交互核加权组合
- [x] Algorithm 2三阶段选择
- [x] SQLite假设存储
- [x] 跨分支查询隔离
- [x] ContextPack集成
- [x] 584单元测试
- [x] 优雅降级（无LLM、无候选、无假设）
- [x] 向后兼容（disable时零开销）

---

**Analysis Date**: 2026-03-09  
**Implementation Status**: Production Ready ✅  
**Last Test Run**: All 584 tests passing ✓
