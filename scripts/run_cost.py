"""
#5  Real LLM-cost report: how much of detection avoids the LLM entirely.

    python scripts/run_cost.py [dataset]     (embeddings only -- no LLM key)

A naive "LLM-per-pair" checker would send every same-subject claim pair to an
LLM. Coherence resolves same-predicate conflicts deterministically (0 LLM) and
sends only the vector-gated cross-predicate residue to the model.
"""
import asyncio
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence import rules
from coherence.gate import VectorGate
from coherence.ingest import ingest_statements

DATA = Path(__file__).resolve().parent.parent / "data"


def _d(c):
    return {"id": str(getattr(c, "id", "")), "subject": c.subject,
            "predicate": c.predicate, "object": c.object, "valid_from": c.valid_from,
            "text": c.text}


async def main(dataset):
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    items = [_d(c) for c in await ingest_statements(json.loads((DATA / f"{dataset}.json").read_text()))]

    # deterministic conflicts -> ZERO LLM calls
    det = rules.find_contradictions(items) + rules.find_supersessions(items)
    flagged = set()
    for d in det:
        a = d.get("a_id") or d.get("older_id")
        b = d.get("b_id") or d.get("newer_id")
        flagged.add(frozenset((a, b)))

    by_subject = defaultdict(list)
    for c in items:
        by_subject[c["subject"]].append(c)
    naive = sum(len(list(combinations(g, 2))) for g in by_subject.values())

    # our LLM calls = vector-gated cross-predicate survivors
    gate = VectorGate()
    llm_calls = 0
    for group in by_subject.values():
        for i, a in enumerate(group):
            partners = [b for b in group[i + 1:]
                        if frozenset((a["id"], b["id"])) not in flagged
                        and a["predicate"] != b["predicate"]]
            if partners:
                llm_calls += len(await gate.close_partners(a, partners))

    reduction = (1 - llm_calls / naive) if naive else 1.0
    print(f"\n=== LLM-cost report: {dataset} ({len(items)} claims) ===")
    print(f"  deterministic conflicts (0 LLM calls) : {len(det)}")
    print(f"  naive 'LLM-per-pair' would call        : {naive}")
    print(f"  Coherence actually calls the LLM       : {llm_calls}")
    print(f"  ==> LLM-call reduction                 : {reduction:.0%}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "eval_suite"))