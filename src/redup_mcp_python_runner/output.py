"""Output formatting and truncation utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    """Result of a script execution."""

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool


def truncate_output(text: str, max_bytes: int) -> str:
    """Truncate text to fit within max_bytes (UTF-8), adding a marker if truncated."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    marker = f"\n... [truncated at {max_bytes / 1024:.0f}KB]"
    marker_bytes = marker.encode("utf-8")
    cut = max_bytes - len(marker_bytes)
    # Decode back, ignoring partial chars at the cut boundary
    truncated = encoded[:cut].decode("utf-8", errors="ignore")
    return truncated + marker


def format_result(result: ExecutionResult, max_output_bytes: int) -> str:
    """Format an ExecutionResult as a human-readable string."""
    stdout = truncate_output(result.stdout, max_output_bytes)
    stderr = truncate_output(result.stderr, max_output_bytes)

    parts: list[str] = []
    if stdout:
        parts.append(f"--- stdout ---\n{stdout}")
    if stderr:
        parts.append(f"--- stderr ---\n{stderr}")
    parts.append(f"--- exit_code: {result.exit_code} ---")
    parts.append(f"--- duration_ms: {result.duration_ms} ---")
    if result.timed_out:
        parts.append("--- timed_out: true ---")
    return "\n".join(parts)
