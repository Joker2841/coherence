# """
# Phase 1-2: ingest raw statements and build the temporal knowledge graph.
# """
# from __future__ import annotations

# import cognee

# from .config import CLAIMS_NODE_SET, DATASET
# from .models import Claim


# async def ingest_statements(statements: list[dict], dataset: str = DATASET) -> None:
#     """
#     statements: [{"id": "w2", "text": "...", "source": "Phil",
#                   "time": "2025-06-27T21:00:00"}, ...]

#     We fold source + time into the ingested text so temporal_cognify can extract
#     a timestamp and the provenance survives extraction.
#     """
#     for s in statements:
#         content = f"({s.get('source', 'unknown')}, {s.get('time', '')}) {s['text']}"
#         await cognee.add(content, node_set=[CLAIMS_NODE_SET], dataset_name=dataset)

#     # graph_model=Claim shapes extraction into Claim nodes.
#     # temporal_cognify=True tags edges with event dates -> supersession detection.
#     #
#     # FIRST-RUN CHECK: confirm cognify accepts a DataPoint subclass directly as
#     # graph_model in your installed version. If extraction looks noisy, fall back
#     # to a plain `await cognee.cognify(datasets=[dataset], temporal_cognify=True)`
#     # and extract Claims inside the memify extraction task (see tasks.py).
#     await cognee.cognify(
#         datasets=[dataset],
#         graph_model=Claim,
#         temporal_cognify=True,
#     )

"""Build clean Claim nodes directly. No cognify text-extraction,
so this runs in seconds and gives queryable subject/predicate/object/time."""
from __future__ import annotations
from cognee.tasks.storage import add_data_points
from .config import DATASET
from .models import Claim


def _to_claim(s: dict) -> Claim:
    return Claim(text=s["text"], subject=s["subject"], predicate=s["predicate"],
                 object=s["object"], valid_from=s.get("time"),
                 source=s.get("source"), ref_id=s.get("id"))


async def ingest_statements(statements: list[dict], dataset: str = DATASET) -> list[Claim]:
    claims = [_to_claim(s) for s in statements]
    await add_data_points(claims)          # writes to Kuzu (graph) + LanceDB (vectors)
    print(f"[coherence] ingested {len(claims)} claims")
    return claims
