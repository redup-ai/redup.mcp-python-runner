"""Offline native sandbox for Linux via ``unshare --net``.

Puts the child in an empty network namespace (no routes → no egress).
Requires ``CAP_SYS_ADMIN``.

Do **not** add ``--pid/--mount-proc`` here: on typical Deckhouse/k8s nodes
``unshare --pid --fork --mount-proc`` fails with Operation not permitted even
with SYS_ADMIN. Network escape via ``setns(/proc/1/ns/net)`` must be blocked by
a pod **NetworkPolicy deny-egress** (CNI enforces on the pod netns).
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
        del script_path, extra_ro_binds
        unshare = self._unshare_path or "unshare"
        return [unshare, "--net", "--", *cmd]

    def describe(self) -> str:
        if self._unshare_path:
            return (
                f"unshare --net ({self._unshare_path}); "
                "empty netns, no egress (needs CAP_SYS_ADMIN + NetworkPolicy)"
            )
        return "unshare (not found)"


BubblewrapSandbox = UnshareNetSandbox
