"""FastMCP server with tool definitions."""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP

from redup_mcp_python_runner.config import ServerConfig
from redup_mcp_python_runner.executor import execute
from redup_mcp_python_runner.metrics import tracked_work
from redup_mcp_python_runner.output import format_result
from redup_mcp_python_runner.sandbox import get_sandbox
from redup_mcp_python_runner.script import build_script, extract_metadata


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

    @mcp.tool
    async def execute_python(
        script: str,
        dependencies: list[str] | None = None,
        timeout_seconds: int = config.default_timeout,
    ) -> str:
        """Execute a Python script with automatic dependency management.

        The script can include PEP 723 inline metadata (# /// script blocks)
        for declaring dependencies. Additional dependencies can also be passed
        via the dependencies parameter and will be merged.

        Args:
            script: Python source code to execute. May include PEP 723 metadata.
            dependencies: Extra PEP 508 dependency specifiers to make available.
            timeout_seconds: Maximum execution time (1-300, default 30).

        Returns:
            Formatted output with stdout, stderr, exit code, and duration.

        Example - simple script:

            execute_python(script="print('hello')")

        Example - with dependencies parameter:

            execute_python(
                script="import requests; print(requests.get('https://example.com').status_code)",
                dependencies=["requests>=2.32"]
            )

        Example - with inline dependency metadata (preferred for multiple deps):

            execute_python(script='''
            # /// script
            # dependencies = ["pandas>=2.2", "numpy>=1.26"]
            # ///

            import pandas as pd
            import numpy as np
            print(pd.DataFrame({"a": np.arange(5)}).describe())
            ''')

        Always pin dependency versions (e.g. "pandas>=2.2" instead of "pandas") for
        reproducible results.

        The inline metadata block (# /// script ... # ///) is the recommended way to
        declare dependencies directly in the script (see PEP 723:
        https://peps.python.org/pep-0723/). The dependencies parameter is a simpler
        alternative when you just need to add a few packages. Both accept standard
        pip-style version specifiers like "requests>=2.28" or "pandas" (see PEP 508:
        https://peps.python.org/pep-0508/).
        """
        async with tracked_work("execute_python"):
            # Clamp timeout
            timeout = max(1, min(timeout_seconds, config.max_timeout))

            # Build script with merged metadata
            final_script = build_script(
                script, extra_dependencies=dependencies, python_version=config.python_version
            )

            # Write to temp file and execute
            with tempfile.TemporaryDirectory(prefix="mcp-py-") as tmpdir:
                script_path = Path(tmpdir) / "script.py"
                script_path.write_text(final_script, encoding="utf-8")

                sandbox = get_sandbox(config.sandbox_backend)

                result = await execute(
                    script_path=script_path,
                    python_version=config.python_version,
                    timeout=timeout,
                    sandbox=sandbox,
                    max_output_bytes=config.max_output_bytes,
                    uv_path=config.uv_path,
                )

            return format_result(result, config.max_output_bytes)

    @mcp.tool
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

    @mcp.tool
    async def validate_script(
        script: str,
        dependencies: list[str] | None = None,
    ) -> str:
        """Validate a Python script's PEP 723 metadata and dependencies without executing it.

        Checks metadata syntax, dependency format, and requires-python compatibility.

        Args:
            script: Python source code to validate. May include inline dependency
                metadata (# /// script blocks, see https://peps.python.org/pep-0723/).
            dependencies: Extra dependency specifiers to validate, using standard
                pip-style format like "requests>=2.28" (see https://peps.python.org/pep-0508/).

        Returns:
            Validation result with metadata details or error information.
        """
        async with tracked_work("validate_script"):
            issues: list[str] = []

            # Try to parse existing metadata
            try:
                extract_metadata(script)
            except Exception as exc:
                return f"INVALID: {exc}"

            # Try to build merged script
            try:
                merged = build_script(
                    script,
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
