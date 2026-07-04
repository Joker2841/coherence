"""
End-to-end extraction: messy document -> structured claims, each attributed to
the PRIMARY ENTITY it concerns (not the reporter, not the metric name). This
alignment fixes both the eval and downstream detection (consistent subjects let
conflicting claims group). Deterministic engine unchanged; measured front layer.
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


_SYSTEM = ("You extract atomic factual claims from messy text and attribute each to "
           "the PRIMARY ENTITY it concerns (a person, company, patient, flight, "
           "project) -- not the reporter and not the metric. Skip content not about "
           "that entity.")

_PROMPT = """From the document below, extract every atomic factual claim as
(source, subject, predicate, object, time).

STEP 1 - Identify the PRIMARY ENTITY the document tracks (usually named in the
header/title: a person, company, patient, flight, project).

RULES:
- SUBJECT = the primary entity the fact is ABOUT -- never the reporter, never the
  metric name. Attribute facts to that entity unless a fact is clearly about a
  different entity. Study these carefully:
    "the auditor put Q3 revenue at $5M"  -> subject=<Company>, predicate=revenue, object=$5M, source=auditor
    "Bob has served as CEO since 2024"   -> subject=<Company>, predicate=ceo, object=Bob   (NOT subject=Bob)
    "Headcount reached 650"              -> subject=<Company>, predicate=employee_count, object=650  (NOT subject=Headcount)
    "Board A shows the flight delayed"   -> subject=<Flight>, predicate=status, object=delayed, source=Board A  (NOT subject=Board A)
    "David is the project manager"       -> subject=<Project>, predicate=manager, object=David  (NOT subject=David)
- source = who reported it (person, board, chart, log). Reporters go HERE, never in
  subject. Use "unknown" if unstated.
- predicate = the KIND of attribute, normalized and CONSISTENT (all physical-location
  facts -> "location"; do not invent synonyms).
- PRESENCE via negation/duration is a location: "X never left Y" -> X.location = Y.
- object = the value of the attribute.
- time = ISO 8601 (YYYY-MM-DDTHH:MM:SS) if stated or implied by the document's date
  context, else null.
- IGNORE anything not about the primary entity: side chatter, lost tigers, cafeteria
  menus, broken espresso machines, catering threads.

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