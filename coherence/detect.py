"""
Detection = tested deterministic core (rules.py) + optional vector-gated semantic
pass. detect() wraps the pure rule functions with DataPoint persistence, so the
logic that ships is exactly the logic covered by tests/.
"""
from __future__ import annotations

from collections import defaultdict

from cognee.tasks.storage import add_data_points

from . import rules
from .gate import VectorGate
from .llm import judge_contradiction
from .models import Claim, Contradiction


def _d(c: Claim) -> dict:
    return {"id": str(getattr(c, "id", "")), "ref": getattr(c, "ref_id", "") or "",
            "subject": c.subject, "predicate": c.predicate, "object": c.object,
            "valid_from": c.valid_from, "text": c.text}


async def detect(claims: list[Claim], use_llm: bool = False) -> list[Contradiction]:
    items = [_d(c) for c in claims]
    found: list[Contradiction] = []
    flagged: set[frozenset] = set()

    # ---- deterministic core (pure, unit-tested in tests/test_rules.py) ----
    for d in rules.find_contradictions(items):
        found.append(Contradiction(
            claim_a_id=d["a_id"], claim_b_id=d["b_id"],
            ref_a=d["a_ref"] or "", ref_b=d["b_ref"] or "",
            conflict_type="contradiction", confidence=d["confidence"], verdict=d["verdict"]))
        flagged.add(frozenset((d["a_id"], d["b_id"])))
        print(f"[CONTRADICTION] {d['verdict']}")

    for d in rules.find_supersessions(items):
        found.append(Contradiction(
            claim_a_id=d["older_id"], claim_b_id=d["newer_id"],
            ref_a=d["older_ref"] or "", ref_b=d["newer_ref"] or "",
            conflict_type="supersession", confidence=d["confidence"],
            winner_claim_id=d["newer_id"], verdict=d["verdict"]))
        flagged.add(frozenset((d["older_id"], d["newer_id"])))
        print(f"[SUPERSESSION] {d['verdict']}")

    # ---- vector-gated semantic pass (cross-predicate residue) ----
    if use_llm:
        gate = VectorGate()
        by_subject = defaultdict(list)
        for c in items:
            by_subject[c["subject"]].append(c)
        for subj, group in by_subject.items():
            for i, a in enumerate(group):
                partners = [b for b in group[i + 1:]
                            if frozenset((a["id"], b["id"])) not in flagged
                            and a["predicate"] != b["predicate"]]
                if not partners:
                    continue
                for b, sim in await gate.close_partners(a, partners):
                    verdict = await judge_contradiction(a, b)
                    if verdict and verdict.get("contradiction"):
                        found.append(Contradiction(
                            claim_a_id=a["id"], claim_b_id=b["id"],
                            ref_a=a["ref"], ref_b=b["ref"], conflict_type="semantic",
                            confidence=round(0.6 + 0.4 * sim, 2),
                            verdict=verdict.get("reason", "Conflicting claims.")))
                        flagged.add(frozenset((a["id"], b["id"])))
                        print(f"[SEMANTIC] {subj}: '{a['object']}' vs '{b['object']}' (sim={sim:.2f})")

    if found:
        await add_data_points(found)
    n_c = sum(1 for f in found if f.conflict_type == "contradiction")
    n_su = sum(1 for f in found if f.conflict_type == "supersession")
    n_se = sum(1 for f in found if f.conflict_type == "semantic")
    print(f"\n[coherence] {len(found)} conflicts "
          f"({n_c} contradiction, {n_su} supersession, {n_se} semantic)")
    return found