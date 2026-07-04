
from __future__ import annotations

import cognee
from cognee.modules.pipelines.tasks.task import Task
from cognee.tasks.storage import add_data_points

from . import rules
from .config import CLAIMS_NODE_SET, DATASET
from .models import Contradiction


def _node_to_claim(node) -> dict:
    """Pull a claim dict off a CogneeGraph node. Defensive about node shape
    (attributes dict vs direct attrs) -- confirm on first run via the debug line."""
    attrs = getattr(node, "attributes", None) or {}
    get = attrs.get if hasattr(attrs, "get") else (lambda k, d=None: getattr(node, k, d))
    return {
        "id": str(get("id") or getattr(node, "id", "")),
        "ref": get("ref_id") or "",
        "subject": get("subject", "") or "",
        "predicate": get("predicate", "") or "",
        "object": get("object", "") or "",
        "valid_from": get("valid_from"),
    }


async def extract_claims_from_graph(subgraphs):
    """memify EXTRACTION task: read Claim nodes off the graph, yield as one batch."""
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
            if c["subject"] and c["object"]:
                claims.append(c)
    print(f"[memify] extraction task -> {len(claims)} claim nodes in scope")
    yield claims


def _as_claim_list(batch) -> list[dict]:
    """The enrichment task receives a forwarded batch; normalize to a flat list."""
    if isinstance(batch, dict):
        return [batch]
    if isinstance(batch, list) and batch and isinstance(batch[0], dict):
        return batch
    if isinstance(batch, list) and batch and isinstance(batch[0], list):
        return batch[0]
    if isinstance(batch, list):
        out = []
        for x in batch:
            out.extend(x if isinstance(x, list) else [x])
        return [c for c in out if isinstance(c, dict)]
    return []


async def apply_rules(batch):
    """memify ENRICHMENT task: run the tested rules, persist Contradiction nodes."""
    claims = _as_claim_list(batch)
    found = []
    for d in rules.find_contradictions(claims):
        found.append(Contradiction(
            claim_a_id=d["a_id"], claim_b_id=d["b_id"],
            ref_a=d["a_ref"] or "", ref_b=d["b_ref"] or "",
            conflict_type="contradiction", confidence=d["confidence"], verdict=d["verdict"]))
    for d in rules.find_supersessions(claims):
        found.append(Contradiction(
            claim_a_id=d["older_id"], claim_b_id=d["newer_id"],
            ref_a=d["older_ref"] or "", ref_b=d["newer_ref"] or "",
            conflict_type="supersession", confidence=d["confidence"],
            winner_claim_id=d["newer_id"], verdict=d["verdict"]))
    if found:
        await add_data_points(found)
    print(f"[memify] enrichment task -> {len(found)} conflicts written to the graph")
    for f in found:
        print(f"  [{f.conflict_type.upper()}] {f.verdict}")
        yield f


async def detect_via_memify(dataset: str = DATASET):
    """Detection orchestrated as a native cognee.memify() Task pipeline."""
    await cognee.memify(
        extraction_tasks=[Task(extract_claims_from_graph)],
        enrichment_tasks=[Task(apply_rules)],
        dataset=dataset,
    )