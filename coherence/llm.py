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

_SYSTEM = ("You judge whether two claims about the same subject LOGICALLY CONTRADICT — "
           "whether they CANNOT both be true. Be strict: most claim pairs are compatible.")

_PROMPT = """Two claims about the same subject. Can they BOTH be true at once?

A contradiction means one claim makes the other IMPOSSIBLE. Apply these rules:
- Different times -> the subject changed over time. That is an UPDATE, not a contradiction.
- Different aspects (a role vs an event vs a location) usually coexist. NOT a contradiction.
- Call it a contradiction only when both cannot hold, e.g. a stated property broken by an action.

Examples:
- "is the groom" [role] + "had a bachelor party" [event] -> NOT a contradiction.
- "on the roof at 9 PM" [location] + "in the suite at 11 PM" [location] -> NOT a contradiction (different times).
- "is vegetarian" [diet] + "ordered a steak" [meal] -> CONTRADICTION.

Claim A: {a_text}   [aspect={a_pred}, time={a_time}]
Claim B: {b_text}   [aspect={b_pred}, time={b_time}]

Respond ONLY with: {{"contradiction": true or false, "reason": ""}}"""

async def judge_contradiction(a: dict, b: dict):
    from cognee.infrastructure.llm.LLMGateway import LLMGateway
    prompt = _PROMPT.format(
        a_text=a["text"], a_pred=a["predicate"], a_time=a.get("valid_from") or "unknown",
        b_text=b["text"], b_pred=b["predicate"], b_time=b.get("valid_from") or "unknown"
    )
    try:
        r = await LLMGateway.acreate_structured_output(
            text_input=prompt, system_prompt=_SYSTEM, response_model=ContradictionVerdict)
        return r if isinstance(r, dict) else {"contradiction": bool(r.contradiction), "reason": r.reason}
    except Exception as e:
        print(f"[coherence] judge error: {type(e).__name__}: {e}")
        return None