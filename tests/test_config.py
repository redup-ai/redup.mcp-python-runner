"""Tests for server configuration."""

import sys

import pytest

from redup_mcp_python_runner.__main__ import parse_args
from redup_mcp_python_runner.config import ServerConfig


class TestServerConfig:
    def test_defaults(self):
        config = ServerConfig()
        assert config.python_version == "3.13"
        assert config.sandbox_backend == "native"
        assert config.max_timeout == 300
        assert config.default_timeout == 30
        assert config.max_output_bytes == 1_048_576
        assert config.warm_cache is False
        assert config.transport == "http"
        assert config.json_response is True

    def test_invalid_sandbox_backend(self):
        with pytest.raises(ValueError, match="Invalid sandbox_backend"):
            ServerConfig(sandbox_backend="invalid")

    def test_invalid_max_timeout(self):
        with pytest.raises(ValueError, match="max_timeout must be >= 1"):
            ServerConfig(max_timeout=0)

    def test_invalid_default_timeout(self):
        with pytest.raises(ValueError, match="default_timeout must be between"):
            ServerConfig(default_timeout=0)

    def test_default_timeout_exceeds_max(self):
        with pytest.raises(ValueError, match="default_timeout must be between"):
            ServerConfig(max_timeout=10, default_timeout=20)

    def test_invalid_max_output_bytes(self):
        with pytest.raises(ValueError, match="max_output_bytes must be >= 1024"):
            ServerConfig(max_output_bytes=100)

    def test_from_servicekit(self):
        config = ServerConfig.from_servicekit(
            {
                "service": {
                    "host": "127.0.0.1",
                    "port": 9000,
                    "path": "/mcp",
                },
                "McpPythonRunner": {
                    "sandbox_backend": "native",
                    "python_version": "3.13",
                    "runtime_python": "/opt/code-tools-env/bin/python",
                    "default_timeout": 15,
                    "max_timeout": 120,
                    "max_output_bytes": 50_000,
                    "warm_cache": False,
                    "json_response": True,
                    "stateless_http": True,
                },
            }
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.sandbox_backend == "native"
        assert config.runtime_python == "/opt/code-tools-env/bin/python"
        assert config.default_timeout == 15
        assert config.transport == "streamable-http"

    def test_from_servicekit_string_bools(self):
        config = ServerConfig.from_servicekit(
            {
                "service": {"host": "0.0.0.0", "port": "8000", "path": "/mcp"},
                "McpPythonRunner": {
                    "sandbox_backend": "none",
                    "warm_cache": "false",
                    "json_response": "true",
                    "stateless_http": "1",
                },
            }
        )
        assert config.port == 8000
        assert config.warm_cache is False
        assert config.json_response is True
        assert config.stateless_http is True


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.python_version == "3.13"
        expected_backend = "native" if sys.platform == "linux" else "none"
        assert args.sandbox_backend == expected_backend
        assert args.max_timeout == 300
        assert args.default_timeout == 30
        assert args.max_output_bytes == 1_048_576
        assert args.transport == "stdio"

    def test_custom_args(self):
        args = parse_args(
            [
                "--transport",
                "http",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--runtime-python",
                "/opt/code-tools-env/bin/python",
                "--sandbox-backend",
                "none",
                "--max-timeout",
                "600",
                "--default-timeout",
                "60",
                "--max-output-bytes",
                "200000",
                "--no-warm-cache",
            ]
        )
        assert args.transport == "http"
        assert args.runtime_python == "/opt/code-tools-env/bin/python"
        assert args.sandbox_backend == "none"
        assert args.max_timeout == 600
        assert args.no_warm_cache is True
