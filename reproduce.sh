#!/usr/bin/env bash
# Reproduce every headline claim in Coherence.
# Run with the API server STOPPED (CLI scripts and the server share a Kuzu lock).
#
#   chmod +x reproduce.sh && ./reproduce.sh
#
# PART A runs fully offline (Kuzu + LanceDB + local fastembed embeddings, no LLM).
# PART B needs a free LLM (Gemini / Groq / Ollama) configured in .env.

banner() { echo; echo "=================================================================="; echo "  $1"; echo "=================================================================="; }

banner "PART A  --  offline (no LLM key required)"

banner "1  Unit tests (deterministic core)"
pytest tests/ -q

banner "2  Detection accuracy  (expect precision/recall/F1 = 1.0)"
python eval/evaluate.py --dataset doug_witnesses
python eval/evaluate.py --dataset eval_suite

banner "3  Agent guardrail  (BLOCKED on contradiction -> CLEAR after resolve)"
python scripts/run_guardrail.py

banner "4  Detection as a native cognee.memify() pipeline  (expect 6 conflicts)"
python scripts/run_memify.py doug_witnesses

banner "PART B  --  requires a free LLM in .env  (Gemini / Groq / Ollama)"

banner "5  Semantic tier  (agent_memory recall 67% deterministic -> 100% with LLM)"
python eval/evaluate.py --dataset agent_memory --use-llm \
  || echo "  (needs an LLM configured in .env)"

banner "6  Raw-text extraction across 5 domains  (expect 85-96% recall)"
python scripts/run_extract_suite.py \
  || echo "  (needs an LLM configured in .env)"

banner "Done -- every headline number, re-runnable."