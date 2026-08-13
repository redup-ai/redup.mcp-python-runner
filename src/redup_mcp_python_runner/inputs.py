"""Materialize execute_python ``files`` into an isolated INPUTS_DIR."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from redup_mcp_python_runner.errors import InputFilesError

_MAX_INPUT_FILES_DEFAULT = 16


def _safe_relative_path(raw: str) -> Path:
    """Return a relative Path under inputs; raise on abs / .. / empty."""
    text = (raw or "").strip()
    if not text:
        raise InputFilesError("files[].path must be a non-empty relative path")
    if text.startswith(("/", "\\")) or (len(text) >= 2 and text[1] == ":"):
        raise InputFilesError(
            f"files[].path must be relative (got absolute {text!r})"
        )
    candidate = Path(text)
    if candidate.is_absolute():
        raise InputFilesError(
            f"files[].path must be relative (got absolute {text!r})"
        )
    if ".." in candidate.parts:
        raise InputFilesError(
            f"files[].path must not contain '..' (got {text!r})"
        )
    return candidate


def materialize_input_files(
    inputs_dir: Path,
    files: list[Any] | None,
    *,
    max_file_bytes: int,
    max_total_bytes: int,
    max_count: int = _MAX_INPUT_FILES_DEFAULT,
) -> list[str]:
    """Decode ``files`` into ``inputs_dir``. Returns written relative paths.

    Each item: ``{"path": "<relative>", "content_base64": "<b64>"}``.
    """
    if not files:
        inputs_dir.mkdir(parents=True, exist_ok=True)
        return []

    if not isinstance(files, list):
        raise InputFilesError("files must be a list of {path, content_base64}")

    if len(files) > max_count:
        raise InputFilesError(
            f"files: at most {max_count} items allowed (got {len(files)})"
        )

    inputs_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    total = 0

    for i, item in enumerate(files):
        if not isinstance(item, dict):
            raise InputFilesError(
                f"files[{i}] must be an object with path and content_base64"
            )
        rel = _safe_relative_path(str(item.get("path") or ""))
        b64 = str(item.get("content_base64") or item.get("contentBase64") or "")
        if not b64.strip():
            raise InputFilesError(
                f"files[{i}] ({rel.as_posix()!r}): content_base64 is required"
            )
        try:
            data = base64.b64decode(b64, validate=False)
        except Exception as exc:
            raise InputFilesError(
                f"files[{i}] ({rel.as_posix()!r}): invalid content_base64: {exc}"
            ) from exc

        size = len(data)
        if size > max_file_bytes:
            raise InputFilesError(
                f"files[{i}] ({rel.as_posix()!r}): "
                f"{size} bytes exceeds max_input_file_bytes={max_file_bytes}"
            )
        total += size
        if total > max_total_bytes:
            raise InputFilesError(
                f"files: total decoded size {total} exceeds "
                f"max_inputs_total_bytes={max_total_bytes}"
            )

        dest = (inputs_dir / rel).resolve()
        try:
            dest.relative_to(inputs_dir.resolve())
        except ValueError as exc:
            raise InputFilesError(
                f"files[{i}]: path escapes INPUTS_DIR ({rel.as_posix()!r})"
            ) from exc

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        written.append(rel.as_posix())

    return written
