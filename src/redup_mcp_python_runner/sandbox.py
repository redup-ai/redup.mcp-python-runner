"""Sandbox abstract base class and factory."""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class Sandbox(ABC):
    """Abstract base class for execution sandboxes."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this sandbox backend is available on the current system."""
        ...

    @abstractmethod
    def wrap(
        self,
        cmd: list[str],
        script_path: Path,
        extra_ro_binds: list | None = None,
    ) -> list[str]:
        """Wrap a command with sandbox isolation (no network)."""
        ...

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of the sandbox configuration."""
        ...


class NoopSandbox(Sandbox):
    """No-op sandbox that passes commands through unchanged."""

    def is_available(self) -> bool:
        return True

    def wrap(self, cmd: list[str], script_path: Path, extra_ro_binds: list | None = None) -> list[str]:
        return cmd

    def describe(self) -> str:
        return "none (no sandboxing; still offline — no package install)"


def get_sandbox(backend: str) -> Sandbox:
    """Create a sandbox instance for the given backend.

    Falls back to NoopSandbox with a warning if the requested backend
    is not available. Supported backends: ``native`` (unshare --net, Linux),
    ``none``.
    """
    if backend == "none":
        return NoopSandbox()

    if backend == "native":
        if sys.platform != "linux":
            logger.warning(
                "Native sandbox is Linux-only; falling back to none on %s",
                sys.platform,
            )
            return NoopSandbox()

        from redup_mcp_python_runner.sandbox_linux import UnshareNetSandbox

        sb = UnshareNetSandbox()
        if not sb.is_available():
            logger.warning("unshare not found, falling back to no sandbox")
            return NoopSandbox()
        return sb

    raise ValueError(f"Unknown sandbox backend: {backend!r}")
