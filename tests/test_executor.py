"""Tests for executor engine (mocked subprocess)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from redup_mcp_python_runner.executor import _build_clean_env, execute


class TestBuildCleanEnv:
    def test_includes_safe_vars(self):
        with patch.dict(
            "os.environ",
            {"PATH": "/usr/bin", "HOME": "/home/user", "SECRET_KEY": "abc123"},
        ):
            env = _build_clean_env()
            assert "PATH" in env
            assert "HOME" in env
            assert "SECRET_KEY" not in env

    def test_includes_uv_cache_dir(self):
        env = _build_clean_env(uv_cache_dir="/tmp/cache")
        assert env["UV_CACHE_DIR"] == "/tmp/cache"


class TestExecute:
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute(
                script_path=Path("/tmp/test.py"),
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_nonzero_exit(self):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error\n"))
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute(
                script_path=Path("/tmp/test.py"),
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 1
        assert result.stderr == "error\n"
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_timeout(self):
        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"partial", b""))
        mock_proc.returncode = -9

        async def slow_communicate():
            raise TimeoutError()

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            # After timeout, communicate is called again to collect output
            result = await execute(
                script_path=Path("/tmp/test.py"),
                python_version="3.13",
                timeout=1,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.timed_out is True
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_wrapping(self):
        mock_sandbox = MagicMock()
        mock_sandbox.wrap.return_value = [
            "sandbox-exec",
            "-p",
            "profile",
            "uv",
            "run",
            "--script",
            "--python",
            "3.13",
            "/tmp/test.py",
        ]

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await execute(
                script_path=Path("/tmp/test.py"),
                python_version="3.13",
                timeout=30,
                sandbox=mock_sandbox,
                max_output_bytes=102400,
            )

        mock_sandbox.wrap.assert_called_once()
        # Verify the sandbox-wrapped command was used
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "sandbox-exec"

    @pytest.mark.asyncio
    async def test_unicode_output(self):
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=("Hello 世界 🌍".encode(), b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute(
                script_path=Path("/tmp/test.py"),
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert "Hello 世界 🌍" in result.stdout
