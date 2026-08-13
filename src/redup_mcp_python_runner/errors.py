"""Exception hierarchy for redup-mcp-python-runner."""


class ExecutorError(Exception):
    """Base exception for all executor errors."""


class ScriptTimeoutError(ExecutorError):
    """Script execution exceeded the allowed timeout."""


class PackageInstallError(ExecutorError):
    """Raised when code attempts a forbidden runtime package install."""


class SandboxError(ExecutorError):
    """Sandbox setup or enforcement failed."""


class ScriptMetadataError(ExecutorError):
    """Invalid or malformed PEP 723 script metadata."""


class InputFilesError(ExecutorError):
    """Invalid execute_python ``files`` payload (path / size / base64)."""
