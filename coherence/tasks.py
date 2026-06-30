"""
Phase 3: the custom memify pipeline -- extraction + enrichment tasks.

We extend memify the way it is designed to be extended (Task-wrapped async
generators that forward data down the pipeline), rather than reimplementing
graph plumbing.

  extraction_task -> find_candidate_pairs  (cheap: group by subject, prefilter)
  enrichment_task -> detect_contradictions (temporal first, LLM only if needed)
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, AsyncIterator

from cognee.tasks.storage import add_data_points

from .llm import judge_contradiction
from .models import Contradiction
from .temporal import check_supersession


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _node_to_claim(node):
    """Normalize a graph node into a plain claim dict."""
    attrs = getattr(node, "attributes", None)
    get = attrs.get if isinstance(attrs, dict) else (lambda k, d=None: getattr(node, k, d))
    return {
        "id": get("id") or getattr(node, "id", None),
        "text": get("text", "") or get("name", "") or "",
        "subject": get("subject", "") or "",
        "predicate": get("predicate", "") or "",
        "object": get("object", "") or "",
        "valid_from": get("valid_from"),
        "source": get("source"),
    }


def _as_pairs(obj):
    """Cognee hands the next task a BATCH (list). Accept every shape it might use."""
    def is_pair(x):
        return isinstance(x, (tuple, list)) and len(x) == 2 and all(isinstance(i, dict) for i in x)
    if is_pair(obj):
        return [tuple(obj)]
    if isinstance(obj, (list, tuple)):
        return [tuple(i) for i in obj if is_pair(i)]
    return []


async def find_candidate_pairs(subgraphs):
    """Extraction task: yield candidate claim PAIRS (same subject) worth checking."""
    if not isinstance(subgraphs, list):
        subgraphs = [subgraphs]

    claims = []
    for sg in subgraphs:
        nodes = getattr(sg, "nodes", None)
        if nodes is None:
            iterable = [sg]
        elif hasattr(nodes, "values"):
            iterable = nodes.values()
        else:
            iterable = nodes
        for node in iterable:
            c = _node_to_claim(node)
            if c["text"] or c["subject"]:
                claims.append(c)

    # ---- DEBUG (delete once verified) ----
    print(f"\n[debug] {len(claims)} claim nodes in scope")
    for c in claims[:4]:
        print(f"[debug]   subj={c['subject']!r} pred={c['predicate']!r} "
              f"obj={c['object']!r} from={c['valid_from']!r} text={c['text'][:70]!r}")
    # --------------------------------------

    by_subject = {}
    for c in claims:
        by_subject.setdefault(c["subject"], []).append(c)

    pairs = 0
    for group in by_subject.values():
        for a, b in combinations(group, 2):
            pairs += 1
            yield (a, b)
    print(f"[debug] yielded {pairs} candidate pairs\n")


async def detect_contradictions(batch):
    """Enrichment task: receives a BATCH (list) of candidate pairs, not one pair."""
    for a, b in _as_pairs(batch):
        sup = check_supersession(a, b)
        if sup:
            node = Contradiction(
                claim_a_id=a.get("id", ""), claim_b_id=b.get("id", ""),
                conflict_type=sup["conflict_type"], verdict=sup["verdict"],
                confidence=sup["confidence"], winner_claim_id=sup["winner_claim_id"],
            )
            await add_data_points([node])
            print(f"[debug] CONFLICT temporal: {sup['verdict']}")
            yield node
            continue

        verdict = await judge_contradiction(a.get("text", ""), b.get("text", ""))
        if verdict and verdict.get("contradiction"):
            node = Contradiction(
                claim_a_id=a.get("id", ""), claim_b_id=b.get("id", ""),
                conflict_type="semantic",
                verdict=verdict.get("reason", "Conflicting claims."), confidence=0.85,
            )
            await add_data_points([node])
            print(f"[debug] CONFLICT semantic: {verdict.get('reason')}")
            yield node