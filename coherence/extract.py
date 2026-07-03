"""
End-to-end extraction: messy document -> structured claims.

An LLM pulls atomic (source, subject, predicate, object, time) claims out of
noisy free text; a canonicalization pass forces predicate CONSISTENCY -- the
thing that makes or breaks downstream detection (roof and pool must BOTH be
'location' or they never get compared). The deterministic engine is unchanged;
this is a measured front layer.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ExtractedClaim(BaseModel):
    source: str = "unknown"
    subject: str
    predicate: str
    object: str
    time: Optional[str] = None
    text: str = ""


class Extraction(BaseModel):
    claims: list[ExtractedClaim]


_SYSTEM = ("You extract atomic factual claims from messy, noisy text. "
           "Precision over recall: skip anything that isn't a concrete, checkable assertion.")

_PROMPT = """From the document below, extract every atomic factual claim as
(source, subject, predicate, object, time).

RULES:
- One claim = one subject + one attribute + one value. Split compound sentences.
- source = who asserts it (a named person, or a log). Use "unknown" if unstated.
- predicate = the KIND of attribute, NORMALIZED. CRITICAL: use the SAME predicate
  for the same kind of fact. Every physical-location fact -> "location". A person's
  job/title -> "role". A scheduled happening/party -> "event". Do NOT invent
  synonyms like "whereabouts", "position", or "spotted" -- collapse them all to
  one canonical predicate.
- time = ISO 8601 (YYYY-MM-DDTHH:MM:SS) if a time is stated or implied by context,
  else null. Use the document's date context to resolve "9 PM" to a full timestamp.
- IGNORE noise: side chatter, hedges, irrelevant detail.

Return JSON: {{"claims": [{{"source","subject","predicate","object","time","text"}}]}}

DOCUMENT:
{document}"""

# Collapse the model's predicate drift onto canonical forms.
_PREDICATE_CANON = {
    "location": {"location", "whereabouts", "position", "place", "located",
                 "seen at", "spotted", "sighting", "was at"},
    "role": {"role", "title", "job"},
    "event": {"event", "activity", "happening", "party"},
    "manager": {"manager", "boss", "supervisor", "reports to", "reporting"},
    "diet": {"diet", "dietary", "food preference", "eats"},
    "date": {"date", "scheduled", "day", "when", "meeting date"},
}


def canon_predicate(pred: str) -> str:
    p = (pred or "").strip().lower()
    for canon, syns in _PREDICATE_CANON.items():
        if p == canon or p in syns:
            return canon
    return p


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