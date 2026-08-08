"""Tests for MCP server tool definitions."""

import json

import pytest
from pydantic import ValidationError

from redup_mcp_python_runner.config import ServerConfig
from redup_mcp_python_runner.server import create_server


def _tool_text(out) -> str:
    if hasattr(out, "content"):
        blobs = []
        for c in out.content or []:
            blobs.append(getattr(c, "text", None) or str(c))
        return "\n".join(blobs)
    return str(out)


@pytest.fixture
def server():
    config = ServerConfig(sandbox_backend="none", warm_cache=False)
    return create_server(config)


class TestCreateServer:
    def test_creates_server(self, server):
        assert server is not None

    @pytest.mark.asyncio
    async def test_tool_annotations(self, server):
        tools = await server.get_tools()
        assert tools["execute_python"].annotations.readOnlyHint is False
        assert tools["execute_python"].annotations.destructiveHint is True
        assert tools["execute_python"].annotations.openWorldHint is False
        assert tools["check_environment"].annotations.readOnlyHint is True
        assert tools["validate_code"].annotations.readOnlyHint is True
        assert "validate_script" not in tools

    @pytest.mark.asyncio
    async def test_execute_python_schema_no_dependencies(self, server):
        tools = await server.get_tools()
        props = tools["execute_python"].parameters["properties"]
        assert "code" in props
        assert "timeout" in props
        assert "dependencies" not in props
        assert "script" not in props
        assert tools["execute_python"].parameters["required"] == ["code"]

    @pytest.mark.asyncio
    async def test_execute_python_rejects_legacy_script_arg(self, server):
        tools = await server.get_tools()
        with pytest.raises(ValidationError):
            await tools["execute_python"].run(
                {"script": "print('legacy')", "timeout_seconds": 5}
            )

    @pytest.mark.asyncio
    async def test_validate_code_ok(self, server):
        tools = await server.get_tools()
        out = await tools["validate_code"].run({"code": "print(1)"})
        assert "VALID" in _tool_text(out)

    @pytest.mark.asyncio
    async def test_validate_code_rejects_deps(self, server):
        tools = await server.get_tools()
        code = """\
# /// script
# dependencies = ["requests"]
# ///
print(1)
"""
        out = await tools["validate_code"].run({"code": code})
        text = _tool_text(out)
        assert "INVALID" in text
        assert "dependencies" in text.lower() or "not allowed" in text.lower()

    @pytest.mark.asyncio
    async def test_execute_python_rejects_pep723_deps_without_running(self, server):
        tools = await server.get_tools()
        code = """\
# /// script
# dependencies = ["requests"]
# ///
print(1)
"""
        out = await tools["execute_python"].run({"code": code, "timeout": 5})
        data = json.loads(_tool_text(out))
        assert data["exit_code"] == 2
        assert "not allowed" in data["stderr"]
