"""CLI entry point for local / desktop MCP (stdio or ad-hoc HTTP).

Docker / Kubernetes use ``python -m redup_mcp_python_runner.service /config/config.yaml``.
"""

from __future__ import annotations

import argparse
import sys


def _default_sandbox_backend() -> str:
    """Return the platform-appropriate default sandbox backend."""
    return "native" if sys.platform == "linux" else "none"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_backend = _default_sandbox_backend()
    parser = argparse.ArgumentParser(
        prog="redup-mcp-python-runner",
        description=(
            "MCP Python runner (local CLI, offline sandbox). "
            "For production HTTP use: python -m redup_mcp_python_runner.service CONFIG.yaml"
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport (default: stdio for desktop clients)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address for HTTP transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP transports (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="URL path for Streamable HTTP (default: /mcp)",
    )
    parser.add_argument(
        "--python-version",
        default="3.13",
        help="Python version label for diagnostics (default: 3.13)",
    )
    parser.add_argument(
        "--runtime-python",
        default="",
        help="Preinstalled interpreter path (default: CODE_TOOLS_PYTHON or sys.executable)",
    )
    parser.add_argument(
        "--packages-file",
        default="",
        help="Path to packages.txt allowlist",
    )
    parser.add_argument(
        "--sandbox-backend",
        choices=["native", "none"],
        default=default_backend,
        help=(
            "Sandbox backend: native (bwrap offline, Linux only) or none "
            f"(default: {default_backend})"
        ),
    )
    parser.add_argument(
        "--max-timeout",
        type=int,
        default=300,
        help="Maximum allowed timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--default-timeout",
        type=int,
        default=30,
        help="Default timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=1_048_576,
        help="Maximum stdout/stderr size in bytes (default: 1048576)",
    )
    parser.add_argument(
        "--no-warm-cache",
        action="store_true",
        help="Ignored (kept for CLI compat); runtime installs are disabled",
    )
    parser.add_argument(
        "--uv-path",
        default="uv",
        help="Path to uv binary for diagnostics only (default: uv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    from redup_mcp_python_runner.config import ServerConfig
    from redup_mcp_python_runner.server import create_server

    transport = args.transport
    if transport == "http":
        transport = "streamable-http"

    config = ServerConfig(
        python_version=args.python_version,
        sandbox_backend=args.sandbox_backend,
        max_timeout=args.max_timeout,
        default_timeout=args.default_timeout,
        max_output_bytes=args.max_output_bytes,
        runtime_python=args.runtime_python,
        packages_file=args.packages_file,
        warm_cache=False,
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
