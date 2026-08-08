# redup.mcp-python-runner

![Docker test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/docker-test.yml/badge.svg?branch=master)
![Python test](https://github.com/redup-ai/redup.mcp-python-runner/actions/workflows/python-test.yml/badge.svg?branch=master)

MCP Streamable HTTP service for **offline** ephemeral Python execution.

## Security model

- **No runtime package installs** — no `uv run --script` dependency resolution,
  no `dependencies` tool arg, PEP 723 `dependencies = [...]` is **rejected**.
- Allowlisted packages are installed **only at image build time** into
  `/opt/code-tools-env` (see `packages.txt`).
- **Offline execution** (`sandbox_backend: native`): each script runs under
  `unshare --net --pid --fork --mount-proc` (empty netns + private `/proc`).
  Requires **`CAP_SYS_ADMIN`**. Also deploy a **NetworkPolicy deny-egress** on
  the pod (see helm `extraDeploy`) so CNI blocks egress even if netns is joined.
- Tool results are **JSON** (`stdout` / `stderr` / `exit_code` / `artifacts`),
  not a concatenated text dump.

### Docker run (local)

```bash
docker run --rm -p 8000:8000 -p 9999:9999 \
  --cap-add SYS_ADMIN \
  mcp-python:test
```

`CAP_SYS_ADMIN` is enough for `unshare --net`. Full bubblewrap `--unshare-all`
would need `--privileged` on most hosts — we intentionally use `unshare --net`
instead.

### Kubernetes

Chart sets `deployment.securityContext.capabilities.add: [SYS_ADMIN, …]` and
`sandbox_backend: native`. Also add a **NetworkPolicy deny-egress** on the
code-tools pods as defense in depth.

Contract: MCP tools `execute_python`, `check_environment`, `validate_code`.
Endpoint: `POST http://<host>:8000/mcp` (stateless Streamable HTTP, JSON).
Metrics: `GET http://<host>:9999/metrics` (Prometheus via `redup-servicekit`).

**Tool args:** `execute_python` / `validate_code` take **`code`** (required);
`execute_python` also takes **`timeout`** (seconds). There is **no**
`dependencies` argument.

**Binaries:** write files under `ARTIFACTS_DIR` (set in the process env). They
are returned in the JSON `artifacts[]` field as `content_base64`. Do not paste
raw tool transcripts into `create_file`.

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
  sandbox_backend: native        # unshare --net; needs CAP_SYS_ADMIN
  python_version: "3.13"
  runtime_python: "/opt/code-tools-env/bin/python"
  packages_file: "/config/packages.txt"
  default_timeout: 30
  max_timeout: 300
  max_output_bytes: 1048576
  max_artifact_bytes: 5242880
  max_artifacts_total_bytes: 10485760
  json_response: true
  stateless_http: true
```

Override via servicekit env substitution (`section___key`):

```bash
export McpPythonRunner___sandbox_backend=native
export McpPythonRunner___runtime_python=/opt/code-tools-env/bin/python
export service___port=8000
```

`sandbox_backend=native` needs `CAP_SYS_ADMIN` (see Docker run / Helm
`securityContext` above). If the capability is missing, `unshare --net` fails
and tool calls return a non-zero exit — fix the securityContext, do not silently
fall back to networked execution.

## Run with Docker

```bash
docker run --rm -p 8000:8000 -p 9999:9999 \
  redup4ai/redup.mcp-python-runner:0.1.0-3.13-slim
```

MCP URL: `http://127.0.0.1:8000/mcp`. Metrics: `http://127.0.0.1:9999/metrics`.

## Run locally without Docker

Requires Python 3.13+ and a preinstalled scientific stack (or point
`--runtime-python` at a venv that already has `packages.txt` installed):

```bash
uv sync
uv run python -m redup_mcp_python_runner.service config/config.yaml
```

Desktop MCP clients (stdio):

```bash
uv run redup-mcp-python-runner --transport stdio --sandbox-backend none
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
