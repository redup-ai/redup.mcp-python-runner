"""Integration tests — require uv installed."""

import shutil
import tempfile
from pathlib import Path

import pytest

from redup_mcp_python_runner.executor import execute
from redup_mcp_python_runner.script import build_script

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv not installed",
)


class TestRealExecution:
    @pytest.mark.asyncio
    async def test_simple_script(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text("print('hello from uv')\n")

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 0
        assert "hello from uv" in result.stdout
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_script_with_exit_code(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text("import sys; sys.exit(42)\n")

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 42

    @pytest.mark.asyncio
    async def test_script_with_stderr(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text("import sys; print('err', file=sys.stderr)\nprint('out')\n")

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 0
        assert "out" in result.stdout
        assert "err" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text("import time; time.sleep(60)\n")

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=2,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_script_with_pep723_deps(self):
        """Test that PEP 723 inline metadata works with uv."""
        script = build_script(
            "import pydantic; print(pydantic.__version__)\n",
            extra_dependencies=["pydantic>=2.0"],
            python_version="3.13",
        )

        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text(script)

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=120,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code == 0
        # Should print a version like "2.x.y"
        assert result.stdout.strip().startswith("2.")

    @pytest.mark.asyncio
    async def test_invalid_dependency(self):
        """Test that an invalid dependency produces a clear error."""
        script = build_script(
            "print('hello')\n",
            extra_dependencies=["this-package-does-not-exist-xyz123"],
            python_version="3.13",
        )

        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "test.py"
            script_path.write_text(script)

            result = await execute(
                script_path=script_path,
                python_version="3.13",
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
            )

        assert result.exit_code != 0
