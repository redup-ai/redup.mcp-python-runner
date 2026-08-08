"""Tests for executor engine (mocked subprocess)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from redup_mcp_python_runner.executor import _build_clean_env, execute, resolve_runtime_python


class TestBuildCleanEnv:
    def test_includes_safe_vars(self, tmp_path: Path):
        with patch.dict(
            "os.environ",
            {"PATH": "/usr/bin", "HOME": "/home/user", "SECRET_KEY": "abc123", "HTTP_PROXY": "x"},
        ):
            env = _build_clean_env(artifacts_dir=tmp_path / "a", work_dir=tmp_path)
            assert "PATH" in env
            assert "SECRET_KEY" not in env
            assert "HTTP_PROXY" not in env
            assert env["ARTIFACTS_DIR"] == str(tmp_path / "a")
            assert env["PYTHONNOUSERSITE"] == "1"


class TestResolveRuntimePython:
    def test_configured_wins(self):
        assert resolve_runtime_python("/opt/x/bin/python") == "/opt/x/bin/python"

    def test_falls_back_to_sys(self):
        with patch.dict("os.environ", {"CODE_TOOLS_PYTHON": ""}, clear=False):
            py = resolve_runtime_python("")
            assert py


class TestExecute:
    @pytest.mark.asyncio
    async def test_successful_execution(self, tmp_path: Path):
        script = tmp_path / "script.py"
        script.write_text("print(1)\n")
        (tmp_path / "artifacts").mkdir()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            result = await execute(
                script_path=script,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python="/usr/bin/python3",
            )

        assert result.stdout == "hello\n"
        assert result.exit_code == 0
        assert result.timed_out is False
        assert mock_exec.call_args[0][0] == "/usr/bin/python3"
        assert mock_exec.call_args[0][1] == str(script.resolve())

    @pytest.mark.asyncio
    async def test_nonzero_exit(self, tmp_path: Path):
        script = tmp_path / "script.py"
        script.write_text("raise SystemExit(1)\n")
        (tmp_path / "artifacts").mkdir()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error\n"))
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await execute(
                script_path=script,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 1
        assert result.stderr == "error\n"

    @pytest.mark.asyncio
    async def test_timeout(self, tmp_path: Path):
        script = tmp_path / "script.py"
        script.write_text("import time; time.sleep(99)\n")
        (tmp_path / "artifacts").mkdir()

        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"partial", b""))
        mock_proc.returncode = -9

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            result = await execute(
                script_path=script,
                timeout=1,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.timed_out is True
        mock_proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_wrapping(self, tmp_path: Path):
        script = tmp_path / "script.py"
        script.write_text("print(1)\n")
        (tmp_path / "artifacts").mkdir()

        mock_sandbox = MagicMock()
        mock_sandbox.wrap.return_value = ["bwrap", "/usr/bin/python3", str(script)]

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"ok\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await execute(
                script_path=script,
                timeout=30,
                sandbox=mock_sandbox,
                max_output_bytes=102400,
                runtime_python="/usr/bin/python3",
            )

        mock_sandbox.wrap.assert_called_once()
        assert mock_exec.call_args[0][0] == "bwrap"
