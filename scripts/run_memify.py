"""
Showcase: detection as a native Cognee memify pipeline (data-fed).

    python scripts/run_memify.py [doug_witnesses|agent_memory|eval_suite]
"""
import asyncio
import json
import sys
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence.ingest import ingest_statements
from coherence.pipeline_memify import detect_via_memify

DATA = Path(__file__).resolve().parent.parent / "data"


async def main(dataset: str):
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    claims = await ingest_statements(json.loads((DATA / f"{dataset}.json").read_text()))
    print(f"\n=== detection via cognee.memify() Task pipeline ({dataset}) ===")
    await detect_via_memify(claims)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "doug_witnesses"))