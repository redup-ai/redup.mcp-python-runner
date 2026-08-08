"""Offline native sandbox for Linux via ``unshare --net --pid``.

Creates an empty network namespace (no egress) and a new PID namespace with a
fresh ``/proc`` so scripts cannot ``setns(/proc/1/ns/net)`` into the MCP
server's network namespace.

Requires ``CAP_SYS_ADMIN``. Pair with a pod NetworkPolicy deny-egress so even a
future escape still cannot leave the cluster/internet.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from redup_mcp_python_runner.sandbox import Sandbox


class UnshareNetSandbox(Sandbox):
    """Isolate script execution in empty netns + private pid/proc."""

    def __init__(self) -> None:
        self._unshare_path = shutil.which("unshare")

    def is_available(self) -> bool:
        return self._unshare_path is not None

    def wrap(
        self,
        cmd: list[str],
        script_path: Path,
        extra_ro_binds: list[Path] | None = None,
    ) -> list[str]:
        del script_path, extra_ro_binds  # FS isolation is the container layer
        unshare = self._unshare_path or "unshare"
        # --net: empty network namespace (no routes / no egress).
        # --pid --fork --mount-proc: private PID namespace so /proc/1 is this
        # child, not the MCP server (blocks setns netns escape).
        # Trailing -- so flags in cmd cannot be parsed by unshare.
        return [
            unshare,
            "--net",
            "--pid",
            "--fork",
            "--mount-proc",
            "--",
            *cmd,
        ]

    def describe(self) -> str:
        if self._unshare_path:
            return (
                f"unshare --net --pid --fork --mount-proc ({self._unshare_path}); "
                "empty netns + private /proc (needs CAP_SYS_ADMIN)"
            )
        return "unshare (not found)"


# Back-compat alias used by older imports/tests.
BubblewrapSandbox = UnshareNetSandbox
