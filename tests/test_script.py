"""Tests for offline script preparation (no runtime deps)."""

import pytest

from redup_mcp_python_runner.errors import ScriptMetadataError
from redup_mcp_python_runner.script import (
    extract_metadata,
    prepare_script,
    strip_metadata,
)


def test_extract_metadata_basic():
    script = """\
# /// script
# dependencies = ["requests", "rich"]
# requires-python = ">=3.11"
# ///

print("hello")
"""
    meta = extract_metadata(script)
    assert meta["dependencies"] == ["requests", "rich"]
    assert meta["requires-python"] == ">=3.11"


def test_extract_metadata_no_block():
    assert extract_metadata("print('hello')\n") == {}


def test_extract_metadata_malformed_toml():
    script = """\
# /// script
# this is not valid toml [[[
# ///

print("hello")
"""
    with pytest.raises(ScriptMetadataError, match="Malformed TOML"):
        extract_metadata(script)


def test_strip_metadata():
    script = """\
# /// script
# requires-python = ">=3.13"
# ///

print("hello")
"""
    stripped = strip_metadata(script)
    assert "# /// script" not in stripped
    assert 'print("hello")' in stripped


def test_prepare_script_plain():
    code = "print('hello')\n"
    assert prepare_script(code) == code


def test_prepare_script_strips_requires_python_only():
    script = """\
# /// script
# requires-python = ">=3.13"
# ///

print("hello")
"""
    out = prepare_script(script)
    assert "# ///" not in out
    assert 'print("hello")' in out


def test_prepare_script_rejects_dependencies():
    script = """\
# /// script
# dependencies = ["requests"]
# ///

print("hello")
"""
    with pytest.raises(ScriptMetadataError, match="not allowed"):
        prepare_script(script)
