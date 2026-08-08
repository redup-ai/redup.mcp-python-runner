"""Script execution engine — preinstalled interpreter only (no uv install)."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

from redup_mcp_python_runner.output import ExecutionResult, collect_artifacts


def resolve_runtime_python(configured: str | None = None) -> str:
    """Pick the offline interpreter used to run user code."""
    if configured and configured.strip():
        return configured.strip()
    env = os.environ.get("CODE_TOOLS_PYTHON", "").strip()
    if env:
        return env
    for candidate in (
        "/opt/code-tools-env/bin/python",
        "/opt/code-tools-env/bin/python3",
    ):
        if Path(candidate).is_file():
            return candidate
    return sys.executable


def _build_clean_env(
    *,
    artifacts_dir: Path,
    work_dir: Path,
) -> dict[str, str]:
    """Build a clean environment: no secrets, no proxy, no pip/uv network hints."""
    env: dict[str, str] = {}
    safe_vars = {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "USER", "TZ"}
    for var in safe_vars:
        val = os.environ.get(var)
        if val is not None:
            env[var] = val

    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["ARTIFACTS_DIR"] = str(artifacts_dir)
    env["HOME"] = str(work_dir)
    env["TMPDIR"] = str(work_dir / "tmp")
    # Explicitly disable common proxy / index overrides if present in parent.
    for kill in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "PIP_INDEX_URL",
        "UV_INDEX_URL",
        "UV_EXTRA_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
    ):
        env.pop(kill, None)
    return env


async def execute(
    script_path: Path,
    timeout: int,
    sandbox: object | None,
    max_output_bytes: int,
    runtime_python: str | None = None,
    max_artifact_bytes: int = 5 * 1024 * 1024,
    max_artifacts_total_bytes: int = 10 * 1024 * 1024,
) -> ExecutionResult:
    """Execute a Python script with the preinstalled interpreter (offline).

    Does not invoke ``uv run --script`` and never installs packages.
    """
    resolved_path = script_path.resolve()
    work_dir = resolved_path.parent
    artifacts_dir = work_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "tmp").mkdir(parents=True, exist_ok=True)

    python_bin = resolve_runtime_python(runtime_python)
    cmd = [python_bin, str(resolved_path)]

    extra_ro: list[Path] = []
    py = Path(python_bin).resolve()
    # Bind the venv / prefix so bwrap can see the interpreter.
    for parent in (py.parent.parent, py.parent):
        if parent.exists():
            extra_ro.append(parent)
            break

    if sandbox is not None:
        wrap = getattr(sandbox, "wrap", None)
        if wrap is not None:
            try:
                cmd = wrap(cmd, resolved_path, extra_ro_binds=extra_ro)
            except TypeError:
                # Older / Noop wrap(cmd, script_path) signature
                cmd = wrap(cmd, resolved_path)

    env = _build_clean_env(artifacts_dir=artifacts_dir, work_dir=work_dir)
    start = time.monotonic()
    timed_out = False

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(work_dir),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        timed_out = True
        proc.kill()
        stdout_bytes, stderr_bytes = await proc.communicate()

    elapsed_ms = int((time.monotonic() - start) * 1000)

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    # Soft-trim streamed pipes before JSON formatting (format_result also truncates).
    if len(stdout.encode("utf-8")) > max_output_bytes * 4:
        stdout = stdout[: max_output_bytes * 2]
    if len(stderr.encode("utf-8")) > max_output_bytes * 4:
        stderr = stderr[: max_output_bytes * 2]

    artifacts = collect_artifacts(
        artifacts_dir,
        max_file_bytes=max_artifact_bytes,
        max_total_bytes=max_artifacts_total_bytes,
    )

    return ExecutionResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=proc.returncode if proc.returncode is not None else -1,
        duration_ms=elapsed_ms,
        timed_out=timed_out,
        artifacts=artifacts,
    )
