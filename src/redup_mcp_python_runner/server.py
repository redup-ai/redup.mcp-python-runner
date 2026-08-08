"""FastMCP server with tool definitions."""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from redup_mcp_python_runner.config import ServerConfig
from redup_mcp_python_runner.executor import execute
from redup_mcp_python_runner.metrics import tracked_work
from redup_mcp_python_runner.output import format_result
from redup_mcp_python_runner.sandbox import get_sandbox
from redup_mcp_python_runner.script import build_script, extract_metadata

_CodeArg = Annotated[
    str,
    Field(description="Python source code to run (or validate)."),
]
_DepsArg = Annotated[
    list[str] | None,
    Field(
        default=None,
        description='Optional pip deps, e.g. ["matplotlib>=3.8", "numpy"]. '
        "Prefer PEP 723 # /// script blocks inside code when many deps.",
    ),
]
_TimeoutArg = Annotated[
    int,
    Field(description="Max execution time in seconds (clamped to server max)."),
]


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Server lifespan: initialize sandbox, optionally warm cache."""
    config: ServerConfig = server._mcp_config  # type: ignore[attr-defined]
    sandbox = get_sandbox(config.sandbox_backend)

    ctx = {
        "config": config,
        "sandbox": sandbox,
    }

    # Warm cache in background (non-blocking)
    if config.warm_cache:
        from redup_mcp_python_runner.cache import warm_cache

        asyncio.create_task(
            warm_cache(uv_path=config.uv_path, python_version=config.python_version)
        )

    yield ctx


def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""

    # Verify uv is available
    uv_path = shutil.which(config.uv_path) or config.uv_path
    try:
        result = subprocess.run([uv_path, "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise RuntimeError("uv returned non-zero exit code")
    except FileNotFoundError as err:
        raise RuntimeError(
            f"uv not found at '{config.uv_path}'. "
            "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
        ) from err

    mcp = FastMCP(
        "redup-mcp-python-runner",
        lifespan=_lifespan,
    )
    mcp._mcp_config = config  # type: ignore[attr-defined]

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": True,
        }
    )
    async def execute_python(
        code: _CodeArg,
        dependencies: _DepsArg = None,
        timeout: _TimeoutArg = config.default_timeout,
    ) -> str:
        """Run Python code in an ephemeral sandbox (uv + optional deps).

        Workspace files are discarded after the call — only stdout/stderr return.
        To produce a binary (PNG/PDF/…), write it in-memory and print base64 on stdout
        (or keep output small; large stdout may be truncated by the server).

        Args: ``code`` (required), ``timeout`` (seconds), ``dependencies`` (optional list).
        """
        async with tracked_work("execute_python"):
            # Clamp timeout
            clamped = max(1, min(int(timeout), config.max_timeout))

            # Build script with merged metadata
            final_script = build_script(
                code, extra_dependencies=dependencies, python_version=config.python_version
            )

            # Write to temp file and execute
            with tempfile.TemporaryDirectory(prefix="mcp-py-") as tmpdir:
                script_path = Path(tmpdir) / "script.py"
                script_path.write_text(final_script, encoding="utf-8")

                sandbox = get_sandbox(config.sandbox_backend)

                result = await execute(
                    script_path=script_path,
                    python_version=config.python_version,
                    timeout=clamped,
                    sandbox=sandbox,
                    max_output_bytes=config.max_output_bytes,
                    uv_path=config.uv_path,
                )

            return format_result(result, config.max_output_bytes)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def check_environment() -> str:
        """Check the execution environment and report status.

        Returns information about Python version, uv version, platform,
        sandbox configuration, and cache status.
        """
        async with tracked_work("check_environment"):
            sandbox = get_sandbox(config.sandbox_backend)

            # Get uv version
            try:
                result = subprocess.run(
                    [config.uv_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                uv_version = result.stdout.strip()
            except Exception:
                uv_version = "unknown"

            lines = [
                f"Python version: {config.python_version}",
                f"uv: {uv_version}",
                f"Platform: {platform.system()} {platform.machine()}",
                f"Sandbox backend: {config.sandbox_backend}",
                f"Sandbox status: {sandbox.describe()}",
                f"Default timeout: {config.default_timeout}s",
                f"Max timeout: {config.max_timeout}s",
                f"Max output: {config.max_output_bytes} bytes",
                f"Cache warming: {'enabled' if config.warm_cache else 'disabled'}",
            ]
            return "\n".join(lines)

    @mcp.tool(
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def validate_code(
        code: _CodeArg,
        dependencies: _DepsArg = None,
    ) -> str:
        """Validate Python code metadata/deps without executing (PEP 723 / pip specs).

        Same ``code`` / ``dependencies`` args as execute_python.
        """
        async with tracked_work("validate_code"):
            issues: list[str] = []

            # Try to parse existing metadata
            try:
                extract_metadata(code)
            except Exception as exc:
                return f"INVALID: {exc}"

            # Try to build merged script
            try:
                merged = build_script(
                    code,
                    extra_dependencies=dependencies,
                    python_version=config.python_version,
                )
            except Exception as exc:
                return f"INVALID: Failed to merge metadata: {exc}"

            # Extract final metadata for reporting
            final_meta = extract_metadata(merged)

            lines = ["VALID"]
            if final_meta.get("requires-python"):
                lines.append(f"requires-python: {final_meta['requires-python']}")
            deps = final_meta.get("dependencies", [])
            if deps:
                lines.append(f"dependencies ({len(deps)}):")
                for dep in deps:
                    lines.append(f"  - {dep}")
            else:
                lines.append("dependencies: none")
            if issues:
                lines.append("warnings:")
                for issue in issues:
                    lines.append(f"  - {issue}")

            return "\n".join(lines)

    return mcp
