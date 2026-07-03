"""
FastAPI backend for the Coherence debugger.

Serves the API_CONTRACT shapes. Holds the last ingest+detect result in an
in-memory store. Source-trust is learned deterministically from resolutions
(see trust.py) and flows through the existing `source_trust` field, so the
frontend needs no change. resolve_conflict() still fires improve()+forget()
for real on every resolution.

Run (single worker):  uvicorn coherence.server:app --port 8000
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config

config.setup()

from .detect import detect as run_detection      # noqa: E402
from .ingest import ingest_statements            # noqa: E402
from .resolve import resolve_conflict            # noqa: E402
from .trust import TrustLedger                   # noqa: E402

app = FastAPI(title="Coherence -- AI memory integrity layer")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LABELED = Path(__file__).resolve().parent.parent / "eval" / "labeled_set.json"

# conflict types where one party is genuinely WRONG -> loser's source loses trust.
# Supersession is excluded: being outdated is not being wrong.
_TRUST_MOVING = {"contradiction", "semantic"}


class Store:
    dataset: str | None = None
    claims: list = []
    conflicts: list = []
    metrics: dict = {}
    ledger: TrustLedger = TrustLedger()


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
        "source_trust": STORE.ledger.trust(c.source),
    } for c in STORE.claims]


def _edges() -> list:
    edges = []
    for i, c in enumerate(STORE.conflicts):
        if c.conflict_type == "supersession":
            edges.append({"id": f"e{i}", "source": c.winner_claim_id or c.claim_b_id,
                          "target": c.claim_a_id, "type": "supersedes",
                          "label": "latest value", "confidence": c.confidence, "resolved": c.resolved})
        else:
            edges.append({"id": f"e{i}", "source": c.claim_a_id, "target": c.claim_b_id,
                          "type": "contradicts", "label": c.verdict[:70],
                          "confidence": c.confidence, "resolved": c.resolved})
    return edges


def _conflict_items() -> list:
    by_id = _claims_by_id()
    out = []
    for c in STORE.conflicts:
        a, b = by_id.get(c.claim_a_id), by_id.get(c.claim_b_id)
        out.append({
            "id": str(c.id), "type": c.conflict_type, "verdict": c.verdict,
            "confidence": c.confidence, "resolved": c.resolved, "winner_id": c.winner_claim_id,
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
            "supersessions": kinds["supersession"], "semantic": kinds["semantic"]}


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
    STORE.conflicts, STORE.metrics = [], {}
    STORE.ledger = TrustLedger()               # fresh ledger per dataset
    for c in STORE.claims:
        STORE.ledger.register(c.source)        # everyone starts at trust 1.0
    return {"ingested": len(STORE.claims), "dataset": dataset_name}


@app.post("/detect")
async def detect(use_llm: bool = False):
    STORE.conflicts = await run_detection(STORE.claims, use_llm=use_llm)
    ids = {getattr(c, "ref_id", None) for c in STORE.claims}
    detected = {frozenset((c.ref_a, c.ref_b)) for c in STORE.conflicts if c.ref_a and c.ref_b}
    labeled = [p for p in json.loads(LABELED.read_text())["pairs"] if p["a"] in ids and p["b"] in ids]
    STORE.metrics = _score(detected, labeled)
    return {"conflicts": len(STORE.conflicts), **_counts()}


@app.get("/graph")
async def graph():
    return {"dataset": STORE.dataset, "nodes": _nodes(), "edges": _edges()}


@app.get("/conflicts")
async def conflicts():
    return {"dataset": STORE.dataset, "metrics": STORE.metrics, "conflicts": _conflict_items()}


@app.get("/trust")
async def trust():
    """Source-reliability leaderboard (optional UI panel)."""
    return {"dataset": STORE.dataset, "sources": STORE.ledger.leaderboard()}


@app.post("/resolve")
async def resolve(req: ResolveReq):
    by_id = _claims_by_id()
    conflict = next((c for c in STORE.conflicts if str(c.id) == req.conflict_id), None)

    # 1) trust: only genuine conflicts (not supersession) move a source's score.
    if conflict is not None and conflict.conflict_type in _TRUST_MOVING:
        winner = by_id.get(req.winner_claim_id)
        loser = by_id.get(req.loser_claim_id)
        STORE.ledger.record_resolution(
            winner_source=winner.source if winner else None,
            loser_source=loser.source if loser else None)

    # 2) real Cognee side-effects (improve() reweight + forget()); best-effort.
    await resolve_conflict(req.winner_claim_id, req.loser_claim_id)

    # 3) UI state so /graph + /conflicts reflect the resolution immediately.
    loser = by_id.get(req.loser_claim_id)
    if loser is not None:
        loser.status = "retracted"
    if conflict is not None:
        conflict.resolved = True
        conflict.winner_claim_id = req.winner_claim_id

    return {"status": "resolved",
            "winner_claim_id": req.winner_claim_id,
            "removed_claim_id": req.loser_claim_id,
            "source_trust": STORE.ledger.all_trust()}

_RECALL_Q = {
    "doug_witnesses": ("Doug", "location", "Where is Doug now?"),
    "agent_memory": ("q3_review", "date", "When is the Q3 review?"),
}


@app.get("/recall/{dataset_name}")
async def recall(dataset_name: str):
    subj, pred, query = _RECALL_Q.get(dataset_name, (None, None, "What's the current state?"))
    cands = [c for c in STORE.claims if c.subject == subj and c.predicate == pred]
    cand_ids = {str(c.id) for c in cands}
    superseded = _superseded_ids()
    active = [c for c in cands
              if getattr(c, "status", "active") != "retracted" and str(c.id) not in superseded]
    answer = max(active, key=lambda c: c.valid_from or "", default=None)
    conflicted = any(
        not x.resolved and x.conflict_type in _TRUST_MOVING
        and (x.claim_a_id in cand_ids or x.claim_b_id in cand_ids)
        for x in STORE.conflicts)
    return {
        "query": query,
        "answer": answer.object if answer else None,
        "answer_claim_id": str(answer.id) if answer else None,
        "conflicted": conflicted,
        "candidates": [{"object": c.object, "claim_id": str(c.id), "source": c.source} for c in cands],
    }