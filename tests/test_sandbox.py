"""Tests for sandbox layer."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from redup_mcp_python_runner.sandbox import NoopSandbox, get_sandbox


class TestNoopSandbox:
    def test_is_available(self):
        sb = NoopSandbox()
        assert sb.is_available() is True

    def test_wrap_passthrough(self):
        sb = NoopSandbox()
        cmd = ["python", "test.py"]
        assert sb.wrap(cmd, Path("/tmp/test.py")) == cmd

    def test_describe(self):
        sb = NoopSandbox()
        assert "none" in sb.describe()


class TestGetSandbox:
    def test_none_backend(self):
        sb = get_sandbox("none")
        assert isinstance(sb, NoopSandbox)

    def test_invalid_backend(self):
        with pytest.raises(ValueError, match="Unknown sandbox backend"):
            get_sandbox("invalid")

    @patch("sys.platform", "linux")
    def test_native_linux_fallback_when_bwrap_missing(self):
        with patch("shutil.which", return_value=None):
            sb = get_sandbox("native")
            assert isinstance(sb, NoopSandbox)

    @patch("sys.platform", "darwin")
    def test_native_non_linux_falls_back_to_none(self):
        sb = get_sandbox("native")
        assert isinstance(sb, NoopSandbox)


class TestBubblewrapSandbox:
    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_wrap_command_offline(self):
        from redup_mcp_python_runner.sandbox_linux import BubblewrapSandbox

        with patch("shutil.which", return_value="/usr/bin/bwrap"):
            sb = BubblewrapSandbox()
            cmd = ["/opt/code-tools-env/bin/python", "/tmp/test.py"]
            wrapped = sb.wrap(
                cmd,
                Path("/tmp/test.py"),
                extra_ro_binds=[Path("/opt/code-tools-env")],
            )
            assert wrapped[0] == "/usr/bin/bwrap"
            assert "--unshare-all" in wrapped
            assert "--share-net" not in wrapped
            assert "/etc/resolv.conf" not in wrapped
            assert "--die-with-parent" in wrapped
            assert wrapped[-2:] == cmd
