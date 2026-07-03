"""
Phase 5: human-in-the-loop resolution.

The VISIBLE forget/retract is handled at the integrity layer: the server marks
the losing claim `retracted`, and /recall + /graph exclude it. That is the
correct *surgical* behavior -- one claim removed, everything else intact.

We deliberately do NOT call cognee.forget(dataset=...): it deletes the ENTIRE
dataset (not one claim), which wipes the graph, breaks the vector gate on any
later use_llm detection, and spams EntityNotFoundError. improve() stays as a
genuine reweighting pass over the intact graph.
"""
from __future__ import annotations

import cognee


async def resolve_conflict(winner_claim_id: str, loser_claim_id: str, dataset: str | None = None) -> None:
    # improve(): real reweighting pass over the (now intact) graph. Guarded so a
    # transient failure can never break the /resolve response.
    try:
        await cognee.improve()
    except Exception as e:  # noqa: BLE001
        print(f"[coherence] improve() skipped: {e}")

    # NOTE: no cognee.forget(dataset=...) here -- it is dataset-wide and destructive.
    # The retracted claim is excluded at the integrity layer (server.py sets
    # status='retracted'; /recall and /graph honor it) = correct surgical forget.
    #
    # If you later want a LITERAL per-item Cognee delete, it's the delete-data
    # API (dataset_id + data_id) -- but confirm add_data_points claims expose a
    # data_id first; leave it out of the live demo path until verified.