"""Output formatting, truncation, and artifact collection."""

from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExecutionResult:
    """Result of a script execution."""

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool
    artifacts: list[dict] = field(default_factory=list)


def truncate_output(text: str, max_bytes: int) -> str:
    """Truncate text to fit within max_bytes (UTF-8), adding a marker if truncated."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    marker = f"\n... [truncated at {max_bytes / 1024:.0f}KB]"
    marker_bytes = marker.encode("utf-8")
    cut = max_bytes - len(marker_bytes)
    truncated = encoded[:cut].decode("utf-8", errors="ignore")
    return truncated + marker


def collect_artifacts(
    artifacts_dir: Path,
    *,
    max_files: int = 16,
    max_file_bytes: int = 5 * 1024 * 1024,
    max_total_bytes: int = 10 * 1024 * 1024,
) -> list[dict]:
    """Collect files written under ARTIFACTS_DIR as base64 payloads."""
    if not artifacts_dir.is_dir():
        return []

    items: list[dict] = []
    total = 0
    paths = sorted(
        p for p in artifacts_dir.rglob("*") if p.is_file() and not p.name.startswith(".")
    )
    for path in paths:
        if len(items) >= max_files:
            break
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes:
            items.append(
                {
                    "path": str(path.relative_to(artifacts_dir)),
                    "size": size,
                    "error": f"file too large (max {max_file_bytes} bytes)",
                }
            )
            continue
        if total + size > max_total_bytes:
            items.append(
                {
                    "path": str(path.relative_to(artifacts_dir)),
                    "size": size,
                    "error": f"artifacts total exceeds {max_total_bytes} bytes",
                }
            )
            break
        try:
            data = path.read_bytes()
        except OSError as exc:
            items.append(
                {
                    "path": str(path.relative_to(artifacts_dir)),
                    "size": size,
                    "error": str(exc),
                }
            )
            continue
        mime, _ = mimetypes.guess_type(path.name)
        items.append(
            {
                "path": str(path.relative_to(artifacts_dir)),
                "media_type": mime or "application/octet-stream",
                "size": len(data),
                "content_base64": base64.b64encode(data).decode("ascii"),
            }
        )
        total += len(data)
    return items


def format_result(result: ExecutionResult, max_output_bytes: int) -> str:
    """Format an ExecutionResult as a JSON object string (stable for agents)."""
    payload = {
        "stdout": truncate_output(result.stdout, max_output_bytes),
        "stderr": truncate_output(result.stderr, max_output_bytes),
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "artifacts": result.artifacts,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
