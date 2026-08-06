"""Server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip() != "":
            return value
    return default


@dataclass
class ServerConfig:
    """Configuration for the MCP Python runner service."""

    python_version: str = "3.13"
    sandbox_backend: str = "native"  # "native" (bwrap, Linux) | "none"
    max_timeout: int = 300
    default_timeout: int = 30
    max_output_bytes: int = 102_400  # 100KB
    warm_cache: bool = True
    uv_path: str = "uv"
    # Network transport (default for service deployment)
    transport: str = "http"  # "stdio" | "http" | "streamable-http" | "sse"
    host: str = "0.0.0.0"
    port: int = 8000
    path: str = "/mcp"
    json_response: bool = True
    stateless_http: bool = True

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
        if self.port < 1 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.path.startswith("/"):
            raise ValueError("path must start with '/'")

    @classmethod
    def from_env(cls, **overrides) -> ServerConfig:
        """Build config from environment variables (service-friendly defaults)."""
        data = {
            "python_version": _env_first("PYTHON_VERSION", default="3.13"),
            "sandbox_backend": _env_first("SANDBOX_BACKEND", default="native"),
            "max_timeout": int(_env_first("MAX_TIMEOUT", default="300") or "300"),
            "default_timeout": int(_env_first("DEFAULT_TIMEOUT", default="30") or "30"),
            "max_output_bytes": int(
                _env_first("MAX_OUTPUT_BYTES", default="102400") or "102400"
            ),
            "warm_cache": _env_bool("WARM_CACHE", True),
            "uv_path": _env_first("UV_PATH", default="uv"),
            "transport": _env_first(
                "MCP_TRANSPORT", "FASTMCP_TRANSPORT", default="http"
            ),
            "host": _env_first(
                "LISTEN_ADDRESS", "APP_HOST", "FASTMCP_HOST", default="0.0.0.0"
            ),
            "port": int(
                _env_first("MCP_PORT", "APP_PORT", "FASTMCP_PORT", default="8000")
                or "8000"
            ),
            "path": _env_first(
                "MCP_PATH", "FASTMCP_STREAMABLE_HTTP_PATH", default="/mcp"
            ),
            "json_response": _env_bool(
                "MCP_JSON_RESPONSE",
                _env_bool("FASTMCP_JSON_RESPONSE", True),
            ),
            "stateless_http": _env_bool(
                "MCP_STATELESS_HTTP",
                _env_bool("FASTMCP_STATELESS_HTTP", True),
            ),
        }
        data.update(overrides)
        return cls(**data)
