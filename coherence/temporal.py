"""
Deterministic temporal-supersession detection -- NO LLM, so it is free and
perfectly reliable.

If two claims share the same subject + predicate but differ in object and have
different timestamps, the newer one supersedes the older. This covers the
'release shifted from June to August' / 'meeting moved to Friday' class of
conflict at zero token cost.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


def _parse(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def check_supersession(claim_a: dict, claim_b: dict) -> Optional[dict]:
    """Return a verdict dict if one claim supersedes the other, else None."""
    if claim_a.get("subject") != claim_b.get("subject"):
        return None
    if claim_a.get("predicate") != claim_b.get("predicate"):
        return None
    if claim_a.get("object") == claim_b.get("object"):
        return None  # same value -> no conflict

    ta, tb = _parse(claim_a.get("valid_from")), _parse(claim_b.get("valid_from"))
    if ta is None or tb is None or ta == tb:
        return None  # cannot order in time -> leave for the semantic path

    newer, older = (claim_a, claim_b) if ta > tb else (claim_b, claim_a)
    return {
        "conflict_type": "temporal_supersession",
        "winner_claim_id": newer.get("id"),
        "loser_claim_id": older.get("id"),
        "confidence": 1.0,
        "verdict": (
            f"'{older.get('object')}' ({older.get('valid_from')}) superseded by "
            f"'{newer.get('object')}' ({newer.get('valid_from')}) for "
            f"{newer.get('subject')}.{newer.get('predicate')}."
        ),
    }
