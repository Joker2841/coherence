"""
vector-gated semantic detection.

Deterministic rules handle same-(subject,predicate) conflicts. This gate handles
the residue — same-SUBJECT, DIFFERENT-predicate pairs (diet='vegetarian' vs
meal_order='steak') that structure can't compare. We ask Cognee's LanceDB store
how close the two claim texts are and send only the close ones to the LLM.

graph resolves the easy cases -> LanceDB gates the hard ones -> LLM judges the residue.
"""
from __future__ import annotations
from typing import Optional

SIM_THRESHOLD = 0.35     # tune with eval/evaluate.py --use-llm
_TOPK = 25


class VectorGate:
    """Wraps Cognee's vector engine; self-calibrates score direction on first use."""

    def __init__(self):
        self._engine = None
        self._collection: Optional[str] = None
        self._is_distance: Optional[bool] = None

    async def _ready(self) -> bool:
        if self._engine is None:
            from cognee.infrastructure.databases.vector import get_vector_engine
            self._engine = get_vector_engine()
        if self._collection is None:
            for name in ("Claim_text", "Claim", "claim_text"):
                try:
                    if await self._engine.has_collection(name):
                        self._collection = name
                        break
                except Exception:
                    continue
            print(f"[gate] engine={type(self._engine).__name__} collection={self._collection!r}")
        return self._collection is not None

    async def _scores(self, claim_id: str, text: str) -> dict[str, float]:
        res = await self._engine.search(self._collection, query_text=text, limit=_TOPK)
        scores = {str(getattr(r, "id", "")): float(getattr(r, "score", 0.0)) for r in res}
        if self._is_distance is None and claim_id in scores:
            self._is_distance = scores[claim_id] < 0.5   # self ~0 => distance metric
            print(f"[gate] self-match={scores[claim_id]:.3f} -> "
                  f"{'distance' if self._is_distance else 'similarity'} metric")
        return scores

    def _sim(self, raw: float) -> float:
        is_dist = self._is_distance if self._is_distance is not None else True
        return max(0.0, 1.0 - raw) if is_dist else raw

    async def close_partners(self, claim: dict, others: list[dict]) -> list[tuple[dict, float]]:
        """Of `others`, those whose text is vector-close to `claim`."""
        if not await self._ready():
            return []
        try:
            scores = await self._scores(claim["id"], claim["text"])
        except Exception as e:
            print(f"[gate] search failed: {type(e).__name__}: {e}")
            return []
        hits = []
        for o in others:
            raw = scores.get(o["id"])
            sim = self._sim(raw) if raw is not None else 0.0
            print(f"[gate]   {claim['object']!r} vs {o['object']!r}: sim={sim:.2f}")
            if raw is not None and sim >= SIM_THRESHOLD:
                hits.append((o, sim))
        return hits