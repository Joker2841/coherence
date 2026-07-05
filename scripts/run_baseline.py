"""
#4  Baseline: plain Cognee vs Coherence across 3 contradiction domains.

    python scripts/run_baseline.py     (needs an LLM: cognify + search)
"""
import asyncio
import json
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence.detect import detect
from coherence.guardrail import SafeAgent
from coherence.ingest import ingest_statements

DATA = Path(__file__).resolve().parent.parent / "data"

# (subject, predicate, natural-language question)
SCENARIOS = [
    ("patient_017",  "blood_type", "What is patient_017's blood type?"),
    ("AcmeCorp",     "revenue_q3", "What is AcmeCorp's Q3 revenue?"),
    ("flight_aa100", "status",     "What is the status of flight AA100?"),
]
KEYS = {(s, p) for s, p, _ in SCENARIOS}


def _plain(ans):
    try:
        if isinstance(ans, list) and ans and isinstance(ans[0], dict):
            return ans[0].get("search_result", ans)
    except Exception:
        pass
    return ans


async def main():
    allrecs = json.loads((DATA / "eval_suite.json").read_text())
    records = [r for r in allrecs if (r["subject"], r["predicate"]) in KEYS]  # ~7 claims
    bar = "=" * 66

    # ---- Phase 1: plain Cognee (add + cognify + search) ----
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    for r in records:
        await cognee.add(r["text"])
    await cognee.cognify()
    print(f"\n{bar}\n  WITHOUT Coherence  (plain Cognee recall)\n{bar}")
    for subj, pred, q in SCENARIOS:
        ans = await cognee.search(query_text=q)
        print(f"[q] {q}")
        print(f"    plain cognee -> {_plain(ans)}   (silent; no signal the records conflict)")

    # ---- Phase 2: Coherence ----
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    claims = await ingest_statements(records)
    conflicts = await detect(claims)
    agent = SafeAgent()
    print(f"\n{bar}\n  WITH Coherence\n{bar}")
    for subj, pred, q in SCENARIOS:
        print(f"[q] {q}")
        print(agent.act("answer", subj, pred, claims, conflicts).render())
        print()

    print(f"{bar}\n  Same records, 3 domains. Plain Cognee gambles; Coherence refuses.\n{bar}\n")


if __name__ == "__main__":
    asyncio.run(main())