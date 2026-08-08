"""Deprecated: runtime cache warming / package install removed.

Packages are installed only at image build time into ``/opt/code-tools-env``.
This module remains so older imports do not break; ``warm_cache`` is a no-op.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def warm_cache(*_args, **_kwargs) -> None:
    """No-op. Runtime package downloads are forbidden."""
    logger.info(
        "warm_cache skipped: offline sandbox uses a preinstalled env "
        "(/opt/code-tools-env); no runtime installs"
    )
