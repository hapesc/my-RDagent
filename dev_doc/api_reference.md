# Control Plane API Reference

当前控制面由 `app/control_plane.py` 提供，接口列表如下。命令行运行入口统一为 `rdagent run` / `python agentrd_cli.py run`，不再推荐 `cli.py`。

- `POST /runs`
- `GET /runs/{run_id}`
- `POST /runs/{run_id}/pause`
- `POST /runs/{run_id}/resume`
- `POST /runs/{run_id}/stop`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/branches`
- `GET /scenarios`
- `GET /health`

## `POST /runs`

请求体：

```json
{
  "scenario": "synthetic_research",
  "task_summary": "summarize evaluation benchmark trends",
  "run_id": "optional-run-id",
  "entry_input": {
    "reference_topics": ["benchmarks", "evaluation"]
  },
  "stop_conditions": {
    "max_loops": 1,
    "max_steps": null,
    "max_duration_sec": 300
  },
  "step_overrides": {
    "proposal": {
      "provider": "litellm",
      "model": "openai/gpt-4o-mini",
      "max_retries": 1
    },
    "coding": {},
    "running": {
      "timeout_sec": 120
    },
    "feedback": {}
  }
}
```

说明：

- `scenario` 和 `task_summary` 必填
- 也支持把 `max_loops`、`max_duration_sec` 放在顶层，`RunCreateRequest.from_dict()` 会兼容读取
- `step_overrides` 只允许 `proposal`、`coding`、`running`、`feedback`
- 除保留字段外，顶层其他键会被透传到 `entry_input`

### `data_science` file input

`data_science` 场景读取文件时，推荐直接把 `data_source` 放在顶层请求体，CLI 会把它透传到 `entry_input`：

```json
{
  "scenario": "data_science",
  "task_summary": "classify local csv",
  "data_source": "/absolute/path/to/train.csv",
  "id_column": "id",
  "label_column": "label",
  "stop_conditions": {
    "max_loops": 1,
    "max_duration_sec": 300
  }
}
```

等价写法：

```json
{
  "scenario": "data_science",
  "task_summary": "classify local csv",
  "entry_input": {
    "data_source": "/absolute/path/to/train.csv",
    "id_column": "id",
    "label_column": "label"
  },
  "stop_conditions": {
    "max_loops": 1,
    "max_duration_sec": 300
  }
}
```

当前约束：

- `data_source` 仅在场景代码里作为路径字符串读取，不是文件上传接口
- split-manifest 推断支持 `.csv`、`.jsonl`、`.ndjson`
- 默认 Docker 执行后端只挂载 workspace，不自动挂载任意宿主机文件路径，因此本地绝对路径在默认 Docker 路径下并不可靠

响应体是 `RunSummaryResponse`：

```json
{
  "run_id": "run-123",
  "scenario": "synthetic_research",
  "status": "RUNNING",
  "active_branch_ids": ["main"],
  "created_at": "2026-03-11T12:00:00Z",
  "updated_at": "2026-03-11T12:00:01Z",
  "stop_conditions": {
    "max_loops": 1,
    "max_steps": null,
    "max_duration_sec": 300
  },
  "config_snapshot": {
    "runtime": {
      "llm_provider": "litellm",
      "llm_model": "openai/gpt-4o-mini",
      "uses_real_llm_provider": true,
      "sandbox_timeout_sec": 120,
      "allow_local_execution": true,
      "default_scenario": "data_science",
      "real_provider_safe_profile": {
        "layer0_n_candidates": 1,
        "layer0_k_forward": 1,
        "costeer_max_rounds": 1,
        "sandbox_timeout_sec": 120,
        "max_retries": 1
      },
      "guardrail_warnings": []
    }
  }
}
```

## Run Control Endpoints

`POST /runs/{run_id}/pause`

`POST /runs/{run_id}/resume`

`POST /runs/{run_id}/stop`

统一返回：

```json
{
  "run_id": "run-123",
  "action": "pause",
  "status": "PAUSED",
  "message": "pause requested"
}
```

`resume` 的 `message` 为 `resume scheduled`，`stop` 的 `message` 为 `stop requested`。

## `GET /runs/{run_id}`

返回和 `POST /runs` 相同结构的 `RunSummaryResponse`。

## `GET /runs/{run_id}/events`

查询参数：

- `cursor` 可选
- `limit` 可选，默认 `50`
- `branch_id` 可选

响应：

```json
{
  "run_id": "run-123",
  "items": [],
  "next_cursor": null,
  "limit": 50
}
```

## `GET /runs/{run_id}/artifacts`

可选查询参数：

- `branch_id`

响应：

```json
{
  "run_id": "run-123",
  "items": [
    {
      "path": "/tmp/rd_agent_workspace/run-123/loop-0000/pipeline.py",
      "branch_id": null
    }
  ]
}
```

## `GET /runs/{run_id}/branches`

响应：

```json
{
  "run_id": "run-123",
  "items": [
    {
      "branch_id": "main",
      "head_node_id": "node-run-123-main-0"
    }
  ]
}
```

## `GET /scenarios`

返回已注册 manifest 列表。当前默认 registry 包含：

- `data_science`
- `synthetic_research`
- `quant`

注意：`quant` 虽然会出现在这里，但默认 runtime 没有注入 market data provider。

## `GET /health`

`/health` 会构建真实 runtime，然后返回：

```json
{
  "status": "ok",
  "checks": {
    "sqlite": "ok",
    "artifact_root": "ok",
    "execution_backend": "ok",
    "llm_adapter": "ok"
  },
  "details": {
    "docker_available": true,
    "allow_local_execution": false,
    "registered_scenarios": ["data_science", "synthetic_research", "quant"]
  }
}
```

因此 `/health` 也依赖真实 LLM provider 配置，而不是纯静态检查。
