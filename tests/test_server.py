"""Tests for MCP server tool definitions."""

import pytest
from pydantic import ValidationError

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
        assert tools["validate_code"].annotations.readOnlyHint is True
        assert "validate_script" not in tools

    @pytest.mark.asyncio
    async def test_execute_python_schema_uses_llm_names(self, server):
        tools = await server.get_tools()
        props = tools["execute_python"].parameters["properties"]
        assert "code" in props
        assert "timeout" in props
        assert "script" not in props
        assert "timeout_seconds" not in props
        assert props["code"].get("description")
        assert props["timeout"].get("description")
        assert tools["execute_python"].parameters["required"] == ["code"]

    @pytest.mark.asyncio
    async def test_execute_python_rejects_legacy_script_arg(self, server):
        tools = await server.get_tools()
        with pytest.raises(ValidationError):
            await tools["execute_python"].run(
                {"script": "print('legacy')", "timeout_seconds": 5}
            )

    @pytest.mark.asyncio
    async def test_validate_code_schema(self, server):
        tools = await server.get_tools()
        props = tools["validate_code"].parameters["properties"]
        assert "code" in props
        assert "script" not in props
        out = await tools["validate_code"].run({"code": "print(1)"})
        text = getattr(out, "content", None) or out
        # FastMCP ToolResult wraps content blocks
        if hasattr(out, "content"):
            blobs = []
            for c in out.content or []:
                blobs.append(getattr(c, "text", None) or str(c))
            text = "\n".join(blobs)
        assert "VALID" in str(text)
