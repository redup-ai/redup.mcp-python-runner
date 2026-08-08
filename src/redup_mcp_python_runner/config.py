"""Server configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ServerConfig:
    """Runtime configuration for the MCP Python runner."""

    python_version: str = "3.13"
    sandbox_backend: str = "native"  # "native" (bwrap, Linux) | "none"
    max_timeout: int = 300
    default_timeout: int = 30
    max_output_bytes: int = 1_048_576  # 1MB text streams
    max_artifact_bytes: int = 5 * 1024 * 1024
    max_artifacts_total_bytes: int = 10 * 1024 * 1024
    # Absolute path to preinstalled interpreter (Docker: /opt/code-tools-env/bin/python).
    runtime_python: str = ""
    packages_file: str = ""
    # Network transport
    transport: str = "http"  # "stdio" | "http" | "streamable-http" | "sse"
    host: str = "0.0.0.0"
    port: int = 8000
    path: str = "/mcp"
    json_response: bool = True
    stateless_http: bool = True
    # Kept for CLI compat; ignored — packages are build-time only.
    warm_cache: bool = False
    uv_path: str = "uv"  # only used to report version in check_environment

    def __post_init__(self) -> None:
        valid_backends = ("native", "none")
        if self.sandbox_backend not in valid_backends:
            raise ValueError(
                f"Invalid sandbox_backend {self.sandbox_backend!r}, "
                f"must be one of {valid_backends}"
            )
        if self.max_timeout < 1:
            raise ValueError("max_timeout must be >= 1")
        if self.default_timeout < 1 or self.default_timeout > self.max_timeout:
            raise ValueError(f"default_timeout must be between 1 and {self.max_timeout}")
        if self.max_output_bytes < 1024:
            raise ValueError("max_output_bytes must be >= 1024")
        if self.max_artifact_bytes < 1024:
            raise ValueError("max_artifact_bytes must be >= 1024")
        if self.max_artifacts_total_bytes < self.max_artifact_bytes:
            raise ValueError("max_artifacts_total_bytes must be >= max_artifact_bytes")
        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.path.startswith("/"):
            raise ValueError("path must start with '/'")

    @classmethod
    def from_servicekit(cls, config: Mapping[str, Any]) -> ServerConfig:
        """Build from a servicekit YAML dict (`service` + `McpPythonRunner`)."""
        service = config.get("service") or {}
        runner = config.get("McpPythonRunner") or {}
        return cls(
            python_version=str(runner.get("python_version", "3.13")),
            sandbox_backend=str(runner.get("sandbox_backend", "none")),
            max_timeout=int(runner.get("max_timeout", 300)),
            default_timeout=int(runner.get("default_timeout", 30)),
            max_output_bytes=int(runner.get("max_output_bytes", 1_048_576)),
            max_artifact_bytes=int(runner.get("max_artifact_bytes", 5 * 1024 * 1024)),
            max_artifacts_total_bytes=int(
                runner.get("max_artifacts_total_bytes", 10 * 1024 * 1024)
            ),
            runtime_python=str(runner.get("runtime_python", "") or ""),
            packages_file=str(runner.get("packages_file", "") or ""),
            warm_cache=_as_bool(runner.get("warm_cache"), False),
            uv_path=str(runner.get("uv_path", "uv")),
            transport="streamable-http",
            host=str(service.get("host", "0.0.0.0")),
            port=int(service.get("port", 8000)),
            path=str(service.get("path", "/mcp")),
            json_response=_as_bool(runner.get("json_response"), True),
            stateless_http=_as_bool(runner.get("stateless_http"), True),
        )
