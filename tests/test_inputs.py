"""Tests for execute_python input files materialization."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from redup_mcp_python_runner.errors import InputFilesError
from redup_mcp_python_runner.inputs import materialize_input_files


def test_materialize_empty(tmp_path: Path):
    written = materialize_input_files(
        tmp_path / "inputs",
        None,
        max_file_bytes=1024,
        max_total_bytes=2048,
    )
    assert written == []
    assert (tmp_path / "inputs").is_dir()


def test_materialize_roundtrip(tmp_path: Path):
    payload = b"hello-zip"
    written = materialize_input_files(
        tmp_path / "inputs",
        [
            {
                "path": "data.zip",
                "content_base64": base64.b64encode(payload).decode("ascii"),
            }
        ],
        max_file_bytes=1024,
        max_total_bytes=2048,
    )
    assert written == ["data.zip"]
    assert (tmp_path / "inputs" / "data.zip").read_bytes() == payload


def test_materialize_subdir(tmp_path: Path):
    materialize_input_files(
        tmp_path / "inputs",
        [{"path": "a/b.txt", "content_base64": base64.b64encode(b"x").decode()}],
        max_file_bytes=1024,
        max_total_bytes=2048,
    )
    assert (tmp_path / "inputs" / "a" / "b.txt").read_bytes() == b"x"


def test_reject_absolute(tmp_path: Path):
    with pytest.raises(InputFilesError, match="relative"):
        materialize_input_files(
            tmp_path / "inputs",
            [{"path": "/etc/passwd", "content_base64": "YQ=="}],
            max_file_bytes=1024,
            max_total_bytes=2048,
        )


def test_reject_dotdot(tmp_path: Path):
    with pytest.raises(InputFilesError, match=r"\.\."):
        materialize_input_files(
            tmp_path / "inputs",
            [{"path": "../escape.txt", "content_base64": "YQ=="}],
            max_file_bytes=1024,
            max_total_bytes=2048,
        )


def test_reject_oversize_file(tmp_path: Path):
    data = base64.b64encode(b"x" * 100).decode()
    with pytest.raises(InputFilesError, match="max_input_file_bytes"):
        materialize_input_files(
            tmp_path / "inputs",
            [{"path": "big.bin", "content_base64": data}],
            max_file_bytes=50,
            max_total_bytes=10_000,
        )


def test_reject_too_many(tmp_path: Path):
    items = [
        {"path": f"f{i}.txt", "content_base64": base64.b64encode(b"a").decode()}
        for i in range(5)
    ]
    with pytest.raises(InputFilesError, match="at most"):
        materialize_input_files(
            tmp_path / "inputs",
            items,
            max_file_bytes=1024,
            max_total_bytes=10_000,
            max_count=3,
        )
