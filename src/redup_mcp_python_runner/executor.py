"""Script execution engine using uv subprocess orchestration."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

from redup_mcp_python_runner.output import ExecutionResult

_uv_cache_dir: str | None = None


def _get_uv_cache_dir() -> str | None:
    """Discover uv's cache directory (cached after first call)."""
    global _uv_cache_dir  # noqa: PLW0603
    if _uv_cache_dir is not None:
        return _uv_cache_dir
    uv = shutil.which("uv")
    if uv:
        try:
            result = subprocess.run(
                [uv, "cache", "dir"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                _uv_cache_dir = str(Path(result.stdout.strip()).resolve())
                return _uv_cache_dir
        except Exception:
            pass
    return None


def _build_clean_env(uv_cache_dir: str | None = None) -> dict[str, str]:
    """Build a clean environment dict, stripping secrets from the parent env."""
    env: dict[str, str] = {}

    # Only pass through safe variables
    safe_vars = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "USER"}
    for var in safe_vars:
        val = os.environ.get(var)
        if val is not None:
            env[var] = val

    if uv_cache_dir:
        env["UV_CACHE_DIR"] = uv_cache_dir

    return env


async def execute(
    script_path: Path,
    python_version: str,
    timeout: int,
    sandbox: object | None,
    max_output_bytes: int,
    uv_path: str = "uv",
) -> ExecutionResult:
    """Execute a Python script using uv run --script.

    Args:
        script_path: Path to the script file to execute.
        python_version: Python version to use (e.g. "3.13").
        timeout: Maximum execution time in seconds.
        sandbox: Sandbox instance (with .wrap() method) or None.
        max_output_bytes: Maximum output size in bytes.
        uv_path: Path to the uv binary.

    Returns:
        ExecutionResult with stdout, stderr, exit_code, duration, and timeout status.
    """
    # Resolve symlinks so paths match sandbox allow-lists (e.g. /var -> /private/var)
    resolved_path = script_path.resolve()
    cmd = [uv_path, "run", "--script", "--python", python_version, str(resolved_path)]

    if sandbox is not None:
        cmd = sandbox.wrap(cmd, resolved_path)

    env = _build_clean_env(uv_cache_dir=_get_uv_cache_dir())
    start = time.monotonic()
    timed_out = False

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=resolved_path.parent,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        timed_out = True
        proc.kill()
        stdout_bytes, stderr_bytes = await proc.communicate()

    elapsed_ms = int((time.monotonic() - start) * 1000)

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    return ExecutionResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=proc.returncode if proc.returncode is not None else -1,
        duration_ms=elapsed_ms,
        timed_out=timed_out,
    )
