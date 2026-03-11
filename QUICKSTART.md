# RDAgent 快速开始

这份指南只保留当前 `main` 分支可直接执行的流程。

## 1. 安装依赖

推荐直接安装完整依赖：

```bash
git clone https://github.com/hapesc/my-RDagent.git
cd my-RDagent

uv venv
uv pip install -e ".[all]"
```

如果使用 `make`：

```bash
make install-all
```

说明：

- `make install` 只装核心包，不足以运行真实 LLM 流程
- `agentrd_cli.py`、`cli.py`、FastAPI 控制面都会经过 `build_runtime()`，因此需要 `litellm`

## 2. 准备配置

```bash
cp config.example.yaml config.yaml
python -m app.startup --config ./config.yaml
```

`app.startup` 只做配置加载和打印，不会真正构建运行时。

## 3. 配置真实 LLM Provider

当前源码中的测试 mock 不能作为正常运行时 fallback 使用。最小可运行配置：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-api-key
```

如果你要运行 `data_science` 场景但本机没有 Docker，再额外开启：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

## 4. 本地跑一个最小实验

最省事的是先跑 `synthetic_research`，因为它不依赖本地代码执行沙盒：

```bash
python agentrd_cli.py run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --loops-per-call 1 \
  --max-loops 1 \
  --input '{"task_summary":"write a short brief about evaluation benchmark failure modes","max_loops":1}'
```

如果要验证代码执行链路，再跑 `data_science`：

```bash
python cli.py \
  --config ./config.yaml \
  --scenario data_science \
  --task "classify iris dataset" \
  --max-steps 1
```

## 5. 查看结果

```bash
python agentrd_cli.py trace --run-id <RUN_ID> --format table
python agentrd_cli.py health-check --verbose
```

说明：

- `health-check` 也会构建运行时，所以同样需要真实 LLM provider 配置
- `trace --format json` 会返回完整事件、节点、artifact 列表

## 6. 启动控制面和 UI

```bash
uvicorn app.api_main:app --host 127.0.0.1 --port 8000
streamlit run ui/trace_ui.py
```

常用地址：

- API: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Trace UI: `http://127.0.0.1:8501`

## 7. Docker Compose

仓库里有 `docker-compose.yml` 和 `make quickstart`，但要注意两点：

- 仓库没有 `.env.example`
- `docker-compose.yml` 里的 `RD_AGENT_LLM_PROVIDER` 默认仍是 `mock`，因此你必须在启动前显式覆盖环境变量

示例：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-api-key

make quickstart
```

或直接：

```bash
docker-compose up -d api ui
```

如果你习惯使用 Compose 的 `.env` 文件，可以自行创建，但这不是仓库内置模板能力。

## 8. 量化场景说明

`quant` 场景已注册到插件系统，但默认 `build_runtime()` 没有注入 `QuantConfig.data_provider`，所以不能像 `data_science` 一样直接用默认 CLI 跑通。

要跑真实量化链路，请使用：

```bash
python scripts/run_quant_e2e.py
```

这个脚本会自行装配 `QuantConfig`、真实 LLM provider 和市场数据提供器。

## 9. 常见问题

### `Unknown or missing LLM provider: 'mock'`

说明你已经进入了真正的运行时入口，但还没把 `RD_AGENT_LLM_PROVIDER` 改成 `litellm`。

### `docker unavailable` 或执行后端降级

若没有 Docker，请显式设置：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

### `quant` 运行时报缺少 data provider

这是当前默认 runtime 的已知约束，不是配置文件漏项。请走 `scripts/run_quant_e2e.py` 或自定义 runtime 装配。
