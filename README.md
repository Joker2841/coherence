# Coherence

**The integrity layer for AI memory.**

Cognee gives an agent perfect recall. Coherence makes sure it never believes two
things at once. We ingest statements into a Cognee knowledge graph, then run a
**custom memify pipeline** that flags contradictions — temporal supersession
("the meeting moved to Friday") and semantic conflicts ("on the roof" vs "at the
pool") — and lets a human resolve them, with the whole memory lifecycle
(`remember` / `recall` / `improve` / `forget`) firing live in a debugger UI.

Built for the WeMakeDevs × Cognee hackathon (open-source track). **Stack cost: $0.**

---

## Why this is graph-native, not RAG

Pure vector search can't catch a contradiction when the wording changes. A graph
can: claims that share a subject+predicate but disagree on the object — and carry
different timestamps — are a *structural* relationship, not a similarity score.
That's the whole pitch, and it's the reason this leans on Cognee's hybrid
graph-vector layer instead of a plain vector store.

## Architecture flow

```
1. INGEST     cognee.add(node_set="claims") + temporal_cognify=True
2. BUILD      cognee.cognify(graph_model=Claim)      -> Claim nodes + temporal edges
3. DETECT     cognee.memify(extraction + enrichment) -> Contradiction nodes
                 - temporal supersession : deterministic, NO LLM
                 - semantic contradiction: LLM, only on prefiltered candidates
4. QUERY      cognee.search(...)                     -> answer flags conflicts
5. RESOLVE    improve() reweights  ->  forget() prunes the loser
6. DEBUGGER   FastAPI + graph view + conflict panel + resolve (frontend, next)
```

Each stage maps to a real Cognee call. The cost-heavy LLM step is gated behind a
deterministic temporal check and a same-subject prefilter, so token spend stays
inside Groq's free tier and your GPU only does embeddings.

## Repo map

```
coherence/
  coherence/
    config.py     free-stack setup + the OpenAI-fallback guard
    models.py     Claim + Contradiction (DataPoint subclasses)
    ingest.py     add + temporal cognify
    temporal.py   deterministic supersession (no LLM)
    llm.py        LLM judge for semantic conflicts only
    tasks.py      the custom memify extraction + enrichment tasks  <- the heart
    detect.py     memify orchestration
    resolve.py    improve() feedback + forget()
    server.py     FastAPI backend for the debugger
  data/           doug_witnesses.json (Act 1), agent_memory.json (Act 2)
  eval/           labeled_set.json + evaluate.py (precision / recall)
  scripts/        run_demo.py, reset.py
  frontend/       the live debugger (to build next)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then paste your free Groq key
```

## Run the demo

```bash
# Act 1 — conflicting witnesses
python scripts/run_demo.py --dataset doug_witnesses --query "Where is Doug?"

# Act 2 — AI agent memory integrity
python scripts/run_demo.py --dataset agent_memory --query "When is the Q3 review?"

# Start the debugger backend
uvicorn coherence.server:app --reload --port 8000
```

## First-run checks (verify against your installed Cognee version)

These are the few spots intentionally left to confirm on first run — each is
marked `FIRST-RUN CHECK` in the code:

1. **`graph_model=Claim` in `cognify`** (`ingest.py`) — confirm a DataPoint
   subclass is accepted directly; fallback is plain `cognify` + extract claims in
   the memify extraction task.
2. **Graph node shape inside the memify task** (`tasks.py`, `_node_to_claim`) —
   match attribute access to your `CogneeGraph` nodes.
3. **LLM client import path** (`llm.py`) — `get_llm_client`; there's a LiteLLM
   fallback if the path differs.
4. **Feedback + surgical delete APIs** (`resolve.py`) — wire the winner's
   feedback signal and narrow `forget()` to a single node (or mark `retracted`).
5. **Graph read for the UI** (`server.py` `/graph`, `/conflicts`) — pull live
   state from the Kuzu adapter or the `visualize_graph()` export.

## Parallel: open-source PR track ($100/PR)

Low-hanging targets spotted while building this:
- The `HUGGINGFACE_TOKENIZER`-required-with-Ollama-embeddings bug.
- The `memory_map` graph view (overlaps with our debugger components).
