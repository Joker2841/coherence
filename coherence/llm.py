"""
LLM judge for SEMANTIC contradictions only.

Uses Cognee's own LLMGateway, so we inherit the exact provider/model/key already
configured and working for extraction (Ollama qwen2.5 here). No provider-prefix
or rate-limit surprises, and structured output is handled by instructor.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ContradictionVerdict(BaseModel):
    contradiction: bool
    reason: str


_SYSTEM = "You are a strict consistency checker. Return only the structured verdict."

_PROMPT = """Do these two claims about the same subject DIRECTLY CONTRADICT each other
(they cannot both be true at the same time)? Ignore differences that are merely
additional detail.

Claim A: {a}
Claim B: {b}"""


async def judge_contradiction(text_a: str, text_b: str) -> Optional[dict]:
    """Return {'contradiction': bool, 'reason': str}, or None on failure."""
    from cognee.infrastructure.llm.LLMGateway import LLMGateway

    try:
        result = await LLMGateway.acreate_structured_output(
            text_input=_PROMPT.format(a=text_a, b=text_b),
            system_prompt=_SYSTEM,
            response_model=ContradictionVerdict,
        )
        if isinstance(result, dict):
            return result
        return {
            "contradiction": bool(getattr(result, "contradiction", False)),
            "reason": getattr(result, "reason", ""),
        }
    except Exception as e:  # surface the real error this time, don't mask it
        print(f"[coherence] LLM judge error: {type(e).__name__}: {e}")
        return None