"""
Demo/test helper: runs the full flow against a RUNNING server and resolves the
first real contradiction (no placeholder IDs to fumble). Watch Phil's trust drop.

    python scripts/try_resolve.py      # server must be up on :8000
"""
import json
import urllib.request

BASE = "http://localhost:8000"


def _get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def _post(path, body=None):
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(BASE + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


_post("/ingest/doug_witnesses")
_post("/detect?use_llm=false")

print("TRUST BEFORE:")
for s in _get("/trust")["sources"]:
    print(f"  {s['source']:10} trust={s['trust']}")

# grab the first real contradiction and resolve it (pool bar beats hotel roof)
conflict = next(c for c in _get("/conflicts")["conflicts"] if c["type"] == "contradiction")
a, b = conflict["claim_a"], conflict["claim_b"]
loser = a if a["object"] == "hotel roof" else b
winner = b if loser is a else a

print(f"\nresolving: {conflict['verdict']}")
print(f"  winner: {winner['source']} ({winner['object']})")
print(f"  loser : {loser['source']} ({loser['object']})")

_post("/resolve", {"conflict_id": conflict["id"],
                   "winner_claim_id": winner["id"],
                   "loser_claim_id": loser["id"]})

print("\nTRUST AFTER:")
for s in _get("/trust")["sources"]:
    flag = "  <-- dropped" if s["trust"] < 1.0 else ""
    print(f"  {s['source']:10} trust={s['trust']}  (W{s['wins']}/L{s['losses']}){flag}")