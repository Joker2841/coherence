// Single data seam. MOCK mode (no VITE_API_BASE) uses bundled data; LIVE mode
// talks to Sai's server. Both paths return the same internal
// { nodes, edges, conflicts, metrics, recall } shape so components never know.
//
// `force` flag: when the app finds the backend unreachable it flips to
// force=true and everything falls back to mock.

import { DATASETS, mockDetect } from "./data.js";

const BASE = import.meta.env.VITE_API_BASE || null;
export const isLive = !!BASE;
export const apiBase = BASE;

// frontend key ("doug") -> backend dataset name ("doug_witnesses")
const backendName = (key) => DATASETS[key]?.backend || key;

// --- contract -> internal adapters ---------------------------------------
function adaptNode(n) {
  return { id: n.id, subject: n.subject, predicate: n.predicate, object: n.object,
    text: n.text, time: n.valid_from, source: n.source, status: n.status || "active", source_trust: n.source_trust };
}
const adaptEdge = (e) => ({ id: e.id, source: e.source, target: e.target, type: e.type });
function adaptConflict(c) {
  return { id: c.id, type: c.type, by: c.detected_by, conf: c.confidence, winner: c.winner_id,
    verdict: c.verdict, resolved: c.resolved,
    a: { id: c.claim_a?.id, object: c.claim_a?.object, source: c.claim_a?.source },
    b: { id: c.claim_b?.id, object: c.claim_b?.object, source: c.claim_b?.source } };
}
const adopt = (g, c) => ({
  nodes: (g.nodes || []).map(adaptNode),
  edges: (g.edges || []).map(adaptEdge),
  conflicts: (c.conflicts || []).map(adaptConflict),
  metrics: c.metrics || null,
});

async function getJSON(url, opts) {
  const r = await fetch(url, opts);              // throws on network error
  if (!r.ok) throw new Error(`${(opts && opts.method) || "GET"} ${url} -> ${r.status}`);
  return r.json();
}

// Full snapshot: graph + conflicts + (optional) live recall answer.
async function getState(dsKey) {
  const [g, c, r] = await Promise.all([
    getJSON(`${BASE}/graph`),
    getJSON(`${BASE}/conflicts`),
    getJSON(`${BASE}/recall/${backendName(dsKey)}`).catch(() => null), // recall optional; never fails state
  ]);
  return { ...adopt(g, c), recall: r };
}

const useMock = (force) => !isLive || force;

// --- the flow the UI drives ----------------------------------------------
export async function ingest(dataset, force) {
  if (useMock(force)) return { ingested: DATASETS[dataset].nodes.length, dataset };
  return getJSON(`${BASE}/ingest/${backendName(dataset)}`, { method: "POST" });
}

export async function detect(dataset, useLLM, force) {
  if (useMock(force)) return mockDetect(dataset, useLLM);
  await getJSON(`${BASE}/detect?use_llm=${useLLM}`, { method: "POST" });
  return getState(dataset);
}

// Live: POST /resolve then refetch full snapshot. Mock: null (caller does local).
export async function resolve({ conflictId, winnerId, loserId, dataset }, force) {
  if (useMock(force)) return null;
  await getJSON(`${BASE}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conflict_id: conflictId, winner_claim_id: winnerId, loser_claim_id: loserId }),
  });
  return getState(dataset);
}
