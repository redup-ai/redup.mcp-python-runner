"""CLI entry point for redup-mcp-python-runner."""

from __future__ import annotations

import argparse
import os
import sys


def _default_sandbox_backend() -> str:
    """Return the platform-appropriate default sandbox backend."""
    return "native" if sys.platform == "linux" else "none"


def _env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip() != "":
            return value
    return default


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_backend = _env_first("SANDBOX_BACKEND", default=_default_sandbox_backend())
    parser = argparse.ArgumentParser(
        prog="redup-mcp-python-runner",
        description="MCP Streamable HTTP service for sandboxed ephemeral Python execution",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default=_env_first("MCP_TRANSPORT", "FASTMCP_TRANSPORT", default="http"),
        help="MCP transport (default: http / streamable HTTP)",
    )
    parser.add_argument(
        "--host",
        default=_env_first(
            "LISTEN_ADDRESS", "APP_HOST", "FASTMCP_HOST", default="0.0.0.0"
        ),
        help="Bind address for HTTP transports (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            _env_first("MCP_PORT", "APP_PORT", "FASTMCP_PORT", default="8000") or "8000"
        ),
        help="Bind port for HTTP transports (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default=_env_first("MCP_PATH", "FASTMCP_STREAMABLE_HTTP_PATH", default="/mcp"),
        help="URL path for Streamable HTTP (default: /mcp)",
    )
    parser.add_argument(
        "--python-version",
        default=_env_first("PYTHON_VERSION", default="3.13"),
        help="Python version for script execution (default: 3.13)",
    )
    parser.add_argument(
        "--sandbox-backend",
        choices=["native", "none"],
        default=default_backend,
        help=(
            "Sandbox backend: native (bwrap, Linux only) or none "
            f"(default: {default_backend})"
        ),
    )
    parser.add_argument(
        "--max-timeout",
        type=int,
        default=int(_env_first("MAX_TIMEOUT", default="300") or "300"),
        help="Maximum allowed timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--default-timeout",
        type=int,
        default=int(_env_first("DEFAULT_TIMEOUT", default="30") or "30"),
        help="Default timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=int(_env_first("MAX_OUTPUT_BYTES", default="102400") or "102400"),
        help="Maximum output size in bytes (default: 102400)",
    )
    parser.add_argument(
        "--no-warm-cache",
        action="store_true",
        default=None,
        help="Skip cache warming on startup (or set WARM_CACHE=false)",
    )
    parser.add_argument(
        "--uv-path",
        default=_env_first("UV_PATH", default="uv"),
        help="Path to uv binary (default: uv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    from redup_mcp_python_runner.config import ServerConfig, _env_bool
    from redup_mcp_python_runner.server import create_server

    transport = args.transport
    if transport == "http":
        # Alias used by FastMCP / company MCP services
        transport = "streamable-http"

    if args.no_warm_cache:
        warm_cache = False
    else:
        warm_cache = _env_bool("WARM_CACHE", True)

    config = ServerConfig(
        python_version=args.python_version,
        sandbox_backend=args.sandbox_backend,
        max_timeout=args.max_timeout,
        default_timeout=args.default_timeout,
        max_output_bytes=args.max_output_bytes,
        warm_cache=warm_cache,
        uv_path=args.uv_path,
        transport=transport,
        host=args.host,
        port=args.port,
        path=args.path,
    )

    server = create_server(config)

    if transport == "stdio":
        server.run(transport="stdio")
        return

    server.run(
        transport=transport,
        host=config.host,
        port=config.port,
        path=config.path,
        json_response=config.json_response,
        stateless_http=config.stateless_http,
    )


if __name__ == "__main__":
    main()
