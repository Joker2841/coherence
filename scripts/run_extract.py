"""
End-to-end experiment: messy document -> extract -> detect, scored against the
hand-authored ground truth.

    python scripts/run_extract.py

Reports (1) extraction precision/recall vs your structured claims, and
(2) whether detection still finds the conflicts from raw text.
"""
import asyncio
import json
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence.detect import detect
from coherence.extract import extract_claims
from coherence.ingest import ingest_statements

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "doug_raw.txt"
GT = ROOT / "data" / "doug_witnesses.json"


def _norm(s):
    return (s or "").strip().lower()


def _obj_match(a, b):
    a, b = _norm(a), _norm(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def _claim_match(ex, gt):
    return (_norm(ex["subject"]) == _norm(gt["subject"])
            and _norm(ex["predicate"]) == _norm(gt["predicate"])
            and _obj_match(ex["object"], gt["object"]))


async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    doc = RAW.read_text()
    gt = json.loads(GT.read_text())

    print("=== EXTRACTING from messy document ===")
    extracted = await extract_claims(doc)
    for c in extracted:
        print(f"  [{c['source']:>9}] {c['subject']}.{c['predicate']} = {c['object']}  ({c.get('time')})")

    recovered = sum(1 for g in gt if any(_claim_match(e, g) for e in extracted))
    correct = sum(1 for e in extracted if any(_claim_match(e, g) for g in gt))
    print(f"\nEXTRACTION  recall {recovered}/{len(gt)} = {recovered/len(gt):.0%}   "
          f"precision {correct}/{len(extracted)} = {correct/max(1,len(extracted)):.0%}")

    print("\n=== DETECTION on the extracted claims (end-to-end, raw text in) ===")
    claims = await ingest_statements(extracted)
    conflicts = await detect(claims, use_llm=False)
    print(f"\nEND-TO-END: {len(conflicts)} conflicts detected straight from the document.")


if __name__ == "__main__":
    asyncio.run(main())