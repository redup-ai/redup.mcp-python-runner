"""PEP 723 inline script metadata parsing, merging, and construction."""

from __future__ import annotations

import re
import tomllib

import tomli_w

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
    # Remove leading "# " or "#" from each line
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


def _format_metadata_block(metadata: dict) -> str:
    """Format a metadata dict as a PEP 723 inline metadata block."""
    toml_str = tomli_w.dumps(metadata)
    lines = ["# /// script"]
    for line in toml_str.rstrip("\n").splitlines():
        lines.append(f"# {line}" if line else "#")
    lines.append("# ///")
    return "\n".join(lines) + "\n"


def _normalize_dep_name(dep: str) -> str:
    """Extract the normalized package name from a PEP 508 dependency string.

    Normalizes per PEP 503: lowercase, replace [-_.] runs with single dash.
    """
    # Extract name part before any version specifier or extras
    name = re.split(r"[><=!~;\[\s]", dep, maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def _deduplicate_deps(deps: list[str]) -> list[str]:
    """Deduplicate dependencies, keeping the last occurrence of each name."""
    seen: dict[str, str] = {}
    for dep in deps:
        key = _normalize_dep_name(dep)
        seen[key] = dep
    return list(seen.values())


def build_script(
    script_content: str,
    extra_dependencies: list[str] | None = None,
    python_version: str | None = None,
) -> str:
    """Build a script with merged PEP 723 metadata.

    - If the script already has a metadata block, merges extra_dependencies
      into the existing deps and updates requires-python if provided.
    - If the script has no metadata and no extra deps/python_version,
      returns the script unchanged.
    - Otherwise creates a new metadata block.
    """
    existing_meta = extract_metadata(script_content)
    body = strip_metadata(script_content) if existing_meta else script_content

    has_extras = bool(extra_dependencies)
    needs_python = python_version and "requires-python" not in existing_meta

    # No metadata needed at all
    if not existing_meta and not has_extras and not needs_python:
        return script_content

    # Build merged metadata
    metadata = dict(existing_meta)

    if needs_python and python_version:
        metadata["requires-python"] = f">={python_version}"

    if has_extras and extra_dependencies:
        existing_deps = metadata.get("dependencies", [])
        merged = existing_deps + list(extra_dependencies)
        metadata["dependencies"] = _deduplicate_deps(merged)

    block = _format_metadata_block(metadata)
    return block + "\n" + body
