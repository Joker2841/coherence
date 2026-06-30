# """
# Phase 3 orchestration: run the custom contradiction pipeline via memify().
# """
# from __future__ import annotations

# import cognee
# from cognee.modules.pipelines.tasks.task import Task

# from .config import CLAIMS_NODE_SET, DATASET
# from .tasks import detect_contradictions, find_candidate_pairs


# async def run_detection(dataset: str = DATASET) -> None:
#     """
#     Verified signature:
#       memify(extraction_tasks, enrichment_tasks, data, dataset, user,
#              node_type=NodeSet, node_name, vector_db_config, graph_db_config,
#              run_in_background)

#     We scope to the 'claims' NodeSet via `node_name` so the LLM never sees
#     unrelated chunks.
#     """
#     await cognee.memify(
#         extraction_tasks=[Task(find_candidate_pairs)],
#         enrichment_tasks=[Task(detect_contradictions)],
#         dataset=dataset,
#         node_name=[CLAIMS_NODE_SET],
#     )

"""Detection: same-time-different-value = contradiction; latest value supersedes
earlier."""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
from cognee.tasks.storage import add_data_points
from .models import Claim, Contradiction
from .temporal import parse


def _d(c: Claim) -> dict:
    return {"id": str(getattr(c, "id", "")), "text": c.text, "subject": c.subject,
            "predicate": c.predicate, "object": c.object, "valid_from": c.valid_from}


async def detect(claims: list[Claim], use_llm: bool = False) -> list[Contradiction]:
    items = [_d(c) for c in claims]
    found: list[Contradiction] = []
    groups = defaultdict(list)
    for c in items:
        groups[(c["subject"], c["predicate"])].append(c)

    for (subj, pred), group in groups.items():
        # Rule A: same timestamp, different value -> irreducible contradiction.
        by_time = defaultdict(list)
        for c in group:
            by_time[c["valid_from"]].append(c)
        for t, same_time in by_time.items():
            for a, b in combinations(same_time, 2):
                if a["object"] != b["object"]:
                    found.append(Contradiction(
                        claim_a_id=a["id"], claim_b_id=b["id"],
                        conflict_type="contradiction", confidence=1.0,
                        verdict=f"{subj}.{pred} is both '{a['object']}' and '{b['object']}' at {t}."))
                    print(f"[CONTRADICTION] {subj}.{pred}: '{a['object']}' vs '{b['object']}' @ {t}")

        # Rule B: latest value supersedes earlier different values.
        dated = sorted([c for c in group if c["valid_from"]], key=lambda c: c["valid_from"])
        if len(dated) >= 2:
            latest = dated[-1]
            for older in dated[:-1]:
                if older["object"] != latest["object"] and older["valid_from"] != latest["valid_from"]:
                    found.append(Contradiction(
                        claim_a_id=older["id"], claim_b_id=latest["id"],
                        conflict_type="supersession", confidence=1.0, winner_claim_id=latest["id"],
                        verdict=f"{subj}.{pred}: '{older['object']}' ({older['valid_from']}) "
                                f"superseded by '{latest['object']}' ({latest['valid_from']})."))
                    print(f"[SUPERSESSION] {subj}.{pred}: '{older['object']}' -> '{latest['object']}'")

    # Semantic LLM pass (for cross-predicate cases like vegetarian vs steak) stays
    # OFF until we add a similarity gate — that's where qwen was hallucinating.
    if use_llm:
        pass

    if found:
        await add_data_points(found)
    n_c = sum(1 for f in found if f.conflict_type == "contradiction")
    print(f"\n[coherence] {len(found)} conflicts ({n_c} contradictions, {len(found)-n_c} supersessions)")
    return found