# redup.mcp-python-runner

![Docker test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/docker-test.yml/badge.svg?branch=master)
![Python test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/python-test.yml/badge.svg?branch=master)

MCP Streamable HTTP service for ephemeral Python execution. Scripts run with
inline dependencies ([PEP 723](https://peps.python.org/pep-0723/)) via
[`uv`](https://docs.astral.sh/uv/).

Contract: MCP tools `execute_python`, `check_environment`, `validate_script`.
Endpoint: `POST http://<host>:8000/mcp` (stateless Streamable HTTP, JSON).
Metrics: `GET http://<host>:9999/metrics` (Prometheus via `redup-servicekit`).

## Configuration

`config/config.yaml`:

```yaml
service:
  console_log_level: INFO
  host: "0.0.0.0"
  port: 8000
  path: /mcp
  max_workers: 4
  hpa_max_workers: 2

McpPythonRunner:
  sandbox_backend: none          # or native (bubblewrap + user namespaces)
  python_version: "3.13"
  default_timeout: 30
  max_timeout: 300
  max_output_bytes: 102400
  warm_cache: true
  uv_path: uv
  json_response: true
  stateless_http: true
```

Override without editing the file via servicekit env substitution (`section___key`):

```bash
export McpPythonRunner___sandbox_backend=none
export McpPythonRunner___warm_cache=false
export service___port=8000
```

`McpPythonRunner.sandbox_backend=native` needs bubblewrap and unprivileged user
namespaces. The image defaults to `none` (isolation = container).

## Run with Docker

```bash
docker run --rm -p 8000:8000 -p 9999:9999 \
  redup4ai/redup.mcp-python-runner:0.1.0-3.13-slim
```

MCP URL: `http://127.0.0.1:8000/mcp`. Metrics: `http://127.0.0.1:9999/metrics`.

Smoke with the MCP inspector:

```bash
npx -y @modelcontextprotocol/inspector
# URL: http://127.0.0.1:8000/mcp
```

Or:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.1"}}}'
```

## Run locally without Docker

Requires Python 3.13+ and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python -m redup_mcp_python_runner.service config/config.yaml
```

Desktop MCP clients (stdio, no MonitorServer):

```bash
uv run redup-mcp-python-runner --transport stdio
```

## Tests

```bash
uv sync --dev
uv run pytest tests -q
```

## License

MIT — see `LICENSE`.

Derived from [mcp-python-exec-sandbox](https://github.com/lu-zhengda/mcp-python-exec-sandbox)
(Copyright (c) 2025 mcp-python-executor contributors), MIT. See `NOTICE`.
