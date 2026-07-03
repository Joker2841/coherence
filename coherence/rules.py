"""
Pure, dependency-free deterministic core: conflict detection, predicate
canonicalization, and eval scoring. NO cognee / LLM / pydantic imports, so it
runs anywhere and every metric is unit-testable. detect.py wraps these with
DataPoint persistence; extract.py imports canon_predicate from here.

Claims are plain dicts: {id, subject, predicate, object, valid_from, ref?}.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

PREDICATE_CANON = {
    "location": {"location", "whereabouts", "position", "place", "located",
                 "seen at", "spotted", "sighting", "was at", "presence"},
    "role": {"role", "title", "job"},
    "event": {"event", "activity", "happening", "party"},
    "manager": {"manager", "boss", "supervisor", "reports to", "reporting"},
    "diet": {"diet", "dietary", "food preference", "eats"},
    "date": {"date", "scheduled", "day", "when", "meeting date"},
}


def canon_predicate(pred: str) -> str:
    p = (pred or "").strip().lower()
    for canon, syns in PREDICATE_CANON.items():
        if p == canon or p in syns:
            return canon
    return p


def find_contradictions(claims: list[dict]) -> list[dict]:
    """Same subject+predicate+timestamp, different object => irreducible conflict.
    Claims with an unknown (None) timestamp are NOT treated as 'same time'."""
    out = []
    groups = defaultdict(list)
    for c in claims:
        groups[(c["subject"], c["predicate"])].append(c)
    for (subj, pred), group in groups.items():
        by_time = defaultdict(list)
        for c in group:
            by_time[c.get("valid_from")].append(c)
        for t, same_time in by_time.items():
            if t is None:                       # unknown time != same time
                continue
            for a, b in combinations(same_time, 2):
                if a["object"] != b["object"]:
                    out.append({
                        "a_id": a["id"], "b_id": b["id"],
                        "a_ref": a.get("ref"), "b_ref": b.get("ref"),
                        "subject": subj, "predicate": pred, "type": "contradiction",
                        "confidence": 1.0,
                        "verdict": f"{subj}.{pred} is both '{a['object']}' and '{b['object']}' at {t}.",
                    })
    return out


def find_supersessions(claims: list[dict]) -> list[dict]:
    """Latest-timestamp value supersedes earlier different values (same subj+pred)."""
    out = []
    groups = defaultdict(list)
    for c in claims:
        groups[(c["subject"], c["predicate"])].append(c)
    for (subj, pred), group in groups.items():
        dated = sorted([c for c in group if c.get("valid_from")], key=lambda c: c["valid_from"])
        if len(dated) < 2:
            continue
        latest = dated[-1]
        for older in dated[:-1]:
            if older["object"] != latest["object"] and older["valid_from"] != latest["valid_from"]:
                out.append({
                    "older_id": older["id"], "newer_id": latest["id"],
                    "older_ref": older.get("ref"), "newer_ref": latest.get("ref"),
                    "subject": subj, "predicate": pred, "type": "supersession",
                    "confidence": 1.0,
                    "verdict": f"{subj}.{pred}: '{older['object']}' ({older['valid_from']}) "
                               f"superseded by '{latest['object']}' ({latest['valid_from']}).",
                })
    return out


def score(detected_pairs: set, labeled: list[dict]) -> dict:
    """detected_pairs: set[frozenset(refA,refB)]; labeled: [{a,b,is_contradiction}]."""
    pos = {frozenset((p["a"], p["b"])) for p in labeled if p["is_contradiction"]}
    neg = {frozenset((p["a"], p["b"])) for p in labeled if not p["is_contradiction"]}
    tp, fn = len(detected_pairs & pos), len(pos - detected_pairs)
    fp = len(detected_pairs & neg) + len(detected_pairs - (pos | neg))
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return {"precision": round(P, 3), "recall": round(R, 3), "f1": round(F, 3),
            "tp": tp, "fp": fp, "fn": fn}