"""
Extraction eval — DEBUG mode. Prints extracted claims + unmatched GT per doc so
we can see WHY a doc scored low (subject-slicing vs genuine miss).

    python scripts/run_extract_suite_debug.py
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

    for doc, gts in GT.items():
        text = (RAW / doc).read_text()
        ex = await extract_claims(text)

        print(f"\n================  {doc}  ================")
        print("EXTRACTED:")
        for e in ex:
            print(f"   . {e.get('subject')} | {e.get('predicate')} | {e.get('object')}")
        missed = [g for g in gts if not any(_matches(e, g) for e in ex)]
        print("UNMATCHED GROUND TRUTH:")
        for g in missed:
            print(f"   x {g['subject']} | {g['predicate']} | {g['object']}")
        rec = len(gts) - len(missed)
        cor = sum(1 for e in ex if any(_matches(e, g) for g in gts))
        print(f"recall {rec}/{len(gts)}   precision {cor}/{len(ex)}")


if __name__ == "__main__":
    asyncio.run(main())