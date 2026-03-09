# OSS Maturity: 开源项目基础设施完善

## TL;DR

> **Quick Summary**: 为 my-RDagent 补齐成熟开源项目所需的全部基础设施——CI/CD、代码质量工具链、社区文档、安全策略、结构化日志——让项目从"能跑"变成"可协作、可维护、可信赖"。
> 
> **Deliverables**:
> - GitHub Actions CI 流水线（lint + test + coverage + build验证）
> - Ruff 配置 + pre-commit hooks
> - MIT LICENSE 文件
> - CONTRIBUTING.md + SECURITY.md
> - GitHub Issue/PR 模板
> - 增强版 .gitignore
> - 结构化日志配置（JSON格式）
> - Dependabot 自动依赖更新
> - pyproject.toml 更新（Ruff + dev 依赖组）
> 
> **Estimated Effort**: Medium (10-12 tasks, mostly config/doc files)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (pyproject.toml update) → Wave 2 (CI uses Ruff config) → Wave 3 (final verification)

---

## Context

### Original Request
用户希望将 my-RDagent 打造成成熟的开源项目，第一阶段（包管理、Docker、开箱即用）已完成。第二阶段需要补齐所有部署配置优化项。

### Interview Summary
**Key Discussions**:
- **License**: MIT — 最宽松，社区友好
- **发布渠道**: 不发布到 PyPI/DockerHub/GHCR — CI 仅做验证，不做 publish
- **K8s**: 暂不需要 — Docker Compose 已够用
- **Lint/Format**: Ruff — 替代 Black + Flake8 + isort 的全能工具
- **测试**: 已有564个测试 + 需要覆盖率报告
- **社区文档**: 标准级别 — CONTRIBUTING.md + SECURITY.md + Issue/PR模板
- **监控**: 结构化日志（JSON格式）— 项目已有 observability/ 模块基础

**Research Findings**:
- `observability/service.py` 已有 JSON 结构化日志输出 + metric/trace emission
- `observability/redaction.py` 已有敏感字段脱敏
- `.gitignore` 仅9行，缺少 `.env`, `.venv`, IDE文件, OS文件等
- `app/config.py` 404行，完善的3层配置系统
- 项目无 `.github/` 目录
- `pyproject.toml` 已有 pytest/coverage 配置，但无 Ruff 配置

### Self-Identified Gaps (Metis-equivalent)
**Addressed in plan**:
- pre-commit 需要作为 dev 依赖加入 pyproject.toml
- Ruff 配置需要考虑项目的 Python 3.9+ 兼容性
- CI 矩阵应测试 Python 3.9, 3.11, 3.12
- 结构化日志需要与现有 observability 模块集成，而非另起炉灶
- .gitignore 需要覆盖 macOS/Linux/Windows + 常见 IDE + 项目特有路径

---

## Work Objectives

### Core Objective
为 my-RDagent 补齐成熟开源项目的标准基础设施，覆盖 CI/CD、代码质量、社区协作、安全策略、可观测性五大领域。

### Concrete Deliverables
- `.github/workflows/ci.yml` — CI 流水线
- `.github/dependabot.yml` — 自动依赖更新
- `.github/ISSUE_TEMPLATE/bug_report.yml` — Bug 报告模板
- `.github/ISSUE_TEMPLATE/feature_request.yml` — 功能请求模板
- `.github/PULL_REQUEST_TEMPLATE.md` — PR 模板
- `.pre-commit-config.yaml` — pre-commit 配置
- `LICENSE` — MIT 许可证
- `CONTRIBUTING.md` — 贡献指南
- `SECURITY.md` — 安全策略
- `.gitignore` — 增强版
- `pyproject.toml` — 更新 Ruff 配置 + dev 依赖组
- `observability/logging_config.py` — 结构化日志配置模块

### Definition of Done
- [ ] `ruff check .` 零错误或仅有明确 ignore 的规则
- [ ] `ruff format --check .` 格式检查通过
- [ ] `python -m pytest tests -q` 全部通过
- [ ] `pre-commit run --all-files` 全部通过
- [ ] `.github/workflows/ci.yml` 语法正确 (可通过 `actionlint` 或 YAML schema 验证)
- [ ] 所有新文件存在且非空

### Must Have
- CI 必须在 Python 3.9 和 3.12 上都测试（兼容性保证）
- Ruff 配置的 `target-version` 必须是 `"py39"`
- CONTRIBUTING.md 必须包含本地开发设置步骤
- .gitignore 必须包含 `.env`（防止密钥泄露）
- 结构化日志必须复用现有 `observability/` 模块，不另起炉灶

### Must NOT Have (Guardrails)
- **不做 PyPI/Docker 镜像发布流水线** — 用户明确说不发布
- **不做 Kubernetes/Helm 配置** — 用户明确说暂不需要
- **不修改现有业务逻辑代码** — 本次只涉及基础设施文件
- **不引入 Black/Flake8/isort** — 全部用 Ruff 替代
- **不做 Changelog 自动生成** — 不在本次范围
- **不修改 Dockerfile/docker-compose.yml/Makefile** — 第一阶段产物，本次不动
- **Ruff 不做激进格式化** — 首次引入，先确保能通过，不破坏现有代码风格

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, 564 tests)
- **Automated tests**: YES (Tests-after — CI 集成 + 覆盖率)
- **Framework**: pytest + pytest-cov

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Config files**: Use Bash — validate YAML/TOML syntax, run `ruff check`, run `pre-commit`
- **Documentation**: Use Bash — check file exists, non-empty, contains required sections
- **CI workflow**: Use Bash — validate YAML syntax, check key fields present
- **Logging module**: Use Bash — import and run, verify JSON output format

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — independent config/doc files, MAX PARALLEL):
├── Task 1: pyproject.toml 更新 (Ruff + dev deps) [quick]
├── Task 2: MIT LICENSE 文件 [quick]
├── Task 3: 增强版 .gitignore [quick]
├── Task 4: CONTRIBUTING.md [quick]
├── Task 5: SECURITY.md [quick]
├── Task 6: GitHub Issue/PR 模板 [quick]
├── Task 7: Dependabot 配置 [quick]

