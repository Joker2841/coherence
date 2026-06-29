"""
Phase 6 backend: a thin FastAPI layer the debugger frontend talks to.

Run:
    uvicorn coherence.server:app --reload --port 8000

Endpoints:
    POST /ingest/{dataset_name}  -> load + cognify a demo dataset
    POST /detect                 -> run the contradiction memify pipeline
    GET  /conflicts              -> list detected Contradictions
    GET  /graph                  -> nodes + edges for the graph view
    POST /resolve                -> resolve a conflict (improve + forget)
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config

config.setup()  # configure the free stack BEFORE any cognee operation

from .detect import run_detection  # noqa: E402
from .ingest import ingest_statements  # noqa: E402
from .resolve import resolve_conflict  # noqa: E402

app = FastAPI(title="Coherence -- AI memory integrity layer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class ResolveReq(BaseModel):
    winner_claim_id: str
    loser_claim_id: str


@app.post("/ingest/{dataset_name}")
async def ingest(dataset_name: str):
    statements = json.loads((DATA_DIR / f"{dataset_name}.json").read_text())
    await ingest_statements(statements)
    return {"ingested": len(statements), "dataset": dataset_name}


@app.post("/detect")
async def detect():
    await run_detection()
    return {"status": "detection_complete"}


@app.get("/conflicts")
async def conflicts():
    """List detected Contradictions.

    FIRST-RUN CHECK: query Contradiction nodes from the graph adapter, or capture
    them during detection. Stubbed shape below.
    """
    return {"conflicts": [], "note": "wire to graph adapter / detection capture"}


@app.get("/graph")
async def graph():
    """Return nodes + edges for the debugger graph view.

    FIRST-RUN CHECK: read live state from the Kuzu adapter, or reuse the data
    export behind cognee.visualize_graph(). Stubbed shape below.
    """
    return {"nodes": [], "edges": [], "note": "wire to Kuzu / visualize_graph export"}


@app.post("/resolve")
async def resolve(req: ResolveReq):
    await resolve_conflict(req.winner_claim_id, req.loser_claim_id)
    return {"status": "resolved", "winner": req.winner_claim_id}
