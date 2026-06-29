"""Wipe all Cognee state for a clean demo run.

    python scripts/reset.py
"""
from __future__ import annotations

import asyncio

from coherence import config

config.setup()

import cognee  # noqa: E402


async def main() -> None:
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("[coherence] state reset.")


if __name__ == "__main__":
    asyncio.run(main())
