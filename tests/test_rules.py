import coherence.rules as rules

# The 7 curated Doug claims (id, subject, predicate, object, valid_from, ref)
DOUG = [
    {"id": "1", "ref": "w1_groom",   "subject": "Doug", "predicate": "role",     "object": "groom",         "valid_from": "2025-06-27T10:00:00"},
    {"id": "2", "ref": "w2_roof",    "subject": "Doug", "predicate": "location", "object": "hotel roof",    "valid_from": "2025-06-27T21:00:00"},
    {"id": "3", "ref": "w3_pool",    "subject": "Doug", "predicate": "location", "object": "pool bar",      "valid_from": "2025-06-27T21:00:00"},
    {"id": "4", "ref": "w4_caesars", "subject": "Doug", "predicate": "event",    "object": "bachelor party","valid_from": "2025-06-27T20:00:00"},
    {"id": "5", "ref": "w5_chapel",  "subject": "Doug", "predicate": "location", "object": "wedding chapel","valid_from": "2025-06-28T07:00:00"},
    {"id": "6", "ref": "w6_suite",   "subject": "Doug", "predicate": "location", "object": "hotel suite",   "valid_from": "2025-06-27T23:00:00"},
    {"id": "7", "ref": "w7_airport", "subject": "Doug", "predicate": "location", "object": "airport",       "valid_from": "2025-06-27T23:00:00"},
]


def _pairs(items, ka, kb):
    return {frozenset((c[ka], c[kb])) for c in items}


def test_contradictions_exact():
    c = rules.find_contradictions(DOUG)
    pairs = _pairs(c, "a_ref", "b_ref")
    assert pairs == {frozenset(("w2_roof", "w3_pool")), frozenset(("w6_suite", "w7_airport"))}
    assert all(x["type"] == "contradiction" and x["confidence"] == 1.0 for x in c)


def test_supersessions_exact():
    s = rules.find_supersessions(DOUG)
    pairs = _pairs(s, "older_ref", "newer_ref")
    assert pairs == {
        frozenset(("w2_roof", "w5_chapel")), frozenset(("w3_pool", "w5_chapel")),
        frozenset(("w6_suite", "w5_chapel")), frozenset(("w7_airport", "w5_chapel")),
    }
    assert all(x["newer_ref"] == "w5_chapel" for x in s)   # all resolve to the latest


def test_none_timestamp_not_same_time():
    # two unknown-time claims, different objects -> must NOT be a same-time contradiction
    claims = [
        {"id": "a", "subject": "X", "predicate": "location", "object": "p", "valid_from": None},
        {"id": "b", "subject": "X", "predicate": "location", "object": "q", "valid_from": None},
    ]
    assert rules.find_contradictions(claims) == []


def test_same_object_no_conflict():
    claims = [
        {"id": "a", "subject": "X", "predicate": "location", "object": "p", "valid_from": "2025-01-01T00:00:00"},
        {"id": "b", "subject": "X", "predicate": "location", "object": "p", "valid_from": "2025-01-01T00:00:00"},
    ]
    assert rules.find_contradictions(claims) == []
    assert rules.find_supersessions(claims) == []


def test_different_predicate_not_compared():
    claims = [
        {"id": "a", "subject": "Doug", "predicate": "role",  "object": "groom", "valid_from": "2025-01-01T09:00:00"},
        {"id": "b", "subject": "Doug", "predicate": "event", "object": "party", "valid_from": "2025-01-01T09:00:00"},
    ]
    assert rules.find_contradictions(claims) == []   # different aspects coexist


def test_canon_predicate():
    for syn in ["whereabouts", "spotted", "was at", "position", "Location", " LOCATION "]:
        assert rules.canon_predicate(syn) == "location"
    assert rules.canon_predicate("reports to") == "manager"
    assert rules.canon_predicate("unseen_pred") == "unseen_pred"  # unknown kept as-is


def test_score_perfect_and_penalized():
    labeled = [
        {"a": "w2_roof", "b": "w3_pool", "is_contradiction": True},
        {"a": "w6_suite", "b": "w7_airport", "is_contradiction": True},
        {"a": "w1_groom", "b": "w4_caesars", "is_contradiction": False},
    ]
    perfect = {frozenset(("w2_roof", "w3_pool")), frozenset(("w6_suite", "w7_airport"))}
    r = rules.score(perfect, labeled)
    assert (r["precision"], r["recall"], r["f1"]) == (1.0, 1.0, 1.0)

    # a false positive on the labeled-negative pair drops precision
    with_fp = perfect | {frozenset(("w1_groom", "w4_caesars"))}
    r2 = rules.score(with_fp, labeled)
    assert r2["recall"] == 1.0 and r2["precision"] < 1.0 and r2["fp"] == 1


def test_numeric_contradiction_and_equality():
    same_time = "2024-10-01T00:00:00"
    claims = [
        {"id": "5m",  "ref": "5m",  "subject": "Co", "predicate": "revenue", "object": "$5M",        "valid_from": same_time},
        {"id": "7m",  "ref": "7m",  "subject": "Co", "predicate": "revenue", "object": "$7M",        "valid_from": same_time},
        {"id": "5mf", "ref": "5mf", "subject": "Co", "predicate": "revenue", "object": "$5,000,000", "valid_from": same_time},
    ]
    pairs = {frozenset((c["a_ref"], c["b_ref"])) for c in rules.find_contradictions(claims)}
    assert frozenset(("5m", "7m")) in pairs       # 5M vs 7M -> conflict
    assert frozenset(("7m", "5mf")) in pairs      # 7M vs 5M -> conflict
    assert frozenset(("5m", "5mf")) not in pairs  # 5M == 5,000,000 -> NOT a conflict


def test_numeric_supersession():
    claims = [
        {"id": "a", "ref": "a", "subject": "P", "predicate": "budget", "object": "$2M", "valid_from": "2024-01-01T00:00:00"},
        {"id": "b", "ref": "b", "subject": "P", "predicate": "budget", "object": "$3M", "valid_from": "2024-06-01T00:00:00"},
    ]
    s = rules.find_supersessions(claims)
    assert len(s) == 1 and s[0]["newer_ref"] == "b"


def test_alphanumeric_not_parsed_as_number():
    assert rules.numeric_value("B12") is None      # gate, not the number 12
    assert rules.numeric_value("us-east") is None
    assert rules.numeric_value("O+") is None
    assert rules.numeric_value("$5M") == 5_000_000
    assert rules.numeric_value("99.9") == 99.9