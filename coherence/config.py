"""
Central configuration for the FREE, local-first stack.

  Graph DB : Kuzu        (embedded, file-based, $0)
  Vector DB: LanceDB     (embedded, file-based, $0)
  Embedding: Fastembed   (all-MiniLM, CPU-only, $0)  -- or Ollama on your GPU
  LLM      : Groq free tier, Gemini-compatible OpenRouter, or local Ollama
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


def _normalize_llm_settings(provider: str, model: str, endpoint: str) -> tuple[str, str, str]:
    """Normalize provider/model/endpoint values for the installed Cognee stack."""
    provider = (provider or "").strip().lower()
    model = (model or "").strip()
    endpoint = (endpoint or "").strip()

    if provider == "openrouter":
        if not model:
            model = "google/gemini-2.5-flash-lite"
        if not endpoint:
            endpoint = "https://openrouter.ai/api/v1"
        return "openai", f"openrouter/{model}", endpoint

    return provider, model, endpoint


def get_llm_args() -> dict[str, object]:
    """Return provider-specific kwargs to improve compatibility with the installed stack."""
    provider = (LLM_PROVIDER or "").strip().lower()
    model = (LLM_MODEL or "").strip()
    if provider == "openrouter" or (provider == "openai" and model.startswith("openrouter/")):
        return {"instructor_mode": "OPENROUTER_STRUCTURED_OUTPUTS"}
    return {}


def _guard_no_openai_fallback() -> None:
    """The single most important check for staying at $0."""
    if not LLM_PROVIDER or not EMBEDDING_PROVIDER:
        raise RuntimeError(
            "Both LLM_PROVIDER and EMBEDDING_PROVIDER must be set. Leaving either "
            "unset makes Cognee silently fall back to OpenAI (paid)."
        )
        
    if "groq/" in LLM_MODEL and not LLM_API_KEY:
        raise RuntimeError("Using a Groq model but LLM_API_KEY is empty. Put your free Groq key in .env.")

    if LLM_PROVIDER == "openai" and LLM_MODEL.startswith("openrouter/") and not LLM_API_KEY:
        raise RuntimeError("Using OpenRouter but LLM_API_KEY is empty. Put your OpenRouter key in .env.")


def setup() -> None:
    """Configure Cognee for the free stack and validate the no-fallback rule."""
    global LLM_PROVIDER, LLM_MODEL, LLM_ENDPOINT

    LLM_PROVIDER, LLM_MODEL, LLM_ENDPOINT = _normalize_llm_settings(
        LLM_PROVIDER, LLM_MODEL, LLM_ENDPOINT
    )

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
    if LLM_ENDPOINT:
        cognee.config.set_llm_endpoint(LLM_ENDPOINT)
    if LLM_API_KEY:
        cognee.config.set_llm_api_key(LLM_API_KEY)

    llm_args = get_llm_args()
    if llm_args:
        cognee.config.set_llm_config({"llm_args": llm_args})

    print(
        f"[coherence] stack -> LLM={LLM_PROVIDER}:{LLM_MODEL} | "
        f"embed={EMBEDDING_PROVIDER}:{EMBEDDING_MODEL}({EMBEDDING_DIMENSIONS}d) | "
        f"graph={GRAPH_DATABASE_PROVIDER} | vector={VECTOR_DB_PROVIDER}  (cost: $0)"
    )
