"""
Source-trust scoring.

A source's reliability is LEARNED from how its claims fare in resolved
contradictions. Deterministic and explainable -- every score defends itself
on stage ("3 of Chow's 4 claims were overturned -> 0.25").

    trust = (wins + 1) / (wins + losses + 1)      # smoothed reliability rate

New source starts at 1.0. One loss -> 0.5. Sustained wins stay high.

Design note: only RESOLVED CONTRADICTIONS move trust -- not supersessions.
Being outdated (superseded) is not being wrong; a source shouldn't be
penalized for a claim that was accurate for its time. Only losing a genuine
same-time contradiction, where one party was actually wrong, dings trust.
"""
from __future__ import annotations

from collections import defaultdict


class TrustLedger:
    def __init__(self) -> None:
        self._wins: dict[str, int] = defaultdict(int)
        self._losses: dict[str, int] = defaultdict(int)
        self._sources: set[str] = set()

    def register(self, source: str | None) -> None:
        if source:
            self._sources.add(source)

    def record_resolution(self, winner_source: str | None, loser_source: str | None) -> None:
        if winner_source:
            self._sources.add(winner_source)
            self._wins[winner_source] += 1
        if loser_source:
            self._sources.add(loser_source)
            self._losses[loser_source] += 1

    def trust(self, source: str | None) -> float:
        if not source:
            return 1.0
        w, l = self._wins.get(source, 0), self._losses.get(source, 0)
        return round((w + 1) / (w + l + 1), 2)

    def all_trust(self) -> dict[str, float]:
        return {s: self.trust(s) for s in sorted(self._sources)}

    def leaderboard(self) -> list[dict]:
        rows = [{"source": s, "wins": self._wins.get(s, 0),
                 "losses": self._losses.get(s, 0), "trust": self.trust(s)}
                for s in self._sources]
        return sorted(rows, key=lambda r: (r["trust"], -r["losses"]))