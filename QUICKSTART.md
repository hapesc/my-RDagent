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
- `agentrd_cli.py` 和 FastAPI 控制面都会经过 `build_runtime()`，因此需要 `litellm`

## 2. 准备配置

```bash
cp config.example.yaml config.yaml
python -m app.startup --config ./config.yaml
```

`app.startup` 只做配置加载和打印，不会真正构建运行时。

推荐把稳定运行参数放到 `run_defaults`：

```yaml
run_defaults:
  scenario: data_science
  stop_conditions:
    max_loops: 1
    max_duration_sec: 300
  step_overrides:
    running:
      timeout_sec: 120
  entry_input:
    id_column: id
    label_column: label
```

## 3. 配置真实 LLM Provider

当前源码中的测试 mock 不能作为正常运行时 fallback 使用。最小可运行配置：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=openai/gpt-4o-mini
export RD_AGENT_LLM_API_KEY=your-api-key
```

如果你要使用 LiteLLM ChatGPT auth：

```bash
export RD_AGENT_LLM_PROVIDER=litellm
export RD_AGENT_LLM_MODEL=gpt-5
unset RD_AGENT_LLM_API_KEY
```

说明：

- 当 `RD_AGENT_LLM_PROVIDER=litellm`、`RD_AGENT_LLM_API_KEY` 为空，且模型为 `chatgpt/...` 或裸 `gpt-*` 时，runtime 会自动走 ChatGPT auth
- `openai/...` 在无 API key 时仍不会自动走 auth
- 第一次真实请求时，LiteLLM 会触发 ChatGPT device flow 登录

如果你要运行 `data_science` 场景但本机没有 Docker，再额外开启：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

## 4. 本地跑一个最小实验

最省事的是先跑 `synthetic_research`，因为它不依赖本地代码执行沙盒：

```bash
rdagent run --config ./config.yaml --scenario synthetic_research --task-summary "write a short brief about evaluation benchmark failure modes"
```

如果想显式指定研究主题：

```bash
rdagent run \
  --config ./config.yaml \
  --scenario synthetic_research \
  --input '{
    "task_summary":"write a short brief about evaluation benchmark failure modes",
    "reference_topics":["evaluation", "benchmarking", "failure analysis"],
    "max_loops":1
  }'
```

说明：

- `synthetic_research` 不依赖本地 CSV 或代码执行沙盒
- 它最适合先验证 LLM provider、trace、checkpoint 和控制面链路
- 输出通常是 `research_brief.md`、`research_summary.json` 一类文本结果

如果要验证代码执行链路，再跑 `data_science`：

```bash
rdagent run --config ./config.yaml --task-summary "classify iris dataset"
```

如果 `data_science` 要读取你自己的本地文件，优先用高频 CLI 参数覆盖：

```bash
rdagent run \
  --config ./config.yaml \
  --task-summary "classify local csv" \
  --data-source /absolute/path/to/train.csv
```

高级兼容写法仍然可用：

```bash
rdagent run \
  --config ./config.yaml \
  --scenario data_science \
  --input '{
    "task_summary":"classify local csv",
    "entry_input":{"data_source":"/absolute/path/to/train.csv"},
    "max_loops":1
  }'
```

说明：

- `data_source` 支持 `.csv`、`.jsonl`、`.ndjson`
- `id_column` / `label_column` / `train_ratio` / `test_ratio` / `split_seed` 可以一起传
- 当前默认 Docker 执行后端只挂载 workspace，不会自动挂载任意宿主机数据路径，所以本机文件路径在默认 Docker 路径下并不可靠
- 这类本地文件输入目前更适合在本地执行路径下使用，或者通过自定义 runtime/backend 处理数据挂载

## 5. 查看结果

```bash
rdagent trace --run-id <RUN_ID> --format table
rdagent health-check --verbose
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

`quant` 现在支持像 `data_science` 一样通过 `--data-source` 直接读取本地 OHLCV CSV：

```bash
rdagent run \
  --config ./config.yaml \
  --scenario quant \
  --task-summary "mine a momentum factor from local OHLCV data" \
  --data-source /absolute/path/to/ohlcv.csv
```

文件格式固定为：

```text
date,stock_id,open,high,low,close,volume
```

示例：

```csv
date,stock_id,open,high,low,close,volume
2021-07-01,AAPL,136.60,137.33,135.76,136.96,52485800
2021-07-01,MSFT,271.60,272.00,269.60,271.40,17887700
```

补充说明：

- 只支持这一种 CSV 结构，不做列名猜测
- 每行必须是一只股票在一个交易日的 OHLCV 记录
- `date` 要能解析成日期，其余价格/成交量列必须是数值

如果你想跑仓库自带的 yfinance 示例链路，也可以继续用：

```bash
python scripts/run_quant_e2e.py
```

这个脚本现在是一个薄包装器：

- 先用 `YFinanceDataProvider` 拉取 OHLCV
- 写入临时 CSV
- 再调用统一的 `agentrd run --scenario quant --data-source <temp.csv>`
- 结束后删除临时文件

它只暴露这些参数：

- `--tickers`
- `--start-date`
- `--end-date`
- `--task-summary`
- `--max-loops`

运行前建议准备：

```bash
export RD_AGENT_LLM_API_KEY=your-api-key
```

`scripts/run_quant_e2e.py` 会进一步读取它自己的测试 provider 配置，并通过 `yfinance` 拉取真实市场数据。

适用场景：

- `data_science`: 你有本地数据文件，想做实验型建模或指标产出
- `synthetic_research`: 你想生成 brief / findings / summary
- `quant`: 你想让模型提出因子并对真实市场数据做回测

## 9. 常见问题

### `cli.py is deprecated`

这是预期行为。运行入口已经收窄为 `rdagent run` / `python agentrd_cli.py run`。

### `Unknown or missing LLM provider: 'mock'`

说明你已经进入了真正的运行时入口，但还没把 `RD_AGENT_LLM_PROVIDER` 改成 `litellm`。

### `docker unavailable` 或执行后端降级

若没有 Docker，请显式设置：

```bash
export AGENTRD_ALLOW_LOCAL_EXECUTION=1
```

### `quant` 本地文件报格式错误

优先检查 CSV 是否严格包含：

```text
date,stock_id,open,high,low,close,volume
```
