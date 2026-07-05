#!/usr/bin/env bash
# Reproduce every headline claim in Coherence.
#
#   chmod +x reproduce.sh && ./reproduce.sh
#
# Run with the API server STOPPED -- the CLI scripts and the server share the
# embedded Kuzu / LanceDB lock.
#
# PART A runs fully offline: Kuzu graph + LanceDB vectors + local Fastembed
# embeddings. No LLM key required.
# PART B needs one free LLM configured in .env (Ollama / Groq / Gemini).

banner() { echo; echo "=================================================================="; echo "  $1"; echo "=================================================================="; }

banner "PART A  --  offline (no LLM key required)"

banner "1  Unit tests  (expect 16 passed)"
pytest tests/ -q

banner "2  Detection accuracy  (expect precision / recall / F1 = 1.0)"
python eval/evaluate.py --dataset eval_suite

banner "3  Agent guardrail  (expect 16/16 correct safety decisions)"
python scripts/run_guardrail_eval.py

banner "4  Detection as a native cognee.memify() pipeline  (expect 6 conflicts)"
python scripts/run_memify.py doug_witnesses

banner "PART B  --  requires a free LLM in .env  (Ollama / Groq / Gemini)"

banner "5  LLM-cost report  (deterministic core avoids the LLM; only the gated residue reaches it)"
# run_cost is embeddings-only per its docstring, so it also runs in PART A;
python scripts/run_cost.py agent_memory \
  || echo "  (needs the embedding + LLM providers configured in .env)"

banner "6  Semantic tier  (agent_memory recall 67% deterministic -> 100% with LLM)"
python eval/evaluate.py --dataset agent_memory --use-llm \
  || echo "  (needs an LLM configured in .env)"

banner "7  Raw-text extraction across 5 domains  (expect 85-96% recall)"
python scripts/run_extract_suite.py \
  || echo "  (needs an LLM configured in .env)"

banner "Done -- every headline number, re-runnable."