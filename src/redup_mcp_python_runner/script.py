"""PEP 723 metadata parsing and offline script preparation."""

from __future__ import annotations

import re
import tomllib

from redup_mcp_python_runner.errors import ScriptMetadataError

_METADATA_RE = re.compile(r"(?m)^# /// script\s*\n((?:#[^\n]*\n)*?)# ///$")


def extract_metadata(script: str) -> dict:
    """Extract PEP 723 inline script metadata from a script string.

    Returns the parsed TOML as a dict, or an empty dict if no metadata block
    is found.
    """
    match = _METADATA_RE.search(script)
    if match is None:
        return {}

    raw = match.group(1)
    lines = []
    for line in raw.splitlines():
        if line.startswith("# "):
            lines.append(line[2:])
        elif line == "#":
            lines.append("")
        else:
            lines.append(line[1:] if line.startswith("#") else line)
    toml_str = "\n".join(lines)

    try:
        return tomllib.loads(toml_str)
    except tomllib.TOMLDecodeError as exc:
        raise ScriptMetadataError(f"Malformed TOML in script metadata: {exc}") from exc


def strip_metadata(script: str) -> str:
    """Remove the PEP 723 metadata block from a script string."""
    return _METADATA_RE.sub("", script).lstrip("\n")


def prepare_script(code: str) -> str:
    """Prepare user code for offline execution.

    Strips any PEP 723 metadata block. Raises if the block declares
    ``dependencies`` — runtime installs are forbidden; only preinstalled
    packages may be imported.
    """
    meta = extract_metadata(code)
    deps = meta.get("dependencies") or []
    if deps:
        raise ScriptMetadataError(
            "Inline dependencies are not allowed in this sandbox. "
            "Packages cannot be installed at runtime (no network). "
            "Use only preinstalled packages from check_environment / packages list. "
            f"Rejected dependencies: {deps}"
        )
    if meta:
        return strip_metadata(code)
    return code
