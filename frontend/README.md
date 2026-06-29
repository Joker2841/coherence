# Frontend — the live memory debugger

This is the primary interface for Coherence. **Not built yet** — it's the next
step after the backend is verified end to end.

## What it renders
1. **Graph view** — Claim nodes + Contradiction nodes, with `contradicts` /
   `supersedes` edges. Conflicting nodes glow; resolved ones settle.
2. **Conflict panel** — list of detected Contradictions with the verdict,
   confidence, and conflict type (temporal vs semantic).
3. **Resolve action** — pick the true claim → `POST /resolve` → watch
   `improve()` reweight and `forget()` prune the loser live.
4. **Audit / "why does it believe this?"** — uses each Contradiction's
   provenance stamp (source_pipeline / source_task).
5. **Metrics badge** — precision / recall from the eval harness.

## Backend it talks to
`coherence/server.py` (FastAPI): `/ingest/{dataset}`, `/detect`, `/conflicts`,
`/graph`, `/resolve`.

## Build options (decide when we start)
- **Extend Cognee's built-in `memory_map` graph view** (fastest; aligns with the
  open-source PR track since that view is under active development), or
- **Custom Cytoscape.js / D3 force graph** for full control over the
  conflict-glow animation.

> When we build this, read the frontend-design guidance first so it doesn't read
> as a templated default — the demo's "wow" moment lives here.
