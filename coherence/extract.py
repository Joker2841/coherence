"""
End-to-end extraction: messy document -> structured claims.

An LLM pulls atomic (source, subject, predicate, object, time) claims out of
noisy free text; a canonicalization pass forces predicate CONSISTENCY. The
deterministic engine is unchanged; this is a measured front layer.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .rules import canon_predicate


class ExtractedClaim(BaseModel):
    source: str = "unknown"
    subject: str
    predicate: str
    object: str
    time: Optional[str] = None
    text: str = ""


class Extraction(BaseModel):
    claims: list[ExtractedClaim]


_SYSTEM = ("You extract atomic factual claims from messy, noisy text. Extract the "
           "underlying assertion even when it is phrased indirectly or emphatically; "
           "skip only true noise (chatter, opinions, irrelevant detail).")

_PROMPT = """From the document below, extract every atomic factual claim as
(source, subject, predicate, object, time).

RULES:
- One claim = one subject + one attribute + one value. Split compound sentences.
- source = who asserts it (a named person, or a log). Use "unknown" if unstated.
- predicate = the KIND of attribute, NORMALIZED. Use the SAME predicate for the
  same kind of fact. Every physical-location fact -> "location". A person's
  job/title -> "role". A scheduled happening/party -> "event". Do NOT invent
  synonyms like "whereabouts", "position", "spotted", "was at" -- collapse them
  all to one canonical predicate.
- PRESENCE COUNTS AS LOCATION, even when phrased indirectly. Convert negation or
  duration into the positive location claim:
    "X never left Y"  ->  X.location = Y
    "X stayed at Y all night" / "X remained in Y"  ->  X.location = Y
- time = ISO 8601 (YYYY-MM-DDTHH:MM:SS) if a time is stated or implied; use the
  document's date context to resolve "9 PM" to a full timestamp; else null.
- Strong wording ("insisted", "swears", "repeatedly") does NOT make a statement
  noise -- extract the underlying factual claim. IGNORE only real noise: side
  chatter, hedges, opinions, irrelevant detail.

EXAMPLES (illustrative):
- "Maria insists she never left the office that evening."
   -> {{"source":"Maria","subject":"Maria","predicate":"location","object":"the office","time":null,"text":"never left the office that evening"}}
- "Dispatch shows the van was spotted at the depot at 3 PM on May 2, 2024."
   -> {{"source":"Dispatch","subject":"the van","predicate":"location","object":"the depot","time":"2024-05-02T15:00:00","text":"van spotted at the depot at 3 PM"}}
- "He rambled about the weather for a while."  ->  ignore (noise, not a checkable fact)

Return JSON: {{"claims": [{{"source","subject","predicate","object","time","text"}}]}}

DOCUMENT:
{document}"""


async def extract_claims(document: str) -> list[dict]:
    from cognee.infrastructure.llm.LLMGateway import LLMGateway

    result = await LLMGateway.acreate_structured_output(
        text_input=_PROMPT.format(document=document),
        system_prompt=_SYSTEM,
        response_model=Extraction,
    )
    claims = result.claims if hasattr(result, "claims") else result["claims"]
    out = []
    for i, c in enumerate(claims):
        d = c.model_dump() if hasattr(c, "model_dump") else dict(c)
        d["predicate"] = canon_predicate(d.get("predicate", ""))
        d["id"] = f"x{i}"
        out.append(d)
    return out