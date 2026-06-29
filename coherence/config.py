"""
Central configuration for the FREE, local-first stack.

  Graph DB : Kuzu        (embedded, file-based, $0)
  Vector DB: LanceDB     (embedded, file-based, $0)
  Embedding: Fastembed   (all-MiniLM, CPU-only, $0)  -- or Ollama on your GPU
  LLM      : Groq free tier (clean structured output)  -- or local Ollama

CRITICAL: Cognee SILENTLY falls back to OpenAI (which costs money) if you set
ONLY the LLM provider or ONLY the embedding provider. This module sets BOTH
explicitly and refuses to start if that invariant is broken.

Call `setup()` once at the top of every entry point, BEFORE the first real
Cognee operation.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # read .env before anything touches Cognee

# ---- Stack identity (overridable via .env) --------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "fastembed")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

GRAPH_DATABASE_PROVIDER = os.getenv("GRAPH_DATABASE_PROVIDER", "kuzu")
VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "lancedb")

# Shared constants used across the pipeline
DATASET = os.getenv("COHERENCE_DATASET", "main_dataset")
CLAIMS_NODE_SET = "claims"


def _guard_no_openai_fallback() -> None:
    """The single most important check for staying at $0."""
    if not LLM_PROVIDER or not EMBEDDING_PROVIDER:
        raise RuntimeError(
            "Both LLM_PROVIDER and EMBEDDING_PROVIDER must be set. Leaving either "
            "unset makes Cognee silently fall back to OpenAI (paid)."
        )
    if LLM_PROVIDER == "groq" and not LLM_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER=groq but LLM_API_KEY is empty. Put your free Groq key in .env."
        )


def setup() -> None:
    """Configure Cognee for the free stack and validate the no-fallback rule."""
    _guard_no_openai_fallback()

    # DB providers are read from the environment at engine-init time.
    os.environ["GRAPH_DATABASE_PROVIDER"] = GRAPH_DATABASE_PROVIDER
    os.environ["VECTOR_DB_PROVIDER"] = VECTOR_DB_PROVIDER

    # Embeddings: env vars are the reliable path across versions.
    os.environ["EMBEDDING_PROVIDER"] = EMBEDDING_PROVIDER
    os.environ["EMBEDDING_MODEL"] = EMBEDDING_MODEL
    os.environ["EMBEDDING_DIMENSIONS"] = str(EMBEDDING_DIMENSIONS)
    if LLM_ENDPOINT:
        os.environ["LLM_ENDPOINT"] = LLM_ENDPOINT

    # LLM: also set programmatically to be explicit and order-independent.
    import cognee

    cognee.config.set_llm_provider(LLM_PROVIDER)
    cognee.config.set_llm_model(LLM_MODEL)
    if LLM_API_KEY:
        cognee.config.set_llm_api_key(LLM_API_KEY)

    print(
        f"[coherence] stack -> LLM={LLM_PROVIDER}:{LLM_MODEL} | "
        f"embed={EMBEDDING_PROVIDER}:{EMBEDDING_MODEL}({EMBEDDING_DIMENSIONS}d) | "
        f"graph={GRAPH_DATABASE_PROVIDER} | vector={VECTOR_DB_PROVIDER}  (cost: $0)"
    )
