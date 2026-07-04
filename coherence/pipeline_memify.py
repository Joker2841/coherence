from __future__ import annotations

import cognee
from cognee.modules.pipelines.tasks.task import Task
from cognee.tasks.storage import add_data_points

from . import rules
from .config import DATASET
from .models import Claim, Contradiction


def _claim_to_dict(c: Claim) -> dict:
    return {"id": str(getattr(c, "id", "")), "ref": getattr(c, "ref_id", "") or "",
            "subject": c.subject, "predicate": c.predicate, "object": c.object,
            "valid_from": c.valid_from}


async def prepare_claims(data):
    """memify EXTRACTION task: unwrap a single wrapped payload and forward the
    claim batch to the enrichment task."""
    if isinstance(data, dict) and "claims" in data:
        payload = data["claims"]
    else:
        payload = data
    items = payload if isinstance(payload, list) else [payload]
    flat = []
    for x in items:
        flat.extend(x if isinstance(x, list) else [x])
    claims = [c for c in flat if isinstance(c, dict)]
    print(f"[memify] extraction task -> {len(claims)} claims received")
    yield claims


def _as_claim_list(batch) -> list[dict]:
    if isinstance(batch, dict):
        if "claims" in batch and isinstance(batch["claims"], list):
            return _as_claim_list(batch["claims"])
        return [batch]
    if isinstance(batch, list):
        out = []
        for x in batch:
            if isinstance(x, dict) and "claims" in x and isinstance(x["claims"], list):
                out.extend(_as_claim_list(x["claims"]))
            elif isinstance(x, list):
                out.extend(_as_claim_list(x))
            elif isinstance(x, dict):
                out.append(x)
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


async def detect_via_memify(claims, dataset: str = DATASET):
    """Detection orchestrated as a native cognee.memify() Task pipeline (data-fed)."""
    claim_dicts = [_claim_to_dict(c) for c in claims]
    await cognee.memify(
        extraction_tasks=[Task(prepare_claims)],
        enrichment_tasks=[Task(apply_rules)],
        data=[{"claims": claim_dicts}],
        dataset=dataset,
    )