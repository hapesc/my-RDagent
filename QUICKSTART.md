# RDAgent 快速开始指南

本指南介绍如何使用 **uv** 和 **Docker** 快速搭建 RDAgent 开发环境。

## 📦 环境准备

### 方式一：本地开发（推荐）

#### 1. 安装 uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 克隆并进入项目
```bash
cd /path/to/rdagent
```

#### 3. 创建虚拟环境并安装依赖
```bash
# 仅安装核心依赖（使用 mock LLM）
make install

# 或安装所有依赖（包含 litellm、fastapi、streamlit、pytest）
make install-all
```

或者手动操作：
```bash
uv venv
uv pip install -e ".[all]"
```

#### 4. 验证安装
```bash
python -m app.startup
```

#### 5. 运行示例
```bash
# 使用 mock provider（无需 API key）
python cli.py --scenario data_science --task "classify iris dataset" --max-steps 3

# 或使用完整 CLI
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
python agentrd_cli.py run \
  --scenario data_science \
  --loops-per-call 1 \
  --max-loops 3 \
  --input '{"task_summary": "classify iris dataset", "max_loops": 3}'
```

---

### 方式二：Docker（开箱即用）

#### 1. 快速启动所有服务
```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，设置你的 LLM API key（可选）
# 如果不设置，默认使用 mock provider

# 一键启动
make quickstart

# 或手动启动
# docker-compose up -d api ui
```

启动后访问：
- **API**: http://localhost:8000
- **UI**: http://localhost:8501

#### 2. 常用 Docker 命令
```bash
# 构建镜像
make build

# 启动服务
make up

# 查看日志
make logs

# 进入开发容器
make dev-shell

# 运行测试
make test

# 停止并清理
make down
make clean
```

#### 3. 单独启动服务
```bash
# 仅启动 API
docker-compose up -d api

# 仅启动 UI
docker-compose up -d ui

# 仅启动基础应用
docker-compose up -d app
```

---

## 🔧 配置 LLM Provider

### 使用 LiteLLM（推荐）

编辑 `.env` 文件：
```bash
RD_AGENT_LLM_PROVIDER=litellm
RD_AGENT_LLM_API_KEY=sk-your-api-key
RD_AGENT_LLM_MODEL=gpt-4o-mini
```

支持的模型格式：
- OpenAI: `gpt-4o-mini`, `gpt-4o`
- Anthropic: `claude-3-sonnet-20240229`
- Google: `gemini/gemini-2.5-pro`

### 使用 Mock Provider（测试）
```bash
RD_AGENT_LLM_PROVIDER=mock
```

---

## 🧪 运行测试

### 本地测试
```bash
make test

# 或带覆盖率报告
make test-cov
```

### Docker 测试
```bash
docker-compose run --rm test
```

---

## 🚀 启动 REST API

### 本地启动
```bash
# 确保安装了 api 依赖
uv pip install -e ".[api]"

# 启动服务器
uvicorn app.api_main:app --host 127.0.0.1 --port 8000 --reload
```

访问：
- API 文档: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

### Docker 启动
```bash
make api
```

---

## 🎨 启动 Streamlit UI

### 本地启动
```bash
# 确保安装了 ui 依赖
uv pip install -e ".[ui]"

# 启动 UI
streamlit run ui/trace_ui.py
```

### Docker 启动
```bash
make ui
```

---

## 📁 项目结构

```
.
├── pyproject.toml          # 主要依赖配置（uv/pip 使用）
├── requirements.txt        # 兼容文件（已标记为 deprecated）
├── Dockerfile              # 多阶段构建配置
├── docker-compose.yml      # 服务编排
├── Makefile                # 常用命令快捷方式
├── .env.example            # 环境变量示例
├── config.example.yaml     # 应用配置示例
├── app/                    # 运行时、API、控制平面
├── core/                   # 核心引擎
├── llm/                    # LLM 适配器
├── scenarios/              # 场景插件
├── ui/                     # Streamlit UI
└── tests/                  # 测试套件
```

---

## 🐛 故障排除

### uv 安装失败
```bash
# 使用 pip 安装 uv
pip install uv
```

### Docker 权限问题
```bash
# Linux 用户需要加入 docker 组
sudo usermod -aG docker $USER
# 重新登录后生效
```

### 端口占用
```bash
# 如果 8000 或 8501 被占用，修改 docker-compose.yml 中的端口映射
# 例如："8080:8000" 将 API 映射到主机的 8080 端口
```

### LLM API 调用失败
```bash
# 检查环境变量是否正确设置
cat .env

# 测试 LLM 连接
python -c "
from llm.providers.litellm_provider import LiteLLMProvider
p = LiteLLMProvider(api_key='your-key')
print(p.complete('Hello'))
"
```

---

## 📚 更多信息

- [完整 README](README.md)
- [架构文档](dev_doc/architecture.md)
- [配置说明](dev_doc/configuration.md)
- [API 文档](dev_doc/api_reference.md)

---

## 💡 提示

1. **开发推荐**: 使用 `make dev-shell` 进入 Docker 开发容器，代码修改会实时同步
2. **生产部署**: 修改 `docker-compose.yml` 中的环境变量，使用外部 LLM API
3. **数据持久化**: 默认数据存储在 Docker volumes 中，重启不会丢失
4. **代码检查**: 运行 `make format` 和 `make lint` 保持代码规范（需安装 ruff）