Wave 2 (After Wave 1 — depends on Ruff config):
├── Task 8: pre-commit 配置 (depends: 1) [quick]
├── Task 9: GitHub Actions CI (depends: 1) [unspecified-high]
├── Task 10: 结构化日志配置 (depends: none, but logically wave 2) [unspecified-high]

Wave 3 (After ALL — verification):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real QA — run all tools [unspecified-high]
├── Task F4: Scope fidelity check [deep]

Critical Path: Task 1 → Task 8/9 → Task F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 7 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 8, 9 | 1 |
| 2 | — | — | 1 |
| 3 | — | — | 1 |
| 4 | — | — | 1 |
| 5 | — | — | 1 |
| 6 | — | — | 1 |
| 7 | — | — | 1 |
| 8 | 1 | F1-F4 | 2 |
| 9 | 1 | F1-F4 | 2 |
| 10 | — | F1-F4 | 2 |
| F1 | 1-10 | — | FINAL |
| F2 | 1-10 | — | FINAL |
| F3 | 1-10 | — | FINAL |
| F4 | 1-10 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **7 tasks** — T1-T7 → `quick`
- **Wave 2**: **3 tasks** — T8 → `quick`, T9 → `unspecified-high`, T10 → `unspecified-high`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [ ] 1. pyproject.toml 更新：Ruff 配置 + dev 依赖组

  **What to do**:
  - 在 `pyproject.toml` 中添加 `[tool.ruff]` 配置段：
    - `target-version = "py39"` （匹配项目最低 Python 版本）
    - `line-length = 120` （宽松行长，减少初次引入的格式冲突）
    - `[tool.ruff.lint]` 启用规则集：`["E", "F", "W", "I", "UP", "B", "SIM"]`
    - `[tool.ruff.lint.isort]` 配置 import 排序
    - `[tool.ruff.format]` 使用默认配置（兼容 Black 风格）
    - 添加合理的 `exclude` 列表：`[".venv", "venv", "build", "dist", ".eggs"]`
  - 在 `[project.optional-dependencies]` 中添加 `dev` 依赖组：
    - `ruff>=0.4.0`
    - `pre-commit>=3.5.0`
  - 更新 `all` 依赖组包含 `dev` 组的包
  - **不修改**现有的 `[tool.pytest.ini_options]` 和 `[tool.coverage.*]` 配置

  **Must NOT do**:
  - 不删除或修改任何已有配置段
  - 不修改 `dependencies` 核心依赖
  - 不设置过于激进的 lint 规则（如 `D` docstring 规则）——首次引入要温和

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件 TOML 配置修改，结构明确
  - **Skills**: []
    - No special skills needed — straightforward config edit

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 6, 7)
  - **Blocks**: Tasks 8 (pre-commit), 9 (CI)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `pyproject.toml:1-100` — 现有完整配置，需要在此基础上追加 Ruff 配置段和 dev 依赖组

  **API/Type References**:
  - N/A

  **External References**:
  - Ruff 官方配置文档: https://docs.astral.sh/ruff/configuration/
  - Ruff 规则列表: https://docs.astral.sh/ruff/rules/

  **WHY Each Reference Matters**:
  - `pyproject.toml` — 必须在现有文件基础上追加，不能覆盖已有的 pytest/coverage 配置
  - Ruff 文档 — 确保规则集选择合理，target-version 正确

  **Acceptance Criteria**:

  - [ ] `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` 无报错
  - [ ] `ruff check --config pyproject.toml . --statistics` 可执行（可能有 warning 但不 crash）
  - [ ] `[tool.ruff]` 段存在且 `target-version = "py39"`
  - [ ] `[project.optional-dependencies]` 包含 `dev` 组

  **QA Scenarios**:

  ```
  Scenario: TOML 语法正确性验证
    Tool: Bash
    Preconditions: pyproject.toml 已修改
    Steps:
      1. python -c "import tomllib; data = tomllib.load(open('pyproject.toml','rb')); print(data['tool']['ruff']['target-version'])"
      2. 输出应为 "py39"
    Expected Result: 输出 "py39"，无异常
    Failure Indicators: tomllib.TOMLDecodeError 或 KeyError
    Evidence: .sisyphus/evidence/task-1-toml-valid.txt

  Scenario: Ruff 可运行验证
    Tool: Bash
    Preconditions: ruff 已安装 (uv pip install ruff)
    Steps:
      1. uv pip install ruff
      2. ruff check . --config pyproject.toml --statistics 2>&1 | head -20
      3. 退出码为 0 或 1（有 warning 可接受，不能是配置错误的退出码 2）
    Expected Result: ruff 能读取配置并执行检查，不报 "Invalid configuration"
    Failure Indicators: 退出码 2 + "Invalid configuration" 错误信息
    Evidence: .sisyphus/evidence/task-1-ruff-check.txt

  Scenario: dev 依赖组存在验证
    Tool: Bash
    Preconditions: pyproject.toml 已修改
    Steps:
      1. python -c "import tomllib; data = tomllib.load(open('pyproject.toml','rb')); deps = data['project']['optional-dependencies']['dev']; print(deps)"
      2. 输出应包含 'ruff' 和 'pre-commit'
    Expected Result: 列表中包含 ruff 和 pre-commit 的版本约束
    Failure Indicators: KeyError('dev') 或列表为空
    Evidence: .sisyphus/evidence/task-1-dev-deps.txt
  ```

  **Commit**: YES (groups with Commit 2)
  - Message: `build: add Ruff config, pre-commit hooks, and CI pipeline`
  - Files: `pyproject.toml`
  - Pre-commit: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`

- [ ] 2. MIT LICENSE 文件

  **What to do**:
  - 创建 `LICENSE` 文件，内容为标准 MIT License 全文
  - Copyright 行使用: `Copyright (c) 2024 RDAgent Contributors`
  - 确保文件末尾有换行符

  **Must NOT do**:
  - 不修改任何其他文件
  - 不在 README 中修改 License 部分（那是另一个任务范围外的事）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个标准模板文件创建
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5, 6, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pyproject.toml:7` — `license = {text = "MIT"}` — 确认项目选择了 MIT

  **External References**:
  - MIT License 标准文本: https://opensource.org/licenses/MIT

  **WHY Each Reference Matters**:
  - pyproject.toml 的 license 字段确认了用户的选择

  **Acceptance Criteria**:

  - [ ] `LICENSE` 文件存在于项目根目录
  - [ ] 第一行包含 "MIT License"
  - [ ] 文件包含 "Copyright (c)"
  - [ ] 文件包含 "Permission is hereby granted"

  **QA Scenarios**:

  ```
  Scenario: LICENSE 文件内容验证
    Tool: Bash
    Preconditions: LICENSE 文件已创建
    Steps:
      1. head -1 LICENSE
      2. grep -c "Permission is hereby granted" LICENSE
      3. grep -c "Copyright (c)" LICENSE
    Expected Result: 第一行为 "MIT License"，两个 grep 都返回 1
    Failure Indicators: 文件不存在或 grep 返回 0
    Evidence: .sisyphus/evidence/task-2-license-content.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `LICENSE`

- [ ] 3. 增强版 .gitignore

  **What to do**:
  - 重写 `.gitignore`，保留现有9行规则，大幅扩展覆盖范围：
    - **Python**: `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `*.egg-info/`, `dist/`, `build/`, `.eggs/`, `*.egg`, `.mypy_cache/`, `.ruff_cache/`
    - **Virtual Environments**: `.venv/`, `venv/`, `env/`, `.env` (环境变量文件!)
    - **IDE**: `.vscode/`, `.idea/`, `*.swp`, `*.swo`, `*.swn`, `.project`, `.settings/`
    - **OS**: `.DS_Store`, `Thumbs.db`, `desktop.ini`, `*~`
    - **Project-specific**: `config.yaml` (已有), `*.sqlite3`, `logs/`, `/tmp/`, `.coverage`, `htmlcov/`, `coverage.xml`
    - **Artifacts**: `/tmp/rd_agent_*` patterns
  - 用注释分组，保持可读性
  - **确保 `.env` 在列表中**（防止 API key 泄露到 git）

  **Must NOT do**:
  - 不删除 `config.yaml`（已有的规则必须保留）
  - 不添加 `config.example.yaml` 到 ignore（模板文件需要追踪）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件扩展，模板性质
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5, 6, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `.gitignore:1-9` — 现有规则，必须全部保留：`__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `*.egg-info/`, `dist/`, `build/`, `.eggs/`, `config.yaml`

  **External References**:
  - GitHub 官方 Python .gitignore: https://github.com/github/gitignore/blob/main/Python.gitignore

  **WHY Each Reference Matters**:
  - 现有 .gitignore 的9行规则不能丢失
  - GitHub 官方模板作为参考基线

  **Acceptance Criteria**:

  - [ ] `.gitignore` 行数 > 30
  - [ ] 包含 `.env`（安全关键）
  - [ ] 包含 `.DS_Store`（macOS）
  - [ ] 包含 `.venv/`（虚拟环境）
  - [ ] 包含 `.ruff_cache/`（新增工具）
  - [ ] 保留原有 `config.yaml` 规则

  **QA Scenarios**:

  ```
  Scenario: .gitignore 关键规则验证
    Tool: Bash
    Preconditions: .gitignore 已更新
    Steps:
      1. wc -l .gitignore  → 应 > 30
      2. grep -c "^\.env$" .gitignore  → 应为 1
      3. grep -c "\.DS_Store" .gitignore  → 应为 1
      4. grep -c "\.venv" .gitignore  → 应为 1
      5. grep -c "config\.yaml" .gitignore  → 应为 1
      6. grep -c "\.ruff_cache" .gitignore  → 应为 1
    Expected Result: 行数 > 30，所有 grep 返回 >= 1
    Failure Indicators: 任何 grep 返回 0 或行数 <= 30
    Evidence: .sisyphus/evidence/task-3-gitignore-rules.txt

  Scenario: .env 文件确实被忽略
    Tool: Bash
    Preconditions: .gitignore 已更新
    Steps:
      1. touch .env.test-ignore
      2. git check-ignore .env.test-ignore  → 应输出路径
      3. rm .env.test-ignore
    Expected Result: git check-ignore 返回文件路径（表示被忽略）
    Failure Indicators: git check-ignore 无输出（未被忽略）
    Evidence: .sisyphus/evidence/task-3-env-ignored.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `.gitignore`

- [ ] 4. CONTRIBUTING.md — 贡献指南

  **What to do**:
  - 创建 `CONTRIBUTING.md`，中文为主（匹配项目语境），包含以下章节：
    - **欢迎** — 简短感谢语
    - **开发环境设置** — uv 安装、依赖安装（`uv pip install -e ".[all]"`）、pre-commit 安装（`pre-commit install`）
    - **开发工作流** — Fork → Branch → Code → Test → PR
    - **代码风格** — Ruff 管理，`ruff check .` + `ruff format .`
    - **测试** — `python -m pytest tests -q`，新功能必须附带测试
    - **Commit 规范** — Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `build:`)
    - **PR 要求** — 描述变更、通过 CI、关联 Issue
    - **Issue 报告** — 指向 Issue 模板
    - **行为准则** — 简要说明尊重和包容
  - 确保所有命令可直接复制粘贴运行

  **Must NOT do**:
  - 不创建单独的 CODE_OF_CONDUCT.md（在 CONTRIBUTING 中简要说明即可）
  - 不引用不存在的工具或命令

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准文档模板，参考项目现有工具链填充即可
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5, 6, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pyproject.toml:29-60` — optional-dependencies 列表，CONTRIBUTING 中需要引用安装命令
  - `Makefile:1-全文` — 已有 make 快捷命令，CONTRIBUTING 应引用这些命令
  - `QUICKSTART.md:1-全文` — 已有快速上手指南，CONTRIBUTING 的设置步骤应与之一致

  **WHY Each Reference Matters**:
  - pyproject.toml 的依赖组决定了安装命令写法
  - Makefile 已有 `make install`, `make test` 等命令，应在 CONTRIBUTING 中引用
  - QUICKSTART.md 确保两份文档的设置步骤不矛盾

  **Acceptance Criteria**:

  - [ ] `CONTRIBUTING.md` 存在且 > 100 行
  - [ ] 包含 "uv" 关键字（环境设置）
  - [ ] 包含 "ruff" 关键字（代码风格）
  - [ ] 包含 "pytest" 关键字（测试）
  - [ ] 包含 "pre-commit" 关键字（hooks）

  **QA Scenarios**:

  ```
  Scenario: CONTRIBUTING.md 内容完整性验证
    Tool: Bash
    Preconditions: CONTRIBUTING.md 已创建
    Steps:
      1. wc -l CONTRIBUTING.md  → 应 > 100
      2. grep -ci "uv" CONTRIBUTING.md  → 应 >= 1
      3. grep -ci "ruff" CONTRIBUTING.md  → 应 >= 1
      4. grep -ci "pytest" CONTRIBUTING.md  → 应 >= 1
      5. grep -ci "pre-commit" CONTRIBUTING.md  → 应 >= 1
      6. grep -ci "fork" CONTRIBUTING.md  → 应 >= 1 (PR 工作流)
    Expected Result: 所有检查通过
    Failure Indicators: 任何 grep 返回 0 或行数 <= 100
    Evidence: .sisyphus/evidence/task-4-contributing-content.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `CONTRIBUTING.md`

