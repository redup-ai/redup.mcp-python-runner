"""Cache warming logic — pre-download popular packages on startup."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PACKAGES = [
    "requests",
    "httpx",
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "scikit-learn",
    "pydantic",
    "rich",
    "polars",
    "beautifulsoup4",
    "pillow",
    "sympy",
    "pyyaml",
    "fastapi",
    "sqlalchemy",
]


def _load_package_list(packages_file: Path | None = None) -> list[str]:
    """Load packages from an optional file, else use built-in defaults."""
    if packages_file is not None and packages_file.exists():
        lines = packages_file.read_text().splitlines()
        return [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return list(_DEFAULT_PACKAGES)


async def warm_cache(
    uv_path: str = "uv",
    python_version: str = "3.13",
    packages_file: Path | None = None,
) -> None:
    """Pre-download popular packages into the uv cache.

    This runs in the background and is non-fatal — failures are logged
    as warnings.
    """
    packages = _load_package_list(packages_file)
    if not packages:
        return

    logger.info("Cache warming: downloading %d packages...", len(packages))

    try:
        proc = await asyncio.create_subprocess_exec(
            uv_path,
            "pip",
            "download",
            "--python-version",
            python_version,
            *packages,
            "--dest",
            "/dev/null",  # We only want the cache side-effect
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0:
            logger.info("Cache warming complete")
        else:
            logger.warning(
                "Cache warming finished with errors (exit %d): %s",
                proc.returncode,
                stderr.decode("utf-8", errors="replace")[:500],
            )
    except TimeoutError:
        logger.warning("Cache warming timed out after 300s")
    except Exception:
        logger.warning("Cache warming failed", exc_info=True)
