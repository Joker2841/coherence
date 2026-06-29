"""
End-to-end demo runner.

    python scripts/run_demo.py --dataset doug_witnesses --query "Where is Doug?"
    python scripts/run_demo.py --dataset agent_memory   --query "When is the Q3 review?"

Flow: reset -> ingest -> build temporal graph -> detect contradictions -> query.
Resolution is exercised through the API / debugger (POST /resolve).
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from coherence import config

config.setup()

import cognee  # noqa: E402

from coherence.detect import run_detection  # noqa: E402
from coherence.ingest import ingest_statements  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def run(dataset_name: str, query: str) -> None:
    statements = json.loads((DATA_DIR / f"{dataset_name}.json").read_text())

    print("\n[1/4] reset state")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    print(f"[2/4] ingest {len(statements)} statements + build temporal graph")
    await ingest_statements(statements)

    print("[3/4] detect contradictions (temporal-first, LLM only on candidates)")
    await run_detection()

    print(f"[4/4] query: {query!r}")
    answer = await cognee.search(query_text=query)

    print("\n--- ANSWER ---")
    for row in (answer if isinstance(answer, list) else [answer]):
        print(row)
    print(
        "\nStart the debugger to inspect conflicts and resolve them:"
        "\n    uvicorn coherence.server:app --reload --port 8000\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="doug_witnesses")
    parser.add_argument("--query", default="Where is Doug?")
    args = parser.parse_args()
    asyncio.run(run(args.dataset, args.query))
