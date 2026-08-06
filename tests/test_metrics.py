"""Tests for MonitorServer-style tool metrics helper."""

import pytest

from redup_mcp_python_runner.metrics import tracked_work


@pytest.mark.asyncio
async def test_tracked_work_without_monitor_server():
    async with tracked_work("execute_python"):
        pass
