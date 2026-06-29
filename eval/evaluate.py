"""
Precision / recall harness over the labeled set of known conflicts.

Run AFTER detection so you can score what the engine actually caught:

    python eval/evaluate.py

This is a differentiator: almost no hackathon team shows real metrics. Wire
`predicted_pairs` to the Contradictions your run produced (read them from the
graph, or capture them as detection yields them).
"""
from __future__ import annotations

import json
from pathlib import Path

LABELED = Path(__file__).resolve().parent / "labeled_set.json"


def score(predicted_pairs: set[frozenset], labeled: list[dict]) -> dict:
    truth = {frozenset((x["a"], x["b"])): x["is_contradiction"] for x in labeled}
    tp = sum(1 for k, v in truth.items() if v and k in predicted_pairs)
    fp = sum(1 for k in predicted_pairs if not truth.get(k, False))
    fn = sum(1 for k, v in truth.items() if v and k not in predicted_pairs)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


if __name__ == "__main__":
    labeled = json.loads(LABELED.read_text())["pairs"]

    # TODO: replace with the pairs your detection flagged, e.g.
    #   predicted_pairs = {frozenset((c.claim_a_id, c.claim_b_id)) for c in contradictions}
    predicted_pairs: set[frozenset] = set()

    print(json.dumps(score(predicted_pairs, labeled), indent=2))
