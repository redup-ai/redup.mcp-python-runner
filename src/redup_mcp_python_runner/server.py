"""FastMCP server with tool definitions."""

from __future__ import annotations

import ast
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
from redup_mcp_python_runner.errors import ScriptMetadataError
from redup_mcp_python_runner.executor import execute, resolve_runtime_python
from redup_mcp_python_runner.metrics import tracked_work
from redup_mcp_python_runner.output import ExecutionResult, format_result
from redup_mcp_python_runner.packages import load_package_list
from redup_mcp_python_runner.sandbox import get_sandbox
from redup_mcp_python_runner.script import extract_metadata, prepare_script

_CodeArg = Annotated[
    str,
    Field(description="Python source code to run (or validate)."),
]
_TimeoutArg = Annotated[
    int,
    Field(description="Max execution time in seconds (clamped to server max)."),
]


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """Server lifespan: initialize sandbox (no package downloads)."""
    config: ServerConfig = server._mcp_config  # type: ignore[attr-defined]
    sandbox = get_sandbox(config.sandbox_backend)
    yield {
        "config": config,
        "sandbox": sandbox,
        "runtime_python": resolve_runtime_python(config.runtime_python or None),
        "packages": load_package_list(config.packages_file or None),
    }


def create_server(config: ServerConfig) -> FastMCP:
    """Create and configure the MCP server with all tools."""

    mcp = FastMCP(
        "redup-mcp-python-runner",
        lifespan=_lifespan,
    )
    mcp._mcp_config = config  # type: ignore[attr-defined]

    @mcp.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": False,
        }
    )
    async def execute_python(
        code: _CodeArg,
        timeout: _TimeoutArg = config.default_timeout,
    ) -> str:
        """Run Python in an offline sandbox (no network, no package install).

        Only preinstalled packages are available (see ``check_environment``).
        Do not pass pip/uv/PEP 723 dependencies — they are rejected.

        To return a binary (PNG/PDF/…), write it under ``ARTIFACTS_DIR``
        (env var in the process), e.g.::

            from pathlib import Path
            import os
            Path(os.environ["ARTIFACTS_DIR"], "chart.png").write_bytes(png_bytes)

        The tool returns JSON: stdout, stderr, exit_code, duration_ms, timed_out,
        artifacts[{path, media_type, size, content_base64}].

        Args: ``code`` (required), ``timeout`` (seconds).
        """
        async with tracked_work("execute_python"):
            clamped = max(1, min(int(timeout), config.max_timeout))
            try:
                final_script = prepare_script(code)
            except ScriptMetadataError as exc:
                return format_result(
                    ExecutionResult(
                        stdout="",
                        stderr=str(exc),
                        exit_code=2,
                        duration_ms=0,
                        timed_out=False,
                        artifacts=[],
                    ),
                    config.max_output_bytes,
                )

            with tempfile.TemporaryDirectory(prefix="mcp-py-") as tmpdir:
                work = Path(tmpdir)
                script_path = work / "script.py"
                script_path.write_text(final_script, encoding="utf-8")
                (work / "artifacts").mkdir(exist_ok=True)

                sandbox = get_sandbox(config.sandbox_backend)
                result = await execute(
                    script_path=script_path,
                    timeout=clamped,
                    sandbox=sandbox,
                    max_output_bytes=config.max_output_bytes,
                    runtime_python=config.runtime_python or None,
                    max_artifact_bytes=config.max_artifact_bytes,
                    max_artifacts_total_bytes=config.max_artifacts_total_bytes,
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
        """Report offline sandbox status and the preinstalled package allowlist."""
        async with tracked_work("check_environment"):
            sandbox = get_sandbox(config.sandbox_backend)
            runtime = resolve_runtime_python(config.runtime_python or None)
            packages = load_package_list(config.packages_file or None)

            uv_version = "n/a (not used for execution)"
            if shutil.which(config.uv_path):
                try:
                    result = subprocess.run(
                        [config.uv_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        uv_version = result.stdout.strip()
                except Exception:
                    pass

            lines = [
                f"Python version (config): {config.python_version}",
                f"Runtime interpreter: {runtime}",
                f"uv (diagnostic only): {uv_version}",
                f"Platform: {platform.system()} {platform.machine()}",
                f"Sandbox backend: {config.sandbox_backend}",
                f"Sandbox status: {sandbox.describe()}",
                "Network: disabled (no package install, no egress in native sandbox)",
                f"Default timeout: {config.default_timeout}s",
                f"Max timeout: {config.max_timeout}s",
                f"Max stdout/stderr: {config.max_output_bytes} bytes",
                f"Max artifact file: {config.max_artifact_bytes} bytes",
                "Preinstalled packages (import these only):",
            ]
            for name in packages:
                lines.append(f"  - {name}")
            lines.append(
                "Write binaries to ARTIFACTS_DIR; they return in JSON field artifacts[]."
            )
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
    ) -> str:
        """Validate Python syntax and reject inline dependency metadata (offline policy)."""
        async with tracked_work("validate_code"):
            try:
                meta = extract_metadata(code)
            except Exception as exc:
                return f"INVALID: {exc}"

            deps = meta.get("dependencies") or []
            if deps:
                return (
                    "INVALID: inline dependencies are not allowed "
                    f"(rejected: {deps}). Use preinstalled packages only."
                )

            try:
                body = prepare_script(code)
            except ScriptMetadataError as exc:
                return f"INVALID: {exc}"

            try:
                ast.parse(body)
            except SyntaxError as exc:
                return f"INVALID: syntax error: {exc}"

            packages = load_package_list(config.packages_file or None)
            lines = [
                "VALID",
                "policy: offline sandbox (no runtime installs)",
                f"preinstalled_packages ({len(packages)}): {', '.join(packages)}",
            ]
            return "\n".join(lines)

    return mcp
