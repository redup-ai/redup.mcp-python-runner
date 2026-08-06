# redup.mcp-python-runner

![Docker test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/docker-test.yml/badge.svg?branch=master)
![Python test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/python-test.yml/badge.svg?branch=master)

MCP Streamable HTTP service for ephemeral Python execution. Scripts run with
inline dependencies ([PEP 723](https://peps.python.org/pep-0723/)) via
[`uv`](https://docs.astral.sh/uv/).

Contract: MCP tools `execute_python`, `check_environment`, `validate_script`.
Endpoint: `POST http://<host>:8000/mcp` (stateless Streamable HTTP, JSON).

## Configuration

Image / service defaults (override with env):

```text
LISTEN_ADDRESS=0.0.0.0
APP_PORT=8000
MCP_PATH=/mcp
MCP_STATELESS_HTTP=true
MCP_JSON_RESPONSE=true
SANDBOX_BACKEND=none          # container isolation; or native (bubblewrap)
PYTHON_VERSION=3.13
DEFAULT_TIMEOUT=30
MAX_TIMEOUT=300
WARM_CACHE=true               # pre-fetch common wheels into uv cache
UV_CACHE_DIR=/var/cache/uv
```

`SANDBOX_BACKEND=native` needs bubblewrap and unprivileged user namespaces.
Without that, keep `none` (typical Docker / Kubernetes).

CLI mirrors the same options (`--host`, `--port`, `--path`, `--sandbox-backend`,
`--no-warm-cache`, …). Use `--transport stdio` for desktop MCP clients.

## Run with Docker

```bash
docker run --rm -p 8000:8000 \
  redup4ai/redup.mcp-python-runner:0.1.0-3.13-slim
```

MCP URL: `http://127.0.0.1:8000/mcp`.

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
uv run redup-mcp-python-runner --host 127.0.0.1 --port 8000
```

On Linux, optional tighter isolation:

```bash
sudo apt-get install -y bubblewrap
uv run redup-mcp-python-runner --sandbox-backend native --host 127.0.0.1 --port 8000
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
