"""
Phase 3 orchestration: run the custom contradiction pipeline via memify().
"""
from __future__ import annotations

import cognee
from cognee.modules.pipelines.tasks.task import Task

from .config import CLAIMS_NODE_SET, DATASET
from .tasks import detect_contradictions, find_candidate_pairs


async def run_detection(dataset: str = DATASET) -> None:
    """
    Verified signature:
      memify(extraction_tasks, enrichment_tasks, data, dataset, user,
             node_type=NodeSet, node_name, vector_db_config, graph_db_config,
             run_in_background)

    We scope to the 'claims' NodeSet via `node_name` so the LLM never sees
    unrelated chunks.
    """
    await cognee.memify(
        extraction_tasks=[Task(find_candidate_pairs)],
        enrichment_tasks=[Task(detect_contradictions)],
        dataset=dataset,
        node_name=[CLAIMS_NODE_SET],
    )
