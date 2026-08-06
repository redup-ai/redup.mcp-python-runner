"""Tests for output formatting and truncation."""

from redup_mcp_python_runner.output import ExecutionResult, format_result, truncate_output


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
        # Ensure we don't break multi-byte characters
        text = "Hello 世界 " * 200
        result = truncate_output(text, 1024)
        # Should be valid UTF-8
        result.encode("utf-8")
        assert "truncated" in result


class TestFormatResult:
    def test_success(self):
        result = ExecutionResult(
            stdout="hello\n",
            stderr="",
            exit_code=0,
            duration_ms=42,
            timed_out=False,
        )
        formatted = format_result(result, 102400)
        assert "--- stdout ---" in formatted
        assert "hello" in formatted
        assert "--- exit_code: 0 ---" in formatted
        assert "--- duration_ms: 42 ---" in formatted
        assert "timed_out" not in formatted

    def test_error(self):
        result = ExecutionResult(
            stdout="",
            stderr="error message\n",
            exit_code=1,
            duration_ms=10,
            timed_out=False,
        )
        formatted = format_result(result, 102400)
        assert "--- stderr ---" in formatted
        assert "error message" in formatted
        assert "--- exit_code: 1 ---" in formatted

    def test_timeout(self):
        result = ExecutionResult(
            stdout="partial",
            stderr="",
            exit_code=-9,
            duration_ms=2000,
            timed_out=True,
        )
        formatted = format_result(result, 102400)
        assert "--- timed_out: true ---" in formatted

    def test_empty_output_sections_omitted(self):
        result = ExecutionResult(
            stdout="",
            stderr="",
            exit_code=0,
            duration_ms=5,
            timed_out=False,
        )
        formatted = format_result(result, 102400)
        assert "--- stdout ---" not in formatted
        assert "--- stderr ---" not in formatted
        assert "--- exit_code: 0 ---" in formatted
