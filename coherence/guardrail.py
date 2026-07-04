"""
Agent guardrail: an agent consults Coherence BEFORE it acts and REFUSES when the
memory it would rely on contains an unresolved contradiction. The integrity layer
as a safety gate, not just a debugger.

Pure gate logic (find_blocking_conflicts / active_value) is unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _sid(c):
    return str(getattr(c, "id", ""))


def _active(c):
    return getattr(c, "status", "active") != "retracted"


def find_blocking_conflicts(subject, predicate, claims, conflicts):
    """Unresolved conflicts where BOTH sides are still live and at least one is a
    claim about the (subject, predicate) the agent is about to act on."""
    active_ids = {_sid(c) for c in claims if _active(c)}
    target_ids = {_sid(c) for c in claims
                  if c.subject == subject and c.predicate == predicate and _active(c)}
    blocking = []
    for cf in conflicts:
        if getattr(cf, "conflict_type", None) not in ("contradiction", "semantic"):
            continue
        if getattr(cf, "resolved", False):
            continue
        a, b = getattr(cf, "claim_a_id", ""), getattr(cf, "claim_b_id", "")
        if a in active_ids and b in active_ids and (a in target_ids or b in target_ids):
            blocking.append(cf)
    return blocking


def active_value(subject, predicate, claims):
    cand = [c for c in claims
            if c.subject == subject and c.predicate == predicate and _active(c)]
    if not cand:
        return None
    return max(cand, key=lambda c: c.valid_from or "").object


@dataclass
class Decision:
    blocked: bool
    subject: str
    predicate: str
    value: str | None = None
    conflicts: list = field(default_factory=list)

    def render(self) -> str:
        if self.blocked:
            lines = [f"[coherence] BLOCKED -- refusing to act on {self.subject}.{self.predicate}:"]
            for cf in self.conflicts:
                lines.append(f"    [!] {cf.verdict}")
            lines.append("    Conflicting records; human review required before proceeding.")
            return "\n".join(lines)
        return (f"[coherence] CLEAR -- no unresolved conflict on {self.subject}.{self.predicate}.\n"
                f"[agent]     Proceeding: {self.value}")


class SafeAgent:
    """An agent that gates every action through Coherence."""

    def act(self, task, subject, predicate, claims, conflicts) -> Decision:
        blocking = find_blocking_conflicts(subject, predicate, claims, conflicts)
        if blocking:
            return Decision(True, subject, predicate, conflicts=blocking)
        return Decision(False, subject, predicate, value=active_value(subject, predicate, claims))