// Bundled mock data — used in MOCK mode (no backend) and as the demo fallback.
// Shapes mirror the API contract so the same components render live data.

export const DATASETS = {
  doug: {
    label: "The Missing Groom", no: "01", backend: "doug_witnesses",
    blurb: "Four witnesses. One vanished groom. Where was Doug?",
    truth: 6,
    recall: { query: "Where is Doug?", subject: "Doug", predicate: "location" },
    nodes: [
      { id: "w1_groom",   subject: "Doug", predicate: "role",     object: "the groom",      text: "Doug is the groom; the wedding is Sunday.",  time: "2025-06-27T10:00:00", source: "Phil",     base: "active" },
      { id: "w4_caesars", subject: "Doug", predicate: "event",    object: "party @ Caesars", text: "Doug's bachelor party started at Caesars.",  time: "2025-06-27T20:00:00", source: "Alan",     base: "active" },
      { id: "w2_roof",    subject: "Doug", predicate: "location", object: "hotel roof",      text: "At 9 PM, Doug was on the hotel roof.",        time: "2025-06-27T21:00:00", source: "Phil",     base: "superseded" },
      { id: "w3_pool",    subject: "Doug", predicate: "location", object: "pool bar",        text: "At 9 PM, Doug was at the pool bar.",          time: "2025-06-27T21:00:00", source: "Stu",      base: "superseded" },
      { id: "w6_suite",   subject: "Doug", predicate: "location", object: "hotel suite",     text: "Doug never left the hotel suite all night.", time: "2025-06-27T23:00:00", source: "Mr. Chow", base: "superseded" },
      { id: "w7_airport", subject: "Doug", predicate: "location", object: "airport",         text: "A taxi dropped Doug at the airport at 11 PM.",time: "2025-06-27T23:00:00", source: "Taxi log", base: "superseded" },
      { id: "w5_chapel",  subject: "Doug", predicate: "location", object: "wedding chapel",  text: "Doug has now been found at the chapel.",      time: "2025-06-28T07:00:00", source: "Stu",      base: "active" },
    ],
    edges: [
      { id: "e1", source: "w2_roof",  target: "w3_pool",    type: "contradicts" },
      { id: "e2", source: "w6_suite", target: "w7_airport", type: "contradicts" },
      { id: "e3", source: "w5_chapel", target: "w2_roof",   type: "supersedes" },
      { id: "e4", source: "w5_chapel", target: "w3_pool",   type: "supersedes" },
      { id: "e5", source: "w5_chapel", target: "w6_suite",  type: "supersedes" },
      { id: "e6", source: "w5_chapel", target: "w7_airport", type: "supersedes" },
    ],
    conflicts: [
      { id: "c1", type: "contradiction", by: "deterministic", conf: 1.0, winner: null,
        verdict: "Doug is on the 'hotel roof' AND at the 'pool bar' at 9 PM — one account is false.",
        a: { id: "w2_roof", object: "hotel roof", source: "Phil" }, b: { id: "w3_pool", object: "pool bar", source: "Stu" } },
      { id: "c2", type: "contradiction", by: "deterministic", conf: 1.0, winner: null,
        verdict: "Doug is in the 'hotel suite' AND at the 'airport' at 11 PM — one account is false.",
        a: { id: "w6_suite", object: "hotel suite", source: "Mr. Chow" }, b: { id: "w7_airport", object: "airport", source: "Taxi log" } },
      { id: "c3", type: "supersession", by: "deterministic", conf: 1.0, winner: "w5_chapel",
        verdict: "'hotel roof' (9 PM) superseded by 'wedding chapel' (next morning).",
        a: { id: "w2_roof", object: "hotel roof", source: "Phil" }, b: { id: "w5_chapel", object: "wedding chapel", source: "Stu" } },
      { id: "c4", type: "supersession", by: "deterministic", conf: 1.0, winner: "w5_chapel",
        verdict: "'pool bar' (9 PM) superseded by 'wedding chapel' (next morning).",
        a: { id: "w3_pool", object: "pool bar", source: "Stu" }, b: { id: "w5_chapel", object: "wedding chapel", source: "Stu" } },
      { id: "c5", type: "supersession", by: "deterministic", conf: 1.0, winner: "w5_chapel",
        verdict: "'hotel suite' (11 PM) superseded by 'wedding chapel' (next morning).",
        a: { id: "w6_suite", object: "hotel suite", source: "Mr. Chow" }, b: { id: "w5_chapel", object: "wedding chapel", source: "Stu" } },
      { id: "c6", type: "supersession", by: "deterministic", conf: 1.0, winner: "w5_chapel",
        verdict: "'airport' (11 PM) superseded by 'wedding chapel' (next morning).",
        a: { id: "w7_airport", object: "airport", source: "Taxi log" }, b: { id: "w5_chapel", object: "wedding chapel", source: "Stu" } },
    ],
  },
  agent: {
    label: "The Agent's Memory", no: "02", backend: "agent_memory",
    blurb: "An assistant, many sessions deep. What does it still believe?",
    truth: 3,
    recall: { query: "When is the Q3 review?", subject: "q3_review", predicate: "date" },
    nodes: [
      { id: "m1_veg",     subject: "user",      predicate: "diet",       object: "vegetarian", text: "The user is vegetarian and avoids all meat.", time: "2025-03-01T09:00:00", source: "session 12", base: "active" },
      { id: "m2_steak",   subject: "user",      predicate: "meal_order", object: "steak",      text: "The user ordered a medium-rare steak.",       time: "2025-06-20T19:30:00", source: "session 88", base: "active" },
      { id: "m3_wed",     subject: "q3_review", predicate: "date",       object: "Wednesday",  text: "The Q3 review is scheduled for Wednesday.",   time: "2025-06-10T11:00:00", source: "session 40", base: "superseded" },
      { id: "m4_fri",     subject: "q3_review", predicate: "date",       object: "Friday",     text: "Update: the Q3 review moved to Friday.",       time: "2025-06-18T14:00:00", source: "session 57", base: "active" },
      { id: "m5_sarah",   subject: "user",      predicate: "manager",    object: "Sarah",      text: "The user's manager is Sarah.",                time: "2025-01-05T10:00:00", source: "session 15", base: "superseded" },
      { id: "m6_david",   subject: "user",      predicate: "manager",    object: "David",      text: "After the reorg, the user reports to David.", time: "2025-06-22T16:00:00", source: "session 90", base: "active" },
      { id: "m7_morning", subject: "user",      predicate: "prefers",    object: "mornings",   text: "The user prefers morning meetings.",          time: "2025-02-01T08:00:00", source: "session 20", base: "active" },
    ],
    edges: [
      { id: "me1", source: "m4_fri",   target: "m3_wed",   type: "supersedes" },
      { id: "me2", source: "m6_david", target: "m5_sarah", type: "supersedes" },
      { id: "me3", source: "m1_veg",   target: "m2_steak", type: "contradicts", semantic: true },
    ],
    conflicts: [
      { id: "ac1", type: "supersession", by: "deterministic", conf: 1.0, winner: "m4_fri",
        verdict: "q3_review.date: 'Wednesday' (Jun 10) superseded by 'Friday' (Jun 18).",
        a: { id: "m3_wed", object: "Wednesday", source: "session 40" }, b: { id: "m4_fri", object: "Friday", source: "session 57" } },
      { id: "ac2", type: "supersession", by: "deterministic", conf: 1.0, winner: "m6_david",
        verdict: "user.manager: 'Sarah' (Jan) superseded by 'David' (Jun, post-reorg).",
        a: { id: "m5_sarah", object: "Sarah", source: "session 15" }, b: { id: "m6_david", object: "David", source: "session 90" } },
      { id: "ac3", type: "semantic", by: "llm", conf: 0.85, winner: null, semantic: true,
        verdict: "User is vegetarian, but ordered steak — the meal contradicts the stated diet.",
        a: { id: "m1_veg", object: "vegetarian", source: "session 12" }, b: { id: "m2_steak", object: "steak", source: "session 88" } },
    ],
  },
};

// Mirror the backend's detect result from bundled data (respecting the LLM tier).
export function mockDetect(dsKey, useLLM) {
  const ds = DATASETS[dsKey];
  const edges = ds.edges.filter((e) => !e.semantic || useLLM);
  const conflicts = ds.conflicts.filter((c) => c.by !== "llm" || useLLM);
  const nodes = ds.nodes.map((n) => ({ ...n, status: "active" }));
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  conflicts.forEach((c) => {
    if (c.type === "supersession") {
      const loser = c.a.id === c.winner ? c.b.id : c.a.id;
      if (byId[loser]) byId[loser].status = "superseded";
    }
  });
  const tp = conflicts.length, fp = 0, fn = ds.truth - tp;
  const P = tp + fp ? tp / (tp + fp) : 0;
  const R = tp + fn ? tp / (tp + fn) : 0;
  const F = P + R ? (2 * P * R) / (P + R) : 0;
  return { nodes, edges, conflicts, metrics: { precision: P, recall: R, f1: F, tp, fp, fn } };
}
