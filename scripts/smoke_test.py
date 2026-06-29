import asyncio
from coherence import config
config.setup()
import cognee

async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await cognee.add("Doug is the groom. The wedding is Sunday.")
    await cognee.cognify()
    print(await cognee.search(query_text="Who is the groom?"))

asyncio.run(main())