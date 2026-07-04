from types import SimpleNamespace as NS
from coherence import guardrail as g


def _claim(cid, subj, pred, obj, t, status="active"):
    return NS(id=cid, subject=subj, predicate=pred, object=obj, valid_from=t, status=status)


def _conflict(a, b, typ="contradiction", resolved=False, verdict="v"):
    return NS(claim_a_id=a, claim_b_id=b, conflict_type=typ, resolved=resolved, verdict=verdict)


def test_guardrail_gate():
    C = [_claim("b1", "patient_017", "blood_type", "O+", "2024-01-05T09:00:00"),
         _claim("b2", "patient_017", "blood_type", "A+", "2024-01-05T09:00:00"),
         _claim("b3", "patient_017", "attending", "Dr. Lee", "2024-01-05T08:00:00")]
    K = [_conflict("b1", "b2", verdict="blood_type is both O+ and A+")]
    agent = g.SafeAgent()

    # live contradiction on the target predicate -> BLOCK
    d = agent.act("order blood", "patient_017", "blood_type", C, K)
    assert d.blocked and len(d.conflicts) == 1

    # unrelated predicate is not blocked by the blood conflict
    d2 = agent.act("page doctor", "patient_017", "attending", C, K)
    assert not d2.blocked and d2.value == "Dr. Lee"

    # after retracting A+, the contradiction clears -> PROCEED with O+
    C[1].status = "retracted"
    d3 = agent.act("order blood", "patient_017", "blood_type", C, K)
    assert not d3.blocked and d3.value == "O+"

    # a resolved conflict doesn't block even with both claims active
    C[1].status = "active"; K[0].resolved = True
    d4 = agent.act("order blood", "patient_017", "blood_type", C, K)
    assert not d4.blocked