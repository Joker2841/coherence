import argparse, asyncio, json
from pathlib import Path
from coherence import config
config.setup()
import cognee
from coherence.ingest import ingest_statements
from coherence.detect import detect

DATA = Path(__file__).resolve().parent.parent / "data"
LABELED = Path(__file__).resolve().parent / "labeled_set.json"


def score(detected, labeled):
    k = lambda p: frozenset((p["a"], p["b"]))
    pos = {k(p) for p in labeled if p["is_contradiction"]}
    neg = {k(p) for p in labeled if not p["is_contradiction"]}
    tp, fn = len(detected & pos), len(pos - detected)
    fp = len(detected & neg) + len(detected - (pos | neg))
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return P, R, F, tp, fp, fn, sorted(tuple(x) for x in (pos - detected))


async def run(dataset, use_llm):
    await cognee.prune.prune_data(); await cognee.prune.prune_system(metadata=True)
    statements = json.loads((DATA / f"{dataset}.json").read_text())
    ids = {s["id"] for s in statements}
    conflicts = await detect(await ingest_statements(statements), use_llm=use_llm)
    detected = {frozenset((c.ref_a, c.ref_b)) for c in conflicts if c.ref_a and c.ref_b}
    labeled = [p for p in json.loads(LABELED.read_text())["pairs"]
               if p["a"] in ids and p["b"] in ids]
    P, R, F, tp, fp, fn, missed = score(detected, labeled)
    print(f"\n=== {dataset}  (LLM {'ON' if use_llm else 'off'}) ===")
    print(f"precision {P:.0%}   recall {R:.0%}   f1 {F:.2f}   (TP={tp} FP={fp} FN={fn})")
    if missed: print(f"missed: {missed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="doug_witnesses")
    ap.add_argument("--use-llm", action="store_true")
    a = ap.parse_args()
    asyncio.run(run(a.dataset, a.use_llm))