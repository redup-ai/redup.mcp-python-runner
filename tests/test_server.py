"""Tests for MCP server tool definitions."""

import pytest

from redup_mcp_python_runner.config import ServerConfig
from redup_mcp_python_runner.server import create_server


@pytest.fixture
def server():
    config = ServerConfig(sandbox_backend="none", warm_cache=False)
    return create_server(config)


class TestCreateServer:
    def test_creates_server(self, server):
        assert server is not None

    def test_uv_not_found(self):
        config = ServerConfig(sandbox_backend="none", warm_cache=False, uv_path="/nonexistent/uv")
        with pytest.raises(RuntimeError, match="uv not found"):
            create_server(config)

    @pytest.mark.asyncio
    async def test_tool_annotations(self, server):
        tools = await server.get_tools()
        assert tools["execute_python"].annotations.readOnlyHint is False
        assert tools["execute_python"].annotations.destructiveHint is True
        assert tools["check_environment"].annotations.readOnlyHint is True
        assert tools["validate_script"].annotations.readOnlyHint is True
