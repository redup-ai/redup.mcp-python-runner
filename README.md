# redup.mcp-python-runner

![Docker test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/docker-test.yml/badge.svg?branch=master)
![Python test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/python-test.yml/badge.svg?branch=master)

MCP Streamable HTTP service for sandboxed ephemeral Python execution: scripts run
with inline dependencies ([PEP 723](https://peps.python.org/pep-0723/)) via
[`uv`](https://docs.astral.sh/uv/), without polluting the host environment.

Contract: MCP tools `execute_python`, `check_environment`, `validate_script`.
Transport: Streamable HTTP on `/mcp` (stateless, JSON responses).

## Configuration

Service defaults (override with env):

| Env | Default | Description |
|-----|---------|-------------|
| `LISTEN_ADDRESS` / `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` / `MCP_PORT` | `8000` | Bind port |
| `MCP_PATH` | `/mcp` | Streamable HTTP path |
| `SANDBOX_BACKEND` | `native` | `native` (bubblewrap on Linux) or `none` |
| `PYTHON_VERSION` | `3.13` | Python version for executed scripts |
| `DEFAULT_TIMEOUT` | `30` | Default `execute_python` timeout (seconds) |
| `MAX_TIMEOUT` | `300` | Maximum allowed timeout |

`native` needs [bubblewrap](https://github.com/containers/bubblewrap) and user
namespaces. If that is unavailable (typical constrained Kubernetes), set
`SANDBOX_BACKEND=none` — isolation is then the container only.

CLI flags mirror the same options (`--host`, `--port`, `--path`,
`--sandbox-backend`, …). Use `--transport stdio` for desktop MCP clients.

## Run with Docker

```bash
docker run --rm -p 8000:8000 \
  redup4ai/redup.mcp-python-runner:0.1.0-3.13-slim
```

The service listens for MCP Streamable HTTP on port **8000** at `/mcp`.

Smoke with the MCP inspector:

```bash
npx -y @modelcontextprotocol/inspector
# URL: http://127.0.0.1:8000/mcp
```

Or call `initialize` with curl:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.1"}}}'
```

## Run locally without Docker

Requires Python 3.13+, [`uv`](https://docs.astral.sh/uv/), and on Linux
`bubblewrap` for `SANDBOX_BACKEND=native`:

```bash
sudo apt-get install -y bubblewrap
uv sync
uv run redup-mcp-python-runner --host 127.0.0.1 --port 8000
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
