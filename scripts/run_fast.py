import asyncio, json, sys
from pathlib import Path
from coherence import config
config.setup()
import cognee
from coherence.ingest import ingest_statements
from coherence.detect import detect

DATA = Path(__file__).resolve().parent.parent / "data"

async def run(name):
    await cognee.prune.prune_data(); await cognee.prune.prune_system(metadata=True)
    claims = await ingest_statements(json.loads((DATA / f"{name}.json").read_text()))
    print(f"\n--- conflicts in {name} ---")
    await detect(claims)

asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "doug_witnesses"))