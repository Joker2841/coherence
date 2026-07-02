"""
SPIKE v2 (throwaway): does feedback -> improve() -> recall-SHIFT actually work
when claims are ingested the NORMAL way (add + cognify) that search requires?
This is the 'bridge' feasibility gate. KEY output is step 4: does recall move?
"""
import asyncio
import json
from pathlib import Path

from coherence import config
config.setup()

import cognee
from cognee import SearchType

DATA = Path(__file__).resolve().parent.parent / "data"
Q = "Where was Doug at 9 PM?"
SID = "trust_probe"


async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    # 0) NORMAL flow -> registers default user, creates DB, builds the searchable
    #    graph that search()/feedback operate on. (This is what add_data_points skips.)
    print("\n--- 0. INGEST (add + cognify) ---")
    statements = json.loads((DATA / "doug_witnesses.json").read_text())
    for s in statements:
        await cognee.add(s["text"])
    # plain cognify (no temporal, no custom model) -> fast on short claims.
    # If Groq rate-limits on the burst, add data_per_batch=1 here.
    await cognee.cognify()
    print("cognify done")

    # 1) baseline recall WITH a session so the Q&A is stored
    print("\n--- 1. BASELINE RECALL ---")
    try:
        before = await cognee.search(query_text=Q, query_type=SearchType.GRAPH_COMPLETION, session_id=SID)
    except TypeError:
        before = await cognee.search(query_text=Q, query_type=SearchType.GRAPH_COMPLETION, save_interaction=True)
    print("BEFORE:", before)

    # 2) feedback surface: documented session API first, then older FEEDBACK form
    print("\n--- 2. FEEDBACK ---")
    fed = False
    if hasattr(cognee, "session"):
        print("session methods:", [m for m in dir(cognee.session) if not m.startswith("_")])
        try:
            entries = await cognee.session.get_session(session_id=SID, last_n=5)
            print("entries:", len(entries) if entries else 0)
            if entries:
                latest = entries[-1]
                qa_id = getattr(latest, "qa_id", None) or (latest.get("qa_id") if isinstance(latest, dict) else None)
                print("qa_id:", qa_id)
                ok = await cognee.session.add_feedback(
                    session_id=SID, qa_id=qa_id,
                    feedback_text="Incorrect. Per Stu, Doug was at the pool bar, not the roof.",
                    feedback_score=1)
                print("add_feedback ok:", ok)
                fed = True
        except Exception as e:
            print("session path failed:", type(e).__name__, e)
    if not fed:
        try:
            fb = await cognee.search(
                query_text="Incorrect. Per Stu, Doug was at the pool bar, not the roof.",
                query_type=SearchType.FEEDBACK, last_k=1)
            print("SearchType.FEEDBACK ok:", fb)
            fed = True
        except Exception as e:
            print("SearchType.FEEDBACK failed:", type(e).__name__, e)
    if not fed:
        print("\n!! No feedback path worked -> the pure improve() route is out; use the escape hatch.")
        return

    # 3) apply feedback via improve()
    print("\n--- 3. IMPROVE() ---")
    try:
        await cognee.improve()
        print("improve() done")
    except Exception as e:
        print("improve() failed:", type(e).__name__, e)

    # 4) recall again -- THE decisive test
    print("\n--- 4. RECALL AFTER FEEDBACK ---")
    try:
        after = await cognee.search(query_text=Q, query_type=SearchType.GRAPH_COMPLETION, session_id=SID)
    except TypeError:
        after = await cognee.search(query_text=Q, query_type=SearchType.GRAPH_COMPLETION)
    print("AFTER:", after)
    print("\n=== BEFORE vs AFTER: did the answer move toward 'pool bar'? ===")


if __name__ == "__main__":
    asyncio.run(main())