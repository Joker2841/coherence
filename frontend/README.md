# Coherence — frontend (the live memory debugger)

The debugger UI for Coherence. Renders the claim graph, flags contradictions
and temporal supersessions, and lets a human resolve them while the memory
lifecycle (`remember → detect → improve/forget → recall`) fires on screen.

Built with Vite + React. The graph is hand-built SVG driven by a d3-force layout.

## Quickstart

```bash
npm install
npm run dev          # http://localhost:5173
```

That runs in **mock mode** with bundled data — no backend needed. This is the
demo safety net.

## Run against the live backend

1. Start Sai's server (single worker, no `--reload`):
   ```bash
   uvicorn coherence.server:app --port 8000
   ```
2. Point the frontend at it:
   ```bash
   cp .env.example .env      # sets VITE_API_BASE=http://localhost:8000
   npm run dev
   ```
3. The header will read `· live`, and Ingest/Detect/Resolve now hit the real
   endpoints. (Check the Network tab: calls should go to `:8000`.)

CORS is open on the backend, so the `:5173` dev server calls `:8000` directly.

## The flow the UI drives

```
POST /ingest/{dataset}      → load + build claims
POST /detect?use_llm=true   → run detection
GET  /graph                 → nodes + edges (with status)
GET  /conflicts             → conflicts + precision/recall metrics
POST /resolve               → pick a winner; loser retracted, source_trust drops
```

In mock mode these are simulated from `src/data.js` with identical shapes.

## Layout

```
src/
  App.jsx         orchestration, chrome, recall/case-status
  CaseBoard.jsx   the felt-table SVG graph (slips, string, stamps)
  ConflictLog.jsx the discrepancy docket + resolve controls
  api.js          mock/live data seam + contract→internal adapters
  data.js         bundled mock datasets + mockDetect
  lib.js          time format, d3-force layout, string paths, board dims
  styles.css      the case-board styling
```

## Demo notes

- Two cases: **01 — The Missing Groom** (the hook) and **02 — The Agent's
  Memory** (real-world weight).
- Toggle **LLM off on Case 02**: recall drops to 67%, because the
  vegetarian-vs-steak *semantic* conflict is only caught by the gated LLM tier.
  That's the live proof of the two-tier (deterministic + LLM) detector.
