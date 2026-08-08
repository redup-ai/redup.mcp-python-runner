"""Tests for output formatting and truncation."""

import json
from pathlib import Path

from redup_mcp_python_runner.output import (
    ExecutionResult,
    collect_artifacts,
    format_result,
    truncate_output,
)


class TestTruncateOutput:
    def test_no_truncation_needed(self):
        text = "hello world"
        assert truncate_output(text, 1024) == text

    def test_truncation(self):
        text = "x" * 2000
        result = truncate_output(text, 1024)
        assert len(result.encode("utf-8")) <= 1024
        assert "truncated" in result

    def test_unicode_safe_truncation(self):
        text = "Hello 世界 " * 200
        result = truncate_output(text, 1024)
        result.encode("utf-8")
        assert "truncated" in result


class TestFormatResult:
    def test_success_json(self):
        result = ExecutionResult(
            stdout="hello\n",
            stderr="",
            exit_code=0,
            duration_ms=42,
            timed_out=False,
        )
        formatted = format_result(result, 102400)
        data = json.loads(formatted)
        assert data["stdout"] == "hello\n"
        assert data["exit_code"] == 0
        assert data["duration_ms"] == 42
        assert data["timed_out"] is False
        assert data["artifacts"] == []

    def test_error(self):
        result = ExecutionResult(
            stdout="",
            stderr="error message\n",
            exit_code=1,
            duration_ms=10,
            timed_out=False,
        )
        data = json.loads(format_result(result, 102400))
        assert "error message" in data["stderr"]
        assert data["exit_code"] == 1

    def test_timeout(self):
        result = ExecutionResult(
            stdout="partial",
            stderr="",
            exit_code=-9,
            duration_ms=2000,
            timed_out=True,
        )
        data = json.loads(format_result(result, 102400))
        assert data["timed_out"] is True

    def test_artifacts_roundtrip(self, tmp_path: Path):
        art = tmp_path / "artifacts"
        art.mkdir()
        (art / "a.bin").write_bytes(b"\x00\x01PNG")
        items = collect_artifacts(art)
        assert len(items) == 1
        assert items[0]["path"] == "a.bin"
        assert items[0]["size"] == 5
        assert "content_base64" in items[0]
