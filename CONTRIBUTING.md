# 贡献指南

## 欢迎

感谢您对本项目的兴趣！我们非常欢迎各种形式的贡献，包括 bug 报告、功能建议、文档改进和代码提交。无论您是新手还是经验丰富的开发者，都可以找到适合您的贡献方式。

---

## 开发环境设置

### 1. 安装 uv

uv 是一个快速的 Python 包管理工具。请使用以下命令安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆仓库

```bash
git clone https://github.com/hapesc/my-RDagent.git
cd my-RDagent
```

### 3. 创建虚拟环境

使用 uv 创建虚拟环境：

```bash
uv venv
```

### 4. 安装依赖

安装项目的所有依赖，包括开发依赖：

```bash
uv pip install -e ".[all]"
```

### 5. 安装 pre-commit 钩子

为了确保代码质量，安装 pre-commit 钩子：

```bash
pre-commit install
```

现在您的开发环境已准备就绪！

---

## 开发工作流

我们采用标准的 Git 工作流：

### 1. Fork 仓库

在 GitHub 上 fork 本仓库到您的账户。

### 2. 创建特性分支

从 `main` 分支创建一个新的分支，分支名称应该具有描述性：

```bash
git checkout -b feat/add-new-feature
# 或
git checkout -b fix/resolve-bug-issue
```

### 3. 编写代码

在您的分支上进行修改和开发。遵循下面的代码风格指南。

### 4. 运行测试

在提交前，确保所有测试都通过（详见**测试**部分）。

### 5. 提交 Commit

遵循 Conventional Commits 规范提交您的更改。

### 6. Push 并创建 Pull Request

将您的分支 push 到 fork 仓库，然后创建 Pull Request 到主仓库。

---

## 代码风格

本项目使用 **Ruff** 进行代码风格检查和自动格式化。

### 代码检查

运行以下命令检查代码是否符合风格规范：

```bash
ruff check .
```

### 自动格式化

运行以下命令自动格式化代码：

```bash
ruff format .
```

### 配置

Ruff 的配置位于 `pyproject.toml` 文件中。请不要修改这些配置，以保持项目代码风格的一致性。

---

## 测试

编写测试是确保代码质量的重要部分。所有新功能都必须包含相应的测试。

### 运行测试

执行所有测试：

```bash
python -m pytest tests -q
```

### 测试覆盖率

生成并查看测试覆盖率报告：

```bash
pytest --cov=. --cov-report=term-missing
```

这将显示哪些代码行没有被测试覆盖。

### 编写测试

- 在 `tests/` 目录中创建测试文件
- 使用描述性的测试函数名称
- 确保新功能的测试覆盖率不低于现有标准

---

## Commit 规范

我们采用 **Conventional Commits** 规范来编写 commit 消息，这有助于自动生成 changelog 和版本管理。

### Commit 消息格式

```
<type>: <subject>

<body>
```

### 类型说明

- **feat:** 新功能的添加
- **fix:** bug 修复
- **docs:** 文档相关的修改（如 README、CHANGELOG）
- **chore:** 维护工作，不涉及功能或测试（如依赖更新、build 脚本）
- **build:** 影响构建系统或依赖的修改

### 例子

```
feat: add user authentication module

Implement JWT-based authentication for API endpoints.
- Add login endpoint
- Add token validation middleware
- Add user model

Closes #123
```

```
fix: resolve session timeout issue
```

---

## Pull Request 要求

在提交 PR 时，请确保满足以下要求：

### 1. 描述您的更改

在 PR 描述中清楚地说明：
- 您做了什么修改
- 为什么要做这些修改
- 这会如何影响现有功能

### 2. 通过所有 CI 检查

所有 CI（持续集成）检查必须通过，包括：
- 代码风格检查（ruff）
- 单元测试
- 代码覆盖率检查

### 3. 关联相关 Issue

如果您的 PR 解决了某个 Issue，请在 PR 描述中使用以下格式链接：

```
Closes #<issue-number>
```

或

```
Fixes #<issue-number>
Related to #<issue-number>
```

### 4. 保持分支更新

确保您的分支是最新的，与主分支没有冲突。

---

## Issue 报告

遇到问题？请在 GitHub 上创建 Issue。

我们提供了 Issue 模板来帮助您组织信息：

- **Bug 报告模板** - 用于报告发现的问题
- **功能请求模板** - 用于建议新功能
- **其他问题模板** - 用于其他类型的讨论

使用相应的模板可以帮助维护者更快地理解和处理您的 Issue。

---

## 行为准则

### 我们的承诺

为了促进一个开放和包容的社区，我们承诺：

- 尊重所有贡献者，无论其背景、身份或观点
- 欢迎建设性的反馈和不同的意见
- 致力于创建一个安全、友好和专业的环境

### 预期行为

我们期望所有参与者：

- 使用尊重和包容的语言
- 接受他人的批评和建议
- 关注社区的最佳利益
- 在与他人互动时表现出同理心

### 不可接受的行为

以下行为是不可接受的：

- 骚扰、歧视或人身攻击
- 性骚扰或任何形式的骚扰行为
- 发布他人的私人信息
- 其他不专业或不尊重的行为

### 举报问题

如果您目睹或经历了不可接受的行为，请通过项目的 maintainer 邮件报告。所有报告将被认真对待和调查。

---

## 常见问题

### Q: 我应该从哪里开始？

A: 查看 `README.md` 了解项目概况，然后阅读本指南的开发环境设置部分。

### Q: 我可以改进文档吗？

A: 当然可以！文档改进总是欢迎的。请使用 `docs:` 前缀创建 PR。

### Q: 我应该在哪里提问？

A: 您可以创建一个 GitHub Issue（标记为 question）或在 PR 中讨论。

---

## 感谢

感谢您的贡献！无论贡献的大小，您都帮助我们改进了这个项目。

如有任何问题或建议，欢迎联系项目维护者。
