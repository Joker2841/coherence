"""
Agent guardrail demo: an AI clinical assistant consults Coherence BEFORE acting.
It refuses to order blood while the patient's records contradict each other, then
proceeds safely once a human resolves the conflict.

    python scripts/run_guardrail.py
"""
import asyncio
import json
from pathlib import Path

from coherence import config
config.setup()

import cognee
from coherence.detect import detect
from coherence.guardrail import SafeAgent
from coherence.ingest import ingest_statements

DATA = Path(__file__).resolve().parent.parent / "data"


async def main():
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    claims = await ingest_statements(json.loads((DATA / "medical_agent.json").read_text()))
    conflicts = await detect(claims)

    agent = SafeAgent()
    bar = "=" * 66
    print(f"\n{bar}\n  SCENARIO: clinical assistant preparing a transfusion for patient_017\n{bar}")

    print("\n[agent]  What blood type should I order for patient_017's transfusion?")
    print(agent.act("order blood", "patient_017", "blood_type", claims, conflicts).render())

    print("\n--- a nurse reviews the flagged conflict ---")
    print("[human]  Verified against the wristband: Chart A (O+) is correct. Retracting Chart B (A+).")
    for c in claims:
        if c.object == "A+":
            c.status = "retracted"
    for cf in conflicts:
        cf.resolved = True

    print("\n[agent]  What blood type should I order for patient_017's transfusion?")
    print(agent.act("order blood", "patient_017", "blood_type", claims, conflicts).render())

    print(f"\n{bar}\n  The agent never acted on conflicting memory. That is the integrity layer.\n{bar}\n")


if __name__ == "__main__":
    asyncio.run(main())