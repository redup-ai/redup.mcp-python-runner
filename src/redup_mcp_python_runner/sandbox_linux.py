"""Bubblewrap (bwrap) sandbox implementation for Linux — no network."""

from __future__ import annotations

import shutil
from pathlib import Path

from redup_mcp_python_runner.sandbox import Sandbox


class BubblewrapSandbox(Sandbox):
    """Linux sandbox using bubblewrap (bwrap) without network access."""

    def __init__(self) -> None:
        self._bwrap_path = shutil.which("bwrap")

    def is_available(self) -> bool:
        return self._bwrap_path is not None

    def wrap(
        self,
        cmd: list[str],
        script_path: Path,
        extra_ro_binds: list[Path] | None = None,
    ) -> list[str]:
        script_dir = str(script_path.parent.resolve())

        bwrap_cmd = [
            self._bwrap_path or "bwrap",
            "--unshare-all",
            # Intentionally NO --share-net: offline sandbox.
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/sbin",
            "/sbin",
            "--symlink",
            "/usr/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            # Ephemeral workdir (script + artifacts) is writable.
            "--bind",
            script_dir,
            script_dir,
        ]

        if Path("/lib64").is_dir() and not Path("/lib64").is_symlink():
            bwrap_cmd.extend(["--ro-bind", "/lib64", "/lib64"])

        # Preinstalled interpreter / venv (e.g. /opt/code-tools-env).
        seen: set[str] = set()
        for path in extra_ro_binds or []:
            resolved = str(path.resolve())
            if resolved in seen or not Path(resolved).exists():
                continue
            seen.add(resolved)
            bwrap_cmd.extend(["--ro-bind", resolved, resolved])

        # Common locations for the dedicated env even if not passed explicitly.
        for default_root in ("/opt/code-tools-env", "/usr/local"):
            if default_root not in seen and Path(default_root).exists():
                seen.add(default_root)
                bwrap_cmd.extend(["--ro-bind", default_root, default_root])

        bwrap_cmd.extend(cmd)
        return bwrap_cmd

    def describe(self) -> str:
        if self._bwrap_path:
            return f"bubblewrap offline ({self._bwrap_path}, no network)"
        return "bubblewrap (not found)"
