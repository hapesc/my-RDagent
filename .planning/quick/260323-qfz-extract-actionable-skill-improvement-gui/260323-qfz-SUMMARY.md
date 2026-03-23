# Quick Task 260323-qfz Summary

**Description:** Extract actionable skill-improvement guidance from Google skill patterns for RDagent
**Date:** 2026-03-23
**Status:** Completed

## Executive take

Google总结的五个模式有用，但对 RDagent 最有价值的不是“多学几个写
`SKILL.md` 的套路”，而是把 skill 重新拆成职责明确的层：

- public skill 负责触发和路由
- internal workflow 负责编排
- deterministic tool 负责裁决

如果这三层不分开，再多 pattern 也只是 prompt engineering。

## 从五个模式还能提炼出的改进建议

### 1. 不要把所有 skill 都做成 Pipeline

文章最大隐含建议是“选最小足够模式”。我们现在最容易犯的错，是把每个
skill 都写成又长又全的准流程文件。

对 RDagent 更好的分配是：

- `rd-agent`: `inversion + pipeline`
- 阶段 skill (`rd-propose` / `rd-code` / `rd-execute` / `rd-evaluate`):
  `pipeline`，但要更窄
- `rd-tool-catalog`: `tool-wrapper`
- 安装/环境相关 skill：`tool-wrapper + generator`

也就是说，pattern 是按职责选的，不是按重要性堆的。

### 2. `SKILL.md` 应该更像 adapter，少像 policy handbook

Google 的例子都遵守一个原则：`SKILL.md` 更像协调器，不是把全部知识硬塞
进去。

对 RDagent 的直接建议：

- `SKILL.md` 只写激活条件、何时使用、何时不用、execution context、输出契约
- 长规则、检查表、路由细则放进 `references/`
- 模板放进 `assets/`
- 可重复的确定性逻辑尽量下沉到工具或脚本

这样 skill 才是可维护的，不会每改一次策略就改一整篇 prompt。

### 3. 给每个 skill 加“negative routing contract”

Google 讲了 “when to use”，但对我们更重要的是 “when not to use” 和
“route where instead”。

RDagent 现在已经有部分这类文字，但还不够机械。

应该补成固定结构：

- `When to use`
- `When not to use`
- `If blocked, route to`
- `If ambiguity remains, stop and ask`
- `If state is absent, fresh-start only`

这能显著减少 agent 把 skill 边界越写越宽的趋势。

### 4. 把 Inversion 用在“收集约束”，不要用在“拖长对话”

Google 的 Inversion 模式真正有价值的是 gating，不是多问问题。

对 RDagent 的建议：

- 只在会影响流程选择的缺失信息上做 interview
- 一次只问一个高影响问题
- 如果 canonical state/tool 已能回答，禁止反问用户
- 收集完就写 artifact，不要让答案停留在对话里

也就是说，Inversion 的目标是减少猜测，不是制造 ceremony。

### 5. Pipeline 必须有硬 gate，而且要写“失败后去哪”

文章已经强调 checkpoints，但对 RDagent 还要再加一层：

- 每一步不仅要有进入条件
- 还要有失败后的标准出口

例如：

- preflight 失败 → 只能走 repair / block，不得继续 stage transition
- 当前 repo 无 canonical state → 只能 fresh start / minimum contract
- 需要 direct tool → 只能通过 installed runtime root 调用

这类 gate 如果只写“最好这样”，模型还是会跳。要写成禁止式。

### 6. Reviewer 模式不只适合 code review，也适合 skill 自审

这是文章里最容易被低估的一点。我们完全可以把 Reviewer 用在 skill 自身：

- skill 是否越权
- 是否缺少 output contract
- 是否缺少 failure handling
- 是否缺少 “when not to use”
- 是否把 deterministic decision 留在 prose 里

也就是说，给 skill 建一份 review checklist，然后用 reviewer pattern
周期性审 skill 本身，而不是只审代码。

### 7. Generator 模式可以用来统一 artifact，而不是只生成文档

Google 的例子是 report/template，但对 RDagent 更实用的是：

- plan skeleton
- continuation payload skeleton
- operator guidance skeleton
- verification artifact skeleton
- installed skill execution-context appendix

只要某个产物格式需要稳定，就该考虑 Generator，不限于“写报告”。

### 8. Tool Wrapper 在我们这里应该包“团队真相”，不只是包库知识

文章里的 Tool Wrapper 例子是 FastAPI 约定。对 RDagent，更有价值的是包装
系统真相：

- canonical state location
- installed runtime root
- direct tool invocation root
- allowed execution surfaces
- branch/stage public contracts

这比包装某个框架 API 更重要，因为这些才是 agent 最容易脑补错的东西。

### 9. Pattern 组合应该围绕“风险点”，不是围绕“任务看起来复杂”

推荐的组合方式：

- public skill: `inversion -> pipeline`
- internal workflow: `pipeline`
- verification tail: `pipeline + reviewer`
- artifact creation: `generator`
- repo/runtime conventions: `tool-wrapper`

不要因为一个 skill 很重要，就把五种模式都塞进去。那会直接把 skill 做烂。

### 10. 最值得借鉴的不是 pattern 名字，而是 progressive disclosure

Google 那套的共同点是：只在当前步骤加载当前需要的 reference/template。

对 RDagent 这是非常重要的：

- public skill 不应一上来加载所有 continuation 细节
- stage skill 不应一上来读所有 refs
- workflow 走到某步才加载该步 reference
- tool catalog 只在 downshift 时加载

这不只是省 token，更重要的是减少模型把早期信息误当成全局约束。

## 结合我们现在情况的最具体建议

### 建议 A：把现有 public skill 全部瘦身

目标结构：

- `SKILL.md`: 触发、边界、execution_context、output contract
- `workflows/*.md`: 真正的 step-by-step pipeline
- `references/*.md`: 长规则与检查表

### 建议 B：新增 skill review checklist

至少检查：

- 有没有 deterministic execution root
- 有没有 “when not to use”
- 有没有 failure path
- 有没有 output contract
- 有没有 route-to-next-step 规则
- 有没有把内部 workflow 错暴露成 public surface

### 建议 C：把 internal-only workflow 明确化

类似 GSD 的 `transition`，我们也应该有 internal-only 的：

- start vs resume arbitration
- preflight gate
- stage handoff
- branch convergence transition

这些不应该继续只活在 public skill prose 里。

### 建议 D：让 skill 直接引用 workflow，而不是复述 workflow

这是最实用的一条。凡是 `SKILL.md` 里开始出现大量 numbered steps、if/else、
gating、repair path，就说明它已经在偷做 workflow 的工作了，应该拆出去。

## 最后一个跳出框架的建议

不要把“skill 设计”理解成 prompt 写作问题，而要把它理解成控制面设计问题。

真正稳定的结构不是：

- 一个很强的 `SKILL.md`

而是：

- 一个很薄的 public skill
- 一个很硬的 internal workflow
- 一组 deterministic tools
- 一套 artifact/checklist/tests

如果这四件事齐了，五个 pattern 才会真正产生价值。
