import asyncio
from coherence import config
config.setup()
from coherence.detect import run_detection
asyncio.run(run_detection())