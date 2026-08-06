"""Bubblewrap (bwrap) sandbox implementation for Linux."""

from __future__ import annotations

import shutil
from pathlib import Path

from redup_mcp_python_runner.sandbox import Sandbox


class BubblewrapSandbox(Sandbox):
    """Linux sandbox using bubblewrap (bwrap)."""

    def __init__(self) -> None:
        self._bwrap_path = shutil.which("bwrap")
        self._uv_cache_dir = Path.home() / ".cache" / "uv"

    def is_available(self) -> bool:
        return self._bwrap_path is not None

    def wrap(self, cmd: list[str], script_path: Path) -> list[str]:
        script_dir = str(script_path.parent)
        cache_dir = str(self._uv_cache_dir)

        bwrap_cmd = [
            self._bwrap_path or "bwrap",
            "--unshare-all",
            "--share-net",
            "--die-with-parent",
            # Read-only system mounts
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
            "--ro-bind",
            "/etc/resolv.conf",
            "/etc/resolv.conf",
            "--ro-bind",
            "/etc/ssl",
            "/etc/ssl",
            # Proc and dev
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            # Tmpfs for tmp
            "--tmpfs",
            "/tmp",
            # Read-write mounts for uv cache and script dir
            "--bind",
            cache_dir,
            cache_dir,
            "--bind",
            script_dir,
            script_dir,
        ]

        # If /lib64 exists as a real directory, bind it
        if Path("/lib64").is_dir() and not Path("/lib64").is_symlink():
            bwrap_cmd.extend(["--ro-bind", "/lib64", "/lib64"])

        bwrap_cmd.extend(cmd)
        return bwrap_cmd

    def describe(self) -> str:
        if self._bwrap_path:
            return f"bubblewrap ({self._bwrap_path})"
        return "bubblewrap (not found)"
