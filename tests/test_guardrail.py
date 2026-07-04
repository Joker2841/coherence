from types import SimpleNamespace as NS
from coherence import guardrail as g

def claim(cid, subj, pred, obj, t, status="active"):
    return NS(id=cid, subject=subj, predicate=pred, object=obj, valid_from=t, status=status)
def conflict(a, b, typ="contradiction", resolved=False, verdict="v"):
    return NS(claim_a_id=a, claim_b_id=b, conflict_type=typ, resolved=resolved, verdict=verdict)

# patient with a live blood-type contradiction
C = [claim("b1","patient_017","blood_type","O+","2024-01-05T09:00:00"),
     claim("b2","patient_017","blood_type","A+","2024-01-05T09:00:00"),
     claim("b3","patient_017","attending","Dr. Lee","2024-01-05T08:00:00")]
K = [conflict("b1","b2", verdict="blood_type is both O+ and A+")]

agent = g.SafeAgent()

# 1) live contradiction on the target predicate -> BLOCK
d = agent.act("order blood", "patient_017", "blood_type", C, K)
assert d.blocked and len(d.conflicts) == 1, d

# 2) acting on a DIFFERENT predicate (attending) is not blocked by the blood conflict
d2 = agent.act("page doctor", "patient_017", "attending", C, K)
assert not d2.blocked and d2.value == "Dr. Lee", d2

# 3) after resolution (retract A+), the contradiction no longer blocks -> PROCEED with O+
C[1].status = "retracted"
d3 = agent.act("order blood", "patient_017", "blood_type", C, K)
assert not d3.blocked and d3.value == "O+", d3

# 4) a RESOLVED conflict doesn't block even if both claims were active
C[1].status = "active"; K[0].resolved = True
d4 = agent.act("order blood", "patient_017", "blood_type", C, K)
assert not d4.blocked, d4

print("PASS: guardrail blocks on live conflict, ignores unrelated predicates,")
print("      clears after retract, and respects resolved flags")