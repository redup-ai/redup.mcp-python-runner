"""Integration tests — run with the local interpreter (offline, no uv install)."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from redup_mcp_python_runner.executor import execute
from redup_mcp_python_runner.output import format_result
from redup_mcp_python_runner.script import prepare_script


class TestRealExecution:
    @pytest.mark.asyncio
    async def test_simple_script(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("print('hello from offline')\n")
            (Path(tmpdir) / "artifacts").mkdir()

            result = await execute(
                script_path=script_path,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python=sys.executable,
            )

        assert result.exit_code == 0
        assert "hello from offline" in result.stdout
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_script_with_exit_code(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("import sys; sys.exit(42)\n")
            (Path(tmpdir) / "artifacts").mkdir()

            result = await execute(
                script_path=script_path,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python=sys.executable,
            )

        assert result.exit_code == 42

    @pytest.mark.asyncio
    async def test_script_with_stderr(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(
                "import sys; print('err', file=sys.stderr)\nprint('out')\n"
            )
            (Path(tmpdir) / "artifacts").mkdir()

            result = await execute(
                script_path=script_path,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python=sys.executable,
            )

        assert result.exit_code == 0
        assert "out" in result.stdout
        assert "err" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text("import time; time.sleep(60)\n")
            (Path(tmpdir) / "artifacts").mkdir()

            result = await execute(
                script_path=script_path,
                timeout=2,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python=sys.executable,
            )

        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_artifacts_collected(self):
        with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(
                "import os\n"
                "from pathlib import Path\n"
                "Path(os.environ['ARTIFACTS_DIR'], 'hi.txt').write_text('ok')\n"
                "print('done')\n"
            )
            (Path(tmpdir) / "artifacts").mkdir()

            result = await execute(
                script_path=script_path,
                timeout=30,
                sandbox=None,
                max_output_bytes=102400,
                runtime_python=sys.executable,
            )

        assert result.exit_code == 0
        assert len(result.artifacts) == 1
        assert result.artifacts[0]["path"] == "hi.txt"
        data = json.loads(format_result(result, 102400))
        assert data["artifacts"][0]["path"] == "hi.txt"

    def test_prepare_rejects_network_deps(self):
        with pytest.raises(Exception, match="not allowed"):
            prepare_script(
                "# /// script\n# dependencies = ['requests']\n# ///\nprint(1)\n"
            )

    @pytest.mark.asyncio
    @pytest.mark.skipif(shutil.which("unshare") is None, reason="unshare not installed")
    async def test_unshare_net_wrap_flag(self):
        from redup_mcp_python_runner.sandbox_linux import UnshareNetSandbox

        sb = UnshareNetSandbox()
        if not sb.is_available():
            pytest.skip("unshare unavailable")
        wrapped = sb.wrap([sys.executable, "-c", "print(1)"], Path("/tmp"))
        assert wrapped[:6] == [
            sb._unshare_path,
            "--net",
            "--pid",
            "--fork",
            "--mount-proc",
            "--",
        ]
