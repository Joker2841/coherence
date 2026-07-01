"""
FastAPI backend for the Coherence debugger.

Holds the last ingest+detect result in a small in-memory store (the
demo is single-user), so /graph and /conflicts serve real data with no need to
re-query the graph DB.

Run (single worker for the demo):
    uvicorn coherence.server:app --port 8000
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config

config.setup()  # configure the free stack BEFORE any cognee op

from .detect import detect as run_detection      # noqa: E402
from .ingest import ingest_statements            # noqa: E402
from .resolve import resolve_conflict            # noqa: E402

app = FastAPI(title="Coherence -- AI memory integrity layer")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LABELED = Path(__file__).resolve().parent.parent / "eval" / "labeled_set.json"


# ------------------------------------------------------------------ store
class Store:
    dataset: str | None = None
    claims: list = []          # list[Claim]
    conflicts: list = []       # list[Contradiction]
    metrics: dict = {}
    source_trust: dict = {}    # source name -> float


STORE = Store()


# ------------------------------------------------------------------ helpers
def _claims_by_id() -> dict:
    return {str(c.id): c for c in STORE.claims}


def _superseded_ids() -> set:
    return {c.claim_a_id for c in STORE.conflicts if c.conflict_type == "supersession"}


def _status(claim, superseded: set) -> str:
    if getattr(claim, "status", "active") == "retracted":
        return "retracted"
    if str(claim.id) in superseded:
        return "superseded"
    return "active"


def _nodes() -> list:
    superseded = _superseded_ids()
    return [{
        "id": str(c.id), "type": "claim",
        "subject": c.subject, "predicate": c.predicate, "object": c.object,
        "text": c.text, "valid_from": c.valid_from, "source": c.source,
        "status": _status(c, superseded),
        "source_trust": STORE.source_trust.get(c.source, 1.0),
    } for c in STORE.claims]


def _edges() -> list:
    edges = []
    for i, c in enumerate(STORE.conflicts):
        if c.conflict_type == "supersession":
            edges.append({
                "id": f"e{i}", "source": c.winner_claim_id or c.claim_b_id,
                "target": c.claim_a_id, "type": "supersedes",
                "label": "latest value", "confidence": c.confidence, "resolved": c.resolved,
            })
        else:  # contradiction | semantic
            edges.append({
                "id": f"e{i}", "source": c.claim_a_id, "target": c.claim_b_id,
                "type": "contradicts", "label": c.verdict[:70],
                "confidence": c.confidence, "resolved": c.resolved,
            })
    return edges


def _conflict_items() -> list:
    by_id = _claims_by_id()
    out = []
    for c in STORE.conflicts:
        a, b = by_id.get(c.claim_a_id), by_id.get(c.claim_b_id)
        out.append({
            "id": str(c.id), "type": c.conflict_type, "verdict": c.verdict,
            "confidence": c.confidence, "resolved": c.resolved,
            "winner_id": c.winner_claim_id,
            "detected_by": "llm" if c.conflict_type == "semantic" else "deterministic",
            "claim_a": {"id": c.claim_a_id, "object": a.object if a else "", "source": a.source if a else ""},
            "claim_b": {"id": c.claim_b_id, "object": b.object if b else "", "source": b.source if b else ""},
        })
    return out


def _score(detected: set, labeled: list) -> dict:
    pos = {frozenset((p["a"], p["b"])) for p in labeled if p["is_contradiction"]}
    neg = {frozenset((p["a"], p["b"])) for p in labeled if not p["is_contradiction"]}
    tp, fn = len(detected & pos), len(pos - detected)
    fp = len(detected & neg) + len(detected - (pos | neg))
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return {"precision": round(P, 3), "recall": round(R, 3), "f1": round(F, 3),
            "tp": tp, "fp": fp, "fn": fn}


def _counts() -> dict:
    kinds = defaultdict(int)
    for c in STORE.conflicts:
        kinds[c.conflict_type] += 1
    return {"contradictions": kinds["contradiction"],
            "supersessions": kinds["supersession"],
            "semantic": kinds["semantic"]}


# ------------------------------------------------------------------ models
class ResolveReq(BaseModel):
    conflict_id: str
    winner_claim_id: str
    loser_claim_id: str


# ------------------------------------------------------------------ endpoints
@app.post("/ingest/{dataset_name}")
async def ingest(dataset_name: str):
    statements = json.loads((DATA_DIR / f"{dataset_name}.json").read_text())
    STORE.dataset = dataset_name
    STORE.claims = await ingest_statements(statements)
    STORE.conflicts, STORE.metrics, STORE.source_trust = [], {}, {}
    return {"ingested": len(STORE.claims), "dataset": dataset_name}


@app.post("/detect")
async def detect(use_llm: bool = False):
    STORE.conflicts = await run_detection(STORE.claims, use_llm=use_llm)
    ids = {getattr(c, "ref_id", None) for c in STORE.claims}
    detected = {frozenset((c.ref_a, c.ref_b)) for c in STORE.conflicts if c.ref_a and c.ref_b}
    labeled = [p for p in json.loads(LABELED.read_text())["pairs"]
               if p["a"] in ids and p["b"] in ids]
    STORE.metrics = _score(detected, labeled)
    return {"conflicts": len(STORE.conflicts), **_counts()}


@app.get("/graph")
async def graph():
    return {"dataset": STORE.dataset, "nodes": _nodes(), "edges": _edges()}


@app.get("/conflicts")
async def conflicts():
    return {"dataset": STORE.dataset, "metrics": STORE.metrics, "conflicts": _conflict_items()}


@app.post("/resolve")
async def resolve(req: ResolveReq):
    # Real Cognee side-effects (improve feedback + forget); best-effort.
    await resolve_conflict(req.winner_claim_id, req.loser_claim_id)
    # UI-side state so /graph and /conflicts reflect the resolution immediately.
    loser = _claims_by_id().get(req.loser_claim_id)
    if loser is not None:
        loser.status = "retracted"
        cur = STORE.source_trust.get(loser.source, 1.0)
        STORE.source_trust[loser.source] = round(max(0.0, cur - 0.34), 2)
    for c in STORE.conflicts:
        if str(c.id) == req.conflict_id:
            c.resolved = True
            c.winner_claim_id = req.winner_claim_id
    return {"status": "resolved",
            "winner_claim_id": req.winner_claim_id,
            "removed_claim_id": req.loser_claim_id}