"""Tests for PEP 723 script metadata parsing and building."""

import pytest

from redup_mcp_python_runner.errors import ScriptMetadataError
from redup_mcp_python_runner.script import (
    build_script,
    extract_metadata,
    strip_metadata,
)

# --- extract_metadata ---


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
    script = "print('hello')\n"
    assert extract_metadata(script) == {}


def test_extract_metadata_empty_block():
    script = """\
# /// script
# ///

print("hello")
"""
    meta = extract_metadata(script)
    assert meta == {}


def test_extract_metadata_malformed_toml():
    script = """\
# /// script
# this is not valid toml [[[
# ///

print("hello")
"""
    with pytest.raises(ScriptMetadataError, match="Malformed TOML"):
        extract_metadata(script)


def test_extract_metadata_multiline():
    script = """\
# /// script
# dependencies = [
#     "requests>=2.28",
#     "rich",
# ]
# ///

print("hello")
"""
    meta = extract_metadata(script)
    assert meta["dependencies"] == ["requests>=2.28", "rich"]


# --- strip_metadata ---


def test_strip_metadata():
    script = """\
# /// script
# dependencies = ["requests"]
# ///

print("hello")
"""
    stripped = strip_metadata(script)
    assert "# /// script" not in stripped
    assert 'print("hello")' in stripped


def test_strip_metadata_no_block():
    script = "print('hello')\n"
    assert strip_metadata(script) == script


# --- build_script ---


def test_build_script_no_metadata_no_extras():
    script = "print('hello')\n"
    result = build_script(script)
    assert result == script  # Unchanged


def test_build_script_adds_deps():
    script = "print('hello')\n"
    result = build_script(script, extra_dependencies=["requests>=2.28"])
    assert "# /// script" in result
    assert "print('hello')" in result
    meta = extract_metadata(result)
    assert "requests>=2.28" in meta["dependencies"]


def test_build_script_adds_python_version():
    script = "print('hello')\n"
    result = build_script(script, python_version="3.13")
    assert "# /// script" in result
    meta = extract_metadata(result)
    assert meta["requires-python"] == ">=3.13"


def test_build_script_merges_with_existing():
    script = """\
# /// script
# dependencies = ["requests"]
# ///

print("hello")
"""
    result = build_script(script, extra_dependencies=["rich"])
    meta = extract_metadata(result)
    assert "requests" in meta["dependencies"]
    assert "rich" in meta["dependencies"]


def test_build_script_deduplicates_deps():
    script = """\
# /// script
# dependencies = ["requests>=2.28"]
# ///

print("hello")
"""
    result = build_script(script, extra_dependencies=["requests>=2.30"])
    meta = extract_metadata(result)
    # Should keep the last occurrence (from extra_dependencies)
    assert len([d for d in meta["dependencies"] if d.startswith("requests")]) == 1
    assert "requests>=2.30" in meta["dependencies"]


def test_build_script_preserves_existing_requires_python():
    script = """\
# /// script
# requires-python = ">=3.11"
# ///

print("hello")
"""
    result = build_script(script, python_version="3.13")
    meta = extract_metadata(result)
    # Should keep existing requires-python, not override
    assert meta["requires-python"] == ">=3.11"


def test_build_script_complex_deps():
    script = "import pandas\nprint(pandas.__version__)\n"
    result = build_script(
        script,
        extra_dependencies=["pandas>=2.0", "numpy", "scipy>=1.11"],
        python_version="3.13",
    )
    meta = extract_metadata(result)
    assert len(meta["dependencies"]) == 3
    assert meta["requires-python"] == ">=3.13"
