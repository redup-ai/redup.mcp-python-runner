"""Shared test fixtures."""

import pytest

from redup_mcp_python_runner.config import ServerConfig


@pytest.fixture
def default_config():
    return ServerConfig()


@pytest.fixture
def no_sandbox_config():
    return ServerConfig(sandbox_backend="none", warm_cache=False)
