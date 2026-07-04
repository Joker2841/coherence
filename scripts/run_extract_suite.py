"""
Extraction eval over MULTIPLE messy documents -> an aggregate recall/precision
that actually means something (vs one anecdote).

    python scripts/run_extract_suite.py      # needs Gemini configured

Matches on subject + object (the fact's identity), fuzzy/normalized, so
'the hotel roof' matches 'hotel roof'. Predicate consistency is validated
separately in the detection eval.
"""
import asyncio
import json
import re
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence.extract import extract_claims

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GT = json.loads((ROOT / "eval" / "extract_gt.json").read_text())


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _fuzzy(a, b):
    a, b = _norm(a), _norm(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def _matches(ex, gt):
    return _fuzzy(ex.get("subject"), gt["subject"]) and _fuzzy(ex.get("object"), gt["object"])


async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    tot_rec = tot_gt = tot_cor = tot_ex = 0
    for doc, gts in GT.items():
        text = (RAW / doc).read_text()
        ex = await extract_claims(text)
        rec = sum(1 for g in gts if any(_matches(e, g) for e in ex))
        cor = sum(1 for e in ex if any(_matches(e, g) for g in gts))
        print(f"  {doc:20} recall {rec}/{len(gts)}   precision {cor}/{len(ex)}")
        tot_rec += rec; tot_gt += len(gts); tot_cor += cor; tot_ex += len(ex)

    print(f"\nAGGREGATE  recall {tot_rec}/{tot_gt} = {tot_rec/tot_gt:.0%}   "
          f"precision {tot_cor}/{tot_ex} = {tot_cor/max(1,tot_ex):.0%}")
    print(f"  over {len(GT)} documents / {tot_gt} hand-labeled claims across "
          f"{len(GT)} domains")


if __name__ == "__main__":
    asyncio.run(main())