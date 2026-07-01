"""
Graph node models.

Both inherit from Cognee's DataPoint, so each becomes a first-class graph node:
auto-generated IDs, vector indexing on `index_fields`, DB routing, and
provenance stamping (source_pipeline / source_task) -- the last is what powers
the debugger's "why does the agent believe this?" audit view.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import SkipValidation

from cognee.infrastructure.engine import DataPoint


class Claim(DataPoint):
    """A single atomic assertion extracted from a source statement."""

    text: str                          # e.g. "Doug is on the hotel roof at 9 PM"
    subject: str                       # "Doug"
    predicate: str                     # "location"
    object: str                        # "hotel roof"
    valid_from: Optional[str] = None   # ISO timestamp, populated by temporal_cognify
    source: Optional[str] = None       # witness / session id that asserted it
    confidence: float = 1.0
    status: str = "active"             # active | superseded | retracted
    ref_id: Optional[str] = None   # human-readable dataset id, for eval mapping

    # Only `text` is embedded -> cheap semantic candidate-finding during detection.
    metadata: dict = {"index_fields": ["text"]}


class Contradiction(DataPoint):
    """A detected conflict between two Claims. A first-class node, not just an edge."""

    # Referencing the Claim OBJECTS (not only ids) is what creates the graph edges.
    # Populate these where you have the node objects on hand; ids always set.
    claim_a: SkipValidation[Any] = None
    claim_b: SkipValidation[Any] = None

    claim_a_id: str = ""
    claim_b_id: str = ""
    ref_a: str = ""
    ref_b: str = ""
    conflict_type: str = "semantic"    # "temporal_supersession" | "semantic"
    verdict: str = ""                  # human-readable explanation
    confidence: float = 0.0
    resolved: bool = False
    winner_claim_id: Optional[str] = None

    metadata: dict = {"index_fields": ["verdict"]}