- [ ] 5. SECURITY.md — 安全策略

  **What to do**:
  - 创建 `SECURITY.md`，英文为主（安全文档国际惯例），包含：
    - **Supported Versions** — 表格列出 v0.1.x 为当前支持版本
    - **Reporting a Vulnerability** — 邮件报告流程（不公开 Issue），提供模板邮箱占位符
    - **Response Timeline** — 承诺48小时内确认收到，7天内初步评估
    - **Disclosure Policy** — 修复后公开披露，感谢报告者
    - **Security Best Practices** — 提醒用户：不要硬编码 API key，使用 `.env`，Docker 沙箱执行
  - 引用项目已有的安全机制：`observability/redaction.py` 的敏感字段脱敏

  **Must NOT do**:
  - 不提供真实邮箱（用占位符 `security@example.com`，用户自行替换）
  - 不修改任何代码文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准安全策略模板
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 6, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `observability/redaction.py:7-16` — `SENSITIVE_KEYWORDS` 列表，SECURITY.md 应提及项目已有脱敏机制
  - `.env.example:1-全文` — 列出了所有敏感环境变量，SECURITY.md 应引用此文件

  **WHY Each Reference Matters**:
  - redaction.py 证明项目已有安全意识，可在 SECURITY.md 中展示
  - .env.example 是安全配置的参考

  **Acceptance Criteria**:

  - [ ] `SECURITY.md` 存在且 > 30 行
  - [ ] 包含 "Reporting" 关键字
  - [ ] 包含 "vulnerability" 关键字（不区分大小写）
  - [ ] 包含联系方式占位符

  **QA Scenarios**:

  ```
  Scenario: SECURITY.md 必要内容验证
    Tool: Bash
    Preconditions: SECURITY.md 已创建
    Steps:
      1. wc -l SECURITY.md  → 应 > 30
      2. grep -ci "reporting" SECURITY.md  → 应 >= 1
      3. grep -ci "vulnerability" SECURITY.md  → 应 >= 1
      4. grep -ci "email\|@" SECURITY.md  → 应 >= 1 (联系方式)
    Expected Result: 所有检查通过
    Failure Indicators: 任何 grep 返回 0
    Evidence: .sisyphus/evidence/task-5-security-content.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `SECURITY.md`

- [ ] 6. GitHub Issue/PR 模板

  **What to do**:
  - 创建 `.github/ISSUE_TEMPLATE/bug_report.yml`（YAML-based template form）:
    - 标题前缀: `[Bug]`
    - 必填字段: 描述、复现步骤、预期行为、实际行为
    - 可选字段: 环境信息（OS, Python版本, Docker版本）、日志输出、截图
    - Labels: `bug`
  - 创建 `.github/ISSUE_TEMPLATE/feature_request.yml`:
    - 标题前缀: `[Feature]`
    - 必填字段: 功能描述、使用场景
    - 可选字段: 替代方案、补充说明
    - Labels: `enhancement`
  - 创建 `.github/PULL_REQUEST_TEMPLATE.md`:
    - Checklist: 关联 Issue、描述变更、测试覆盖、CI 通过
    - 变更类型分类: Bug fix / Feature / Docs / Refactor

  **Must NOT do**:
  - 不创建 `config.yml` 来禁用空白 Issue（保持灵活性）
  - 不添加 assignees 或 project 自动化（项目尚小）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准模板文件，结构固定
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 5, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **External References**:
  - GitHub Issue Forms 文档: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms

  **WHY Each Reference Matters**:
  - Issue Forms 使用 YAML 语法而非 Markdown，需要参考正确的 schema

  **Acceptance Criteria**:

  - [ ] `.github/ISSUE_TEMPLATE/bug_report.yml` 存在
  - [ ] `.github/ISSUE_TEMPLATE/feature_request.yml` 存在
  - [ ] `.github/PULL_REQUEST_TEMPLATE.md` 存在
  - [ ] YAML 文件语法正确

  **QA Scenarios**:

  ```
  Scenario: GitHub 模板文件存在性和语法验证
    Tool: Bash
    Preconditions: 模板文件已创建
    Steps:
      1. test -f .github/ISSUE_TEMPLATE/bug_report.yml && echo "OK" || echo "MISSING"
      2. test -f .github/ISSUE_TEMPLATE/feature_request.yml && echo "OK" || echo "MISSING"
      3. test -f .github/PULL_REQUEST_TEMPLATE.md && echo "OK" || echo "MISSING"
      4. python -c "import yaml; yaml.safe_load(open('.github/ISSUE_TEMPLATE/bug_report.yml'))" && echo "VALID"
      5. python -c "import yaml; yaml.safe_load(open('.github/ISSUE_TEMPLATE/feature_request.yml'))" && echo "VALID"
    Expected Result: 全部输出 OK/VALID
    Failure Indicators: MISSING 或 yaml.YAMLError
    Evidence: .sisyphus/evidence/task-6-templates-valid.txt

  Scenario: PR 模板包含必要 checklist
    Tool: Bash
    Preconditions: PR 模板已创建
    Steps:
      1. grep -c "\- \[" .github/PULL_REQUEST_TEMPLATE.md  → 应 >= 3 (至少3个 checklist 项)
      2. grep -ci "issue\|related\|closes" .github/PULL_REQUEST_TEMPLATE.md  → 应 >= 1
    Expected Result: checklist 项 >= 3，包含 Issue 关联提示
    Failure Indicators: grep 返回 0
    Evidence: .sisyphus/evidence/task-6-pr-template.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] 7. Dependabot 配置

  **What to do**:
  - 创建 `.github/dependabot.yml`，配置：
    - `package-ecosystem: "pip"` — 监控 Python 依赖
    - `directory: "/"` — 项目根目录
    - `schedule.interval: "weekly"` — 每周检查一次
    - `open-pull-requests-limit: 10` — 限制并发 PR 数
    - `labels: ["dependencies"]` — 自动添加标签
    - `commit-message.prefix: "build"` — 遵循 Conventional Commits
  - 添加 `package-ecosystem: "github-actions"` 用于自动更新 CI action 版本

  **Must NOT do**:
  - 不配置 Docker ecosystem（不发布镜像）
  - 不设置 auto-merge（需要人工审核）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个小型 YAML 配置文件
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 5, 6)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:

  **External References**:
  - Dependabot 配置文档: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

  **WHY Each Reference Matters**:
  - 确保 YAML schema 正确，尤其是 `version: 2` 必须声明

  **Acceptance Criteria**:

  - [ ] `.github/dependabot.yml` 存在
  - [ ] 包含 `version: 2`
  - [ ] 包含 pip ecosystem 配置
  - [ ] 包含 github-actions ecosystem 配置
  - [ ] YAML 语法正确

  **QA Scenarios**:

  ```
  Scenario: Dependabot 配置有效性验证
    Tool: Bash
    Preconditions: dependabot.yml 已创建
    Steps:
      1. python -c "import yaml; d=yaml.safe_load(open('.github/dependabot.yml')); print(d['version'])"  → 输出 2
      2. python -c "import yaml; d=yaml.safe_load(open('.github/dependabot.yml')); ecosystems=[u['package-ecosystem'] for u in d['updates']]; print(ecosystems)"
      3. 输出应包含 'pip' 和 'github-actions'
    Expected Result: version=2，包含两个 ecosystem
    Failure Indicators: yaml.YAMLError 或缺少 ecosystem
    Evidence: .sisyphus/evidence/task-7-dependabot-valid.txt
  ```

  **Commit**: YES (groups with Commit 1)
  - Message: `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `.github/dependabot.yml`

- [ ] 8. pre-commit 配置

  **What to do**:
  - 创建 `.pre-commit-config.yaml`，hooks 列表：
    - **ruff** (via `astral-sh/ruff-pre-commit`):
      - `ruff` hook (linting, with `--fix`)
      - `ruff-format` hook (formatting)
    - **pre-commit-hooks** (via `pre-commit/pre-commit-hooks`):
      - `trailing-whitespace`
      - `end-of-file-fixer`
      - `check-yaml`
      - `check-toml`
      - `check-added-large-files` (限制 500KB)
      - `check-merge-conflict`
  - 使用固定版本号（不用 `latest`），Ruff 使用 `v0.4.0+` 版本

  **Must NOT do**:
  - 不添加 Black/Flake8/isort hooks（全用 Ruff）
  - 不添加 mypy hook（项目未使用 type checking，首次引入不宜过激）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单个 YAML 配置文件，结构标准化
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (与 Task 9 并行)
  - **Parallel Group**: Wave 2 (with Tasks 9, 10)
  - **Blocks**: F1-F4 (Final Verification)
  - **Blocked By**: Task 1 (需要 pyproject.toml 中的 Ruff 配置)

  **References**:

  **Pattern References**:
  - `pyproject.toml` (Task 1 完成后) — Ruff 配置，pre-commit 的 ruff hook 会读取这些配置

  **External References**:
  - Ruff pre-commit integration: https://docs.astral.sh/ruff/integrations/#pre-commit
  - pre-commit-hooks 列表: https://github.com/pre-commit/pre-commit-hooks

  **WHY Each Reference Matters**:
  - Ruff pre-commit 文档确保 hook 版本和 repo URL 正确
  - pre-commit-hooks 确认可用的通用 hooks

  **Acceptance Criteria**:

  - [ ] `.pre-commit-config.yaml` 存在
  - [ ] 包含 `ruff` 和 `ruff-format` hooks
  - [ ] 包含 `trailing-whitespace` 等基础 hooks
  - [ ] `pre-commit run --all-files` 可执行（可能有 fixable issues，但不 crash）
  - [ ] 不包含 black/flake8/isort hooks

  **QA Scenarios**:

  ```
  Scenario: pre-commit 配置可加载验证
    Tool: Bash
    Preconditions: .pre-commit-config.yaml 已创建，pre-commit 已安装
    Steps:
      1. uv pip install pre-commit
      2. python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" && echo "VALID YAML"
      3. pre-commit run --all-files 2>&1 | tail -20
      4. 检查退出码：0=全部通过, 1=有修复但可接受
    Expected Result: YAML 有效，pre-commit 能运行不 crash
    Failure Indicators: yaml.YAMLError 或 "hook not found" 错误
    Evidence: .sisyphus/evidence/task-8-precommit-run.txt

  Scenario: 不包含禁止的 hooks
    Tool: Bash
    Preconditions: .pre-commit-config.yaml 已创建
    Steps:
      1. grep -ci "black" .pre-commit-config.yaml  → 应为 0
      2. grep -ci "flake8" .pre-commit-config.yaml  → 应为 0
      3. grep -ci "isort" .pre-commit-config.yaml  → 应为 0
    Expected Result: 所有 grep 返回 0
    Failure Indicators: 任何返回 > 0
    Evidence: .sisyphus/evidence/task-8-no-forbidden-hooks.txt
  ```

  **Commit**: YES (groups with Commit 2)
  - Message: `build: add Ruff config, pre-commit hooks, and CI pipeline`
  - Files: `.pre-commit-config.yaml`

- [ ] 9. GitHub Actions CI 流水线

  **What to do**:
  - 创建 `.github/workflows/ci.yml`，包含以下 jobs：

  **Job 1: `lint`** (快速反馈)
  - 触发: `push` to `main`, `pull_request`
  - Runner: `ubuntu-latest`
  - Steps:
    1. `actions/checkout@v4`
    2. `actions/setup-python@v5` with `python-version: "3.12"`
    3. 安装 uv: `astral-sh/setup-uv@v4`
    4. `uv pip install ruff`
    5. `ruff check .`
    6. `ruff format --check .`

  **Job 2: `test`** (矩阵测试)
  - 触发: 同上
  - Strategy matrix: `python-version: ["3.9", "3.11", "3.12"]`
  - Runner: `ubuntu-latest`
  - Steps:
    1. `actions/checkout@v4`
    2. `actions/setup-python@v5` with matrix python-version
    3. 安装 uv: `astral-sh/setup-uv@v4`
    4. `uv venv` + `uv pip install -e ".[all]"`
    5. `python -m pytest tests -q --tb=short --cov=. --cov-report=xml --cov-report=term-missing`
    6. 上传 coverage artifact: `actions/upload-artifact@v4`

  **Job 3: `build-check`** (构建验证)
  - 触发: 同上
  - Needs: `lint`
  - Steps:
    1. `actions/checkout@v4`
    2. `actions/setup-python@v5` with `python-version: "3.12"`
    3. 安装 uv + hatchling
    4. `python -m build` 验证包构建
    5. `docker compose config` 验证 Docker 配置

  - 使用 `concurrency` 配置：同一 PR 取消旧的运行
  - 在 workflow 级别设置 `permissions: contents: read`

  **Must NOT do**:
  - **不做 PyPI publish job** — 用户明确说不发布
  - **不做 Docker push job** — 用户明确说不发布
  - 不使用 `continue-on-error: true`（测试失败必须阻断）
  - 不缓存 `.venv`（uv 足够快，缓存容易引入问题）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: CI 流水线配置复杂度较高，需要正确的 action 版本和 YAML 结构
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (与 Task 8, 10 并行)
  - **Parallel Group**: Wave 2 (with Tasks 8, 10)
  - **Blocks**: F1-F4 (Final Verification)
  - **Blocked By**: Task 1 (需要 pyproject.toml 中的 Ruff 配置和依赖定义)

  **References**:

  **Pattern References**:
  - `pyproject.toml:1-100` — 依赖定义、pytest 配置、scripts 入口
  - `Dockerfile:1-141` — docker compose config 验证参考
  - `docker-compose.yml:1-全文` — build-check 中需要验证此文件

  **External References**:
  - actions/checkout@v4: https://github.com/actions/checkout
  - actions/setup-python@v5: https://github.com/actions/setup-python
  - astral-sh/setup-uv@v4: https://github.com/astral-sh/setup-uv

  **WHY Each Reference Matters**:
  - pyproject.toml 决定了 CI 中的安装命令和测试命令
  - Docker 文件决定了 build-check job 的验证内容
  - Action 版本必须使用最新的 v4/v5 以避免 Node.js 16 deprecation 警告

  **Acceptance Criteria**:

  - [ ] `.github/workflows/ci.yml` 存在
  - [ ] YAML 语法正确
  - [ ] 包含 `lint`, `test`, `build-check` 三个 jobs
  - [ ] test job 使用 Python 矩阵 [3.9, 3.11, 3.12]
  - [ ] 不包含 publish/push 相关 steps
  - [ ] 使用 `concurrency` 配置

  **QA Scenarios**:

  ```
  Scenario: CI 配置 YAML 有效性验证
    Tool: Bash
    Preconditions: ci.yml 已创建
    Steps:
      1. python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print(list(d.get('jobs',{}).keys()))"
      2. 输出应包含 'lint', 'test', 'build-check'（或类似名称）
    Expected Result: 三个 job 名称都出现在列表中
    Failure Indicators: yaml.YAMLError 或缺少 job
    Evidence: .sisyphus/evidence/task-9-ci-jobs.txt

  Scenario: CI 不包含发布 steps
    Tool: Bash
    Preconditions: ci.yml 已创建
    Steps:
      1. grep -ci "publish\|pypi\|push\|registry\|docker login\|ghcr" .github/workflows/ci.yml  → 应为 0
    Expected Result: grep 返回 0（无发布相关内容）
    Failure Indicators: grep 返回 > 0
    Evidence: .sisyphus/evidence/task-9-no-publish.txt

  Scenario: Python 矩阵版本验证
    Tool: Bash
    Preconditions: ci.yml 已创建
    Steps:
      1. grep -c "3.9" .github/workflows/ci.yml  → 应 >= 1
      2. grep -c "3.12" .github/workflows/ci.yml  → 应 >= 1
    Expected Result: 两个 Python 版本都出现
    Failure Indicators: 任何 grep 返回 0
    Evidence: .sisyphus/evidence/task-9-python-matrix.txt
  ```

  **Commit**: YES (groups with Commit 2)
  - Message: `build: add Ruff config, pre-commit hooks, and CI pipeline`
  - Files: `.github/workflows/ci.yml`

- [ ] 10. 结构化日志配置模块

  **What to do**:
  - 创建 `observability/logging_config.py`，提供：

  **`configure_logging(level: str = "INFO", json_format: bool = True) -> None`** 函数：
  - 使用 Python 标准库 `logging` + `logging.config.dictConfig`
  - JSON 模式时使用自定义 `JsonFormatter`：
    - 输出字段: `timestamp` (ISO 8601), `level`, `logger`, `message`, `module`, `function`, `line`
    - 额外字段通过 `extra` dict 传入
    - 使用 `observability/redaction.py` 的 `sanitize_payload` 对日志内容脱敏
  - 非 JSON 模式时使用标准 `logging.Formatter`（人类可读格式，开发环境用）
  - 配置 root logger + `uvicorn`, `uvicorn.access`, `uvicorn.error` 的 handler
  - 集成点：在 `app/config.py` 的配置中已有 `log_level` 字段，新模块应接受此配置

  **`JsonFormatter(logging.Formatter)`** 类：
  - 继承 `logging.Formatter`
  - `format(record)` → JSON 字符串
  - 自动捕获 exception info (`exc_info`)
  - 调用 `sanitize_payload` 对 `record.__dict__` 脱敏

  **Must NOT do**:
  - **不修改 `observability/service.py`** — 现有模块保持不变
  - **不修改 `observability/__init__.py`** — 不改变现有导出
  - **不安装第三方日志库** (如 structlog, python-json-logger) — 纯标准库实现
  - **不修改 `app/config.py`** — 不改变业务逻辑代码

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要正确实现 Python logging 配置和 JSON formatter，有一定复杂度
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (与 Task 8, 9 并行)
  - **Parallel Group**: Wave 2 (with Tasks 8, 9)
  - **Blocks**: F1-F4 (Final Verification)
  - **Blocked By**: None (逻辑上 Wave 2 但无硬依赖)

  **References**:

  **Pattern References**:
  - `observability/service.py:1-88` — 现有 Observability 类的 JSON 日志格式（`json.dumps(record, ensure_ascii=False, sort_keys=True)`），新模块的 JSON 格式应与之一致
  - `observability/redaction.py:24-41` — `sanitize_payload` 函数签名和行为，新模块必须调用此函数
  - `observability/__init__.py` — 查看现有导出，不要修改
  - `app/config.py:24` — `log_level: str` 字段，新模块的 `configure_logging` 应接受此值

  **API/Type References**:
  - `observability/redaction.py:sanitize_payload(payload: Any, sensitive_keywords: Iterable[str] = SENSITIVE_KEYWORDS, redacted_value: str = "***") -> Any`

  **External References**:
  - Python logging.config.dictConfig: https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig
  - Python logging Formatter: https://docs.python.org/3/library/logging.html#formatter-objects

  **WHY Each Reference Matters**:
  - `service.py` 的 JSON 格式是参考基线，新模块的输出格式应保持一致风格
  - `redaction.py` 的 `sanitize_payload` 必须被复用，不能重新实现脱敏逻辑
  - `config.py` 的 `log_level` 字段是集成点

  **Acceptance Criteria**:

  - [ ] `observability/logging_config.py` 存在
  - [ ] `from observability.logging_config import configure_logging, JsonFormatter` 无报错
  - [ ] `configure_logging("DEBUG", json_format=True)` 后，`logging.getLogger("test").info("hello")` 输出有效 JSON
  - [ ] JSON 输出包含 `timestamp`, `level`, `message` 字段
  - [ ] 敏感字段被脱敏（含 "api_key" 的 extra 字段应显示 "***"）
  - [ ] `observability/service.py` 和 `observability/__init__.py` 未被修改

  **QA Scenarios**:

  ```
  Scenario: JSON 日志格式验证
    Tool: Bash
    Preconditions: logging_config.py 已创建
    Steps:
      1. python -c "
         from observability.logging_config import configure_logging
         import logging, json
         configure_logging('DEBUG', json_format=True)
         logger = logging.getLogger('test_json')
         logger.info('hello world')
         "  2>&1 | tail -1 | python -c "import sys,json; d=json.load(sys.stdin); print(d['level'], d['message'])"
      2. 输出应为 "INFO hello world"
    Expected Result: 日志输出可被解析为有效 JSON，包含 level 和 message
    Failure Indicators: json.JSONDecodeError 或 KeyError
    Evidence: .sisyphus/evidence/task-10-json-format.txt

  Scenario: 敏感字段脱敏验证
    Tool: Bash
    Preconditions: logging_config.py 已创建
    Steps:
      1. python -c "
         from observability.logging_config import configure_logging
         import logging, json
         configure_logging('DEBUG', json_format=True)
         logger = logging.getLogger('test_redact')
         logger.info('test', extra={'api_key': 'sk-12345'})
         "  2>&1 | tail -1 | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('api_key', d.get('extra',{}).get('api_key','NOT_FOUND')))"
      2. 输出应为 "***" 而非 "sk-12345"
    Expected Result: api_key 字段值为 "***"
    Failure Indicators: 输出包含 "sk-12345"
    Evidence: .sisyphus/evidence/task-10-redaction.txt

  Scenario: 现有 observability 文件未被修改
    Tool: Bash
    Preconditions: 实现完成
    Steps:
      1. git diff --name-only observability/service.py observability/__init__.py
      2. 输出应为空（无变更）
    Expected Result: 两个文件无 diff
    Failure Indicators: 输出非空
    Evidence: .sisyphus/evidence/task-10-no-modify.txt
  ```

  **Commit**: YES (Commit 3)
  - Message: `feat(observability): add structured JSON logging configuration`
  - Files: `observability/logging_config.py`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `ruff check .` + `ruff format --check .` + `python -m pytest tests -q`. Review all new/changed files for: syntax errors, missing required fields, incorrect YAML structure, broken references. Check that pyproject.toml is valid TOML. Check CI workflow uses correct action versions.
  Output: `Ruff [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA** — `unspecified-high`
  Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Run `pre-commit run --all-files`. Run `python -c "from observability.logging_config import ..."`. Validate all YAML files. Verify .gitignore blocks `.env` files. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual changes. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance — verify Dockerfile/docker-compose/Makefile were NOT modified. Verify no business logic files were changed. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | No-touch files [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **Commit 1** (Wave 1): `chore: add MIT license, community docs, and enhanced .gitignore`
  - Files: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`, `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/dependabot.yml`
- **Commit 2** (Wave 1+2): `build: add Ruff config, pre-commit hooks, and CI pipeline`
  - Files: `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`
- **Commit 3** (Wave 2): `feat(observability): add structured JSON logging configuration`
  - Files: `observability/logging_config.py`

---

## Success Criteria

### Verification Commands
```bash
ruff check .                    # Expected: 0 errors (or only ignored rules)
ruff format --check .           # Expected: All files formatted
python -m pytest tests -q       # Expected: 564 passed
pre-commit run --all-files      # Expected: all hooks passed
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"  # Expected: no error
python -c "from observability.logging_config import configure_logging; configure_logging()"  # Expected: no error
cat LICENSE | head -1            # Expected: "MIT License"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] All new files exist and are non-empty
- [ ] CI workflow is valid YAML
- [ ] No secrets committed
