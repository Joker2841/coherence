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
def _node_to_claim(node: Any) -> dict:
    """Normalize a graph node into a plain claim dict.

    FIRST-RUN CHECK: match attribute access to your CogneeGraph node shape. The
    memify docs show nodes exposing `node.attributes[...]`; adjust if needed.
    """
    attrs = getattr(node, "attributes", None) or {}
    get = attrs.get if hasattr(attrs, "get") else (lambda k, d=None: getattr(node, k, d))
    return {
        "id": get("id") or getattr(node, "id", None),
        "text": get("text", ""),
        "subject": get("subject", ""),
        "predicate": get("predicate", ""),
        "object": get("object", ""),
        "valid_from": get("valid_from"),
        "source": get("source"),
    }


# --------------------------------------------------------------------------
# extraction task: yields candidate PAIRS (the cost gate)
# --------------------------------------------------------------------------
async def find_candidate_pairs(subgraphs: list[Any]) -> AsyncIterator[tuple[dict, dict]]:
    """
    Receives the existing graph (already filtered to the 'claims' NodeSet via
    memify's `node_name` arg) and yields only claim pairs worth checking -- those
    sharing a subject. We never emit the full O(n^2) cross product.
    """
    claims: list[dict] = []
    for sg in subgraphs:
        nodes = getattr(sg, "nodes", {})
        iterable = nodes.values() if hasattr(nodes, "values") else nodes
        for node in iterable:
            claim = _node_to_claim(node)
            if claim["text"]:
                claims.append(claim)

    by_subject: dict[str, list[dict]] = {}
    for claim in claims:
        by_subject.setdefault(claim["subject"], []).append(claim)

    for group in by_subject.values():
        for a, b in combinations(group, 2):
            # OPTIONAL optimization: additionally gate on vector similarity of
            # a["text"] vs b["text"] to skip clearly-unrelated pairs before the LLM.
            yield (a, b)


# --------------------------------------------------------------------------
# enrichment task: detect + persist a Contradiction node
# --------------------------------------------------------------------------
async def detect_contradictions(pair: tuple[dict, dict]) -> AsyncIterator[Contradiction]:
    """
    Two-path detection:
      1. temporal supersession  -> deterministic, NO LLM
      2. semantic contradiction -> LLM, only when (1) does not fire
    Persists each Contradiction back into the graph and yields it downstream.
    """
    a, b = pair

    # Path 1: free + deterministic.
    sup = check_supersession(a, b)
    if sup:
        node = Contradiction(
            claim_a_id=a["id"],
            claim_b_id=b["id"],
            conflict_type=sup["conflict_type"],
            verdict=sup["verdict"],
            confidence=sup["confidence"],
            winner_claim_id=sup["winner_claim_id"],
        )
        await add_data_points([node])
        yield node
        return

    # Path 2: paid path, but only on a pre-filtered same-subject pair.
    verdict = await judge_contradiction(a["text"], b["text"])
    if verdict and verdict.get("contradiction"):
        node = Contradiction(
            claim_a_id=a["id"],
            claim_b_id=b["id"],
            conflict_type="semantic",
            verdict=verdict.get("reason", "Conflicting claims."),
            confidence=0.85,
        )
        await add_data_points([node])
        yield node
