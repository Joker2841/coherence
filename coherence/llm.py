"""
LLM judge for SEMANTIC contradictions only -- the expensive path.

Called solely on vector-prefiltered, same-subject candidate pairs that the
deterministic temporal check could not resolve, so token spend stays tiny and
well inside Groq's free tier.
"""
from __future__ import annotations

import json
import os
from typing import Optional

_PROMPT = """You are a strict consistency checker. Decide whether the two claims
about the same subject directly CONTRADICT each other (cannot both be true at the
same time). Ignore differences that are merely additional detail.

Claim A: {a}
Claim B: {b}

Respond with ONLY compact JSON: {{"contradiction": true or false, "reason": "<short>"}}"""


async def judge_contradiction(text_a: str, text_b: str) -> Optional[dict]:
    """Return {'contradiction': bool, 'reason': str} or None on failure."""
    prompt = _PROMPT.format(a=text_a, b=text_b)

    # Preferred: reuse Cognee's configured LLM client (same provider + key, $0 extra).
    # FIRST-RUN CHECK: confirm this import path / method in your installed version.
    try:
        from cognee.infrastructure.llm.get_llm_client import get_llm_client

        client = get_llm_client()
        raw = await client.acreate_structured_output(
            text_input=prompt,
            system_prompt="Return only JSON.",
            response_model=dict,
        )
        return raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        # Fallback: direct LiteLLM call with the same Groq key. Keeps us unblocked.
        try:
            import litellm

            resp = await litellm.acompletion(
                model=os.getenv("LLM_MODEL", "groq/llama-3.3-70b-versatile"),
                messages=[{"role": "user", "content": prompt}],
                api_key=os.getenv("LLM_API_KEY"),
                temperature=0,
            )
            return json.loads(resp["choices"][0]["message"]["content"])
        except Exception as e:  # noqa: BLE001
            print(f"[coherence] LLM judge failed ({e}); treating pair as non-conflicting.")
            return None
