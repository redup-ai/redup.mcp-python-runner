"""Exception hierarchy for redup-mcp-python-runner."""


class ExecutorError(Exception):
    """Base exception for all executor errors."""


class ScriptTimeoutError(ExecutorError):
    """Script execution exceeded the allowed timeout."""


class PackageInstallError(ExecutorError):
    """Failed to install one or more packages."""


class SandboxError(ExecutorError):
    """Sandbox setup or enforcement failed."""


class ScriptMetadataError(ExecutorError):
    """Invalid or malformed PEP 723 script metadata."""
