"""Offline native sandbox for Linux via ``unshare --net``.

Bubblewrap ``--unshare-all`` needs a full privileged container (user namespaces +
proc mounts). In typical Docker/Kubernetes the reliable offline primitive is:

    unshare --net -- <command>

which requires ``CAP_SYS_ADMIN`` and puts the child in an empty network
namespace (no routes → no egress). The MCP HTTP server process itself is not
wrapped and keeps serving traffic.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from redup_mcp_python_runner.sandbox import Sandbox


class UnshareNetSandbox(Sandbox):
    """Isolate script execution in an empty network namespace (no egress)."""

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
        # --net: new empty network namespace (blocks egress).
        # Trailing -- so flags in cmd cannot be parsed by unshare.
        return [unshare, "--net", "--", *cmd]

    def describe(self) -> str:
        if self._unshare_path:
            return (
                f"unshare --net ({self._unshare_path}); "
                "empty netns, no egress (needs CAP_SYS_ADMIN)"
            )
        return "unshare (not found)"


# Back-compat alias used by older imports/tests.
BubblewrapSandbox = UnshareNetSandbox
