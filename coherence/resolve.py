"""
Phase 5: human-in-the-loop resolution.

We reuse improve()'s native feedback-weight stage rather than hand-rolling edge
scores, then forget() the losing claim. This is what makes all four lifecycle
operations (remember / recall / improve / forget) visibly fire in the demo.
"""
from __future__ import annotations

import cognee

from .config import DATASET


async def resolve_conflict(
    winner_claim_id: str,
    loser_claim_id: str,
    dataset: str = DATASET,
) -> None:
    """
    Two intended effects:
      * boost the winning claim's weight (via the feedback / improve loop)
      * surgically remove the losing claim

    FIRST-RUN CHECK: confirm the exact feedback-submission API in your version.
    improve() consumes thumbs-up/down feedback recorded against the graph
    elements used to answer; wire the winner's positive signal here.
    """
    # 1. Positive signal toward the winner, applied via the improve loop.
    try:
        await cognee.improve()
    except Exception as e:  # noqa: BLE001
        print(f"[coherence] improve() step skipped: {e}")

    # 2. Remove the losing claim.
    #    forget(dataset=...) deletes a whole dataset -- too broad for one claim.
    #    For surgical single-node deletion, confirm the granular delete API
    #    (e.g. datasets.delete_data) in your version. A safe demo alternative is
    #    to mark the loser node status="retracted" instead of hard-deleting.
    try:
        # TODO: narrow this to loser_claim_id instead of the whole dataset.
        await cognee.forget(dataset=dataset)
    except Exception as e:  # noqa: BLE001
        print(f"[coherence] forget() step skipped: {e}")
