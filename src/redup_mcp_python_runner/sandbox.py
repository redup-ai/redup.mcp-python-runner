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
    def wrap(self, cmd: list[str], script_path: Path) -> list[str]:
        """Wrap a command with sandbox isolation.

        Args:
            cmd: The original command to execute.
            script_path: Path to the script being executed.

        Returns:
            The wrapped command list.
        """
        ...

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of the sandbox configuration."""
        ...


class NoopSandbox(Sandbox):
    """No-op sandbox that passes commands through unchanged."""

    def is_available(self) -> bool:
        return True

    def wrap(self, cmd: list[str], script_path: Path) -> list[str]:
        return cmd

    def describe(self) -> str:
        return "none (no sandboxing)"


def get_sandbox(backend: str) -> Sandbox:
    """Create a sandbox instance for the given backend.

    Falls back to NoopSandbox with a warning if the requested backend
    is not available. Supported backends: ``native`` (bubblewrap, Linux),
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

        from redup_mcp_python_runner.sandbox_linux import BubblewrapSandbox

        sb = BubblewrapSandbox()
        if not sb.is_available():
            logger.warning("bwrap not found, falling back to no sandbox")
            return NoopSandbox()
        return sb

    raise ValueError(f"Unknown sandbox backend: {backend!r}")
