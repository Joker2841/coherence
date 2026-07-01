"""Detection: deterministic rules (instant, no LLM) + an optional vector-gated
semantic pass for cross-predicate conflicts structure can't see."""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
from cognee.tasks.storage import add_data_points
from .models import Claim, Contradiction
from .gate import VectorGate
from .llm import judge_contradiction


def _d(c: Claim) -> dict:
    return {"id": str(getattr(c, "id", "")), "ref": getattr(c, "ref_id", "") or "",
            "text": c.text, "subject": c.subject, "predicate": c.predicate,
            "object": c.object, "valid_from": c.valid_from}


async def detect(claims: list[Claim], use_llm: bool = False) -> list[Contradiction]:
    items = [_d(c) for c in claims]
    found: list[Contradiction] = []
    flagged: set[frozenset] = set()

    # ---- Deterministic layer (same subject + predicate) ----
    groups = defaultdict(list)
    for c in items:
        groups[(c["subject"], c["predicate"])].append(c)

    for (subj, pred), group in groups.items():
        by_time = defaultdict(list)
        for c in group:
            by_time[c["valid_from"]].append(c)
        for t, same_time in by_time.items():
            for a, b in combinations(same_time, 2):
                if a["object"] != b["object"]:
                    found.append(Contradiction(
                        claim_a_id=a["id"], claim_b_id=b["id"], ref_a=a["ref"], ref_b=b["ref"],
                        conflict_type="contradiction", confidence=1.0,
                        verdict=f"{subj}.{pred} is both '{a['object']}' and '{b['object']}' at {t}."))
                    flagged.add(frozenset((a["id"], b["id"])))
                    print(f"[CONTRADICTION] {subj}.{pred}: '{a['object']}' vs '{b['object']}' @ {t}")

        dated = sorted([c for c in group if c["valid_from"]], key=lambda c: c["valid_from"])
        if len(dated) >= 2:
            latest = dated[-1]
            for older in dated[:-1]:
                if older["object"] != latest["object"] and older["valid_from"] != latest["valid_from"]:
                    found.append(Contradiction(
                        claim_a_id=older["id"], claim_b_id=latest["id"],
                        ref_a=older["ref"], ref_b=latest["ref"],
                        conflict_type="supersession", confidence=1.0, winner_claim_id=latest["id"],
                        verdict=f"{subj}.{pred}: '{older['object']}' ({older['valid_from']}) "
                                f"superseded by '{latest['object']}' ({latest['valid_from']})."))
                    flagged.add(frozenset((older["id"], latest["id"])))
                    print(f"[SUPERSESSION] {subj}.{pred}: '{older['object']}' -> '{latest['object']}'")

    # ---- Vector-gated semantic layer (same subject, any predicate) ----
    if use_llm:
        gate = VectorGate()
        by_subject = defaultdict(list)
        for c in items:
            by_subject[c["subject"]].append(c)
        for subj, group in by_subject.items():
            for i, a in enumerate(group):
                partners = [b for b in group[i + 1:]
                    if frozenset((a["id"], b["id"])) not in flagged
                    and a["predicate"] != b["predicate"]]     # LLM owns CROSS-predicate only
                if not partners:
                    continue
                for b, sim in await gate.close_partners(a, partners):
                    verdict = await judge_contradiction(a, b)
                    if verdict and verdict.get("contradiction"):
                        found.append(Contradiction(
                            claim_a_id=a["id"], claim_b_id=b["id"], ref_a=a["ref"], ref_b=b["ref"],
                            conflict_type="semantic", confidence=round(0.6 + 0.4 * sim, 2),
                            verdict=verdict.get("reason", "Conflicting claims.")))
                        flagged.add(frozenset((a["id"], b["id"])))
                        print(f"[SEMANTIC] {subj}: '{a['object']}' vs '{b['object']}' "
                              f"(sim={sim:.2f}) -> {verdict.get('reason','')[:70]}")

    if found:
        await add_data_points(found)
    n_c = sum(1 for f in found if f.conflict_type == "contradiction")
    n_su = sum(1 for f in found if f.conflict_type == "supersession")
    n_se = sum(1 for f in found if f.conflict_type == "semantic")
    print(f"\n[coherence] {len(found)} conflicts "
          f"({n_c} contradiction, {n_su} supersession, {n_se} semantic)")
    return found