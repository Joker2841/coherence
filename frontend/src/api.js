// Single data seam. MOCK mode (no VITE_API_BASE) uses bundled data; LIVE mode
// talks to Sai's server. Components never know the difference — both paths
// return the same internal { nodes, edges, conflicts, metrics } shape.

import { DATASETS, mockDetect } from "./data.js";

const BASE = import.meta.env.VITE_API_BASE || null;
export const isLive = !!BASE;
export const apiBase = BASE;

// --- contract -> internal adapters ---------------------------------------
function adaptNode(n) {
  return {
    id: n.id, subject: n.subject, predicate: n.predicate, object: n.object,
    text: n.text, time: n.valid_from, source: n.source,
    status: n.status || "active", source_trust: n.source_trust,
  };
}
function adaptEdge(e) {
  return { id: e.id, source: e.source, target: e.target, type: e.type };
}
function adaptConflict(c) {
  return {
    id: c.id, type: c.type, by: c.detected_by, conf: c.confidence,
    winner: c.winner_id, verdict: c.verdict, resolved: c.resolved,
    a: { id: c.claim_a?.id, object: c.claim_a?.object, source: c.claim_a?.source },
    b: { id: c.claim_b?.id, object: c.claim_b?.object, source: c.claim_b?.source },
  };
}
function adopt(graph, conflicts) {
  return {
    nodes: (graph.nodes || []).map(adaptNode),
    edges: (graph.edges || []).map(adaptEdge),
    conflicts: (conflicts.conflicts || []).map(adaptConflict),
    metrics: conflicts.metrics || null,
  };
}

async function getState() {
  const [g, c] = await Promise.all([
    fetch(`${BASE}/graph`).then((r) => r.json()),
    fetch(`${BASE}/conflicts`).then((r) => r.json()),
  ]);
  return adopt(g, c);
}

// --- the flow the UI drives ----------------------------------------------
export async function ingest(dataset) {
  if (!isLive) return { ingested: DATASETS[dataset].nodes.length, dataset };
  const r = await fetch(`${BASE}/ingest/${dataset}`, { method: "POST" });
  return r.json();
}

export async function detect(dataset, useLLM) {
  if (!isLive) return mockDetect(dataset, useLLM);
  await fetch(`${BASE}/detect?use_llm=${useLLM}`, { method: "POST" });
  return getState();
}

// Live: POST /resolve then refetch. Mock: caller updates local state.
export async function resolve({ conflictId, winnerId, loserId }) {
  if (!isLive) return null;
  await fetch(`${BASE}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conflict_id: conflictId, winner_claim_id: winnerId, loser_claim_id: loserId }),
  });
  return getState();
}
