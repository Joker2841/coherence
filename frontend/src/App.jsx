import { useState, useMemo } from "react";
import { Search, Play, RotateCcw, Zap } from "lucide-react";
import * as api from "./api.js";
import { DATASETS } from "./data.js";
import { runLayout, clamp, W, H } from "./lib.js";
import CaseBoard from "./CaseBoard.jsx";
import ConflictLog from "./ConflictLog.jsx";

export default function App() {
  const [dsKey, setDsKey] = useState("doug");
  const [phase, setPhase] = useState("empty");        // empty | ingested | detected
  const [useLLM, setUseLLM] = useState(true);
  const [busy, setBusy] = useState(false);

  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [positions, setPositions] = useState({});
  const [status, setStatus] = useState({});           // id -> status
  const [resolved, setResolved] = useState({});        // conflictId -> winnerId
  const [pulse, setPulse] = useState(null);
  const [selected, setSelected] = useState(null);

  const meta = DATASETS[dsKey];

  const reset = () => {
    setPhase("empty"); setNodes([]); setEdges([]); setConflicts([]); setMetrics(null);
    setPositions({}); setStatus({}); setResolved({}); setPulse(null); setSelected(null);
  };
  const pick = (k) => { if (k !== dsKey) { setDsKey(k); reset(); } };

  const ingest = async () => {
    setBusy(true);
    try { await api.ingest(dsKey); setPhase("ingested"); }
    finally { setBusy(false); }
  };

  const applyState = (d) => {
    setNodes(d.nodes); setEdges(d.edges); setConflicts(d.conflicts); setMetrics(d.metrics);
    const st = {}; d.nodes.forEach((n) => { st[n.id] = n.status || "active"; }); setStatus(st);
    const rmap = {}; (d.conflicts || []).forEach((c) => { if (c.resolved && c.winner) rmap[c.id] = c.winner; }); setResolved(rmap);
    setPositions(runLayout(d.nodes, d.edges));
  };

  const detect = async () => {
    setBusy(true);
    try {
      const d = await api.detect(dsKey, useLLM);
      setSelected(null); applyState(d); setPhase("detected");
    } finally { setBusy(false); }
  };

  const driftLoser = (loser) => setPositions((prev) => {
    const lp = prev[loser] || { x: W / 2, y: H / 2 };
    const dx = lp.x - W / 2, dy = lp.y - H / 2, d = Math.hypot(dx, dy) || 1;
    return { ...prev, [loser]: { x: clamp(lp.x + (dx / d) * 86, 30, W - 30), y: clamp(lp.y + (dy / d) * 86, 24, H - 24) } };
  });

  const resolve = async (conflict, chosenWinner) => {
    const winner = chosenWinner || conflict.winner || conflict.a.id;
    const loser = winner === conflict.a.id ? conflict.b.id : conflict.a.id;
    setPulse(winner); setTimeout(() => setPulse((p) => (p === winner ? null : p)), 1200);

    if (api.isLive) {
      const d = await api.resolve({ conflictId: conflict.id, winnerId: winner, loserId: loser });
      if (d) { applyState(d); driftLoser(loser); }
    } else {
      const nextStatus = { ...status, [loser]: "retracted", [winner]: "active" };
      const nextResolved = { ...resolved, [conflict.id]: winner };
      conflicts.forEach((c) => {
        if (nextResolved[c.id]) return;
        if (c.a.id === loser || c.b.id === loser) { const w = c.a.id === loser ? c.b.id : c.a.id; nextResolved[c.id] = c.winner || w; }
      });
      setStatus(nextStatus); setResolved(nextResolved); driftLoser(loser);
    }
    if (selected === conflict.id) setSelected(null);
  };

  const nodeById = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  const recall = useMemo(() => {
    const { subject, predicate } = meta.recall;
    return nodes.filter((n) => n.subject === subject && n.predicate === predicate && (status[n.id] || "active") === "active");
  }, [nodes, status, meta]);

  const allResolved = phase === "detected" && conflicts.length > 0 && Object.keys(resolved).length === conflicts.length;
  const statusWord = phase === "empty" || phase === "ingested" ? (phase === "ingested" ? "OPEN" : "—") : allResolved ? "SOLVED" : "OPEN";
  const pct = (x) => Math.round((x || 0) * 100);

  return (
    <div className="coh">
      <header className="bar">
        <div className="brand">
          <span className="suit">♠</span>
          <div className="bwrap">
            <div className="logo">COHERENCE</div>
            <div className="sub">memory integrity · case board{api.isLive ? " · live" : ""}</div>
          </div>
        </div>

        <div className="controls">
          <div className="seg">
            {Object.keys(DATASETS).map((k) => (
              <button key={k} className={"segbtn" + (k === dsKey ? " on" : "")} onClick={() => pick(k)}>{k === "doug" ? "Case 01" : "Case 02"}</button>
            ))}
          </div>
          <button className="btn" onClick={ingest} disabled={busy || phase !== "empty"}><Play size={13} />Ingest</button>
          <button className="btn go" onClick={detect} disabled={busy || phase === "empty"}><Search size={13} />Run detection</button>
          <button className={"toggle" + (useLLM ? " on" : "")} onClick={() => setUseLLM((v) => !v)}><Zap size={12} />LLM {useLLM ? "on" : "off"}</button>
          <button className="btn ico" onClick={reset} title="New case"><RotateCcw size={13} /></button>
        </div>

        {phase === "detected" && metrics && (
          <div className="stats">
            <b className={pct(metrics.precision) >= 100 ? "" : "w"}>{pct(metrics.precision)}%</b><span>prec</span>
            <b className={pct(metrics.recall) >= 100 ? "" : "w"}>{pct(metrics.recall)}%</b><span>rec</span>
            <b>{metrics.tp}<i>/{meta.truth}</i></b><span>flagged</span>
          </div>
        )}
      </header>

      <div className="cover">
        <div className="cno">CASE No. {meta.no}</div>
        <div className="ctitle">{meta.label}</div>
        <div className="cright">
          <span className="qq">{meta.recall.query}</span>
          <span className={"stat " + statusWord.toLowerCase()}>{statusWord}</span>
          <span className={"ans " + (phase === "empty" || phase === "ingested" ? "muted" : recall.length === 1 ? (allResolved ? "ok" : "lead") : "bad")}>
            {phase === "empty" ? "ingest to open the case"
              : phase === "ingested" ? "run detection…"
              : recall.length === 1 ? (allResolved ? recall[0].object : "leading: " + recall[0].object)
              : recall.length + " conflicting accounts"}
          </span>
        </div>
      </div>

      <div className="body">
        <CaseBoard
          meta={meta} phase={phase} nodes={nodes} edges={edges} conflicts={conflicts}
          status={status} resolved={resolved} positions={positions} pulse={pulse}
          selected={selected} onSelectConflict={setSelected}
        />
        <ConflictLog
          phase={phase} conflicts={conflicts} resolved={resolved} selected={selected}
          onSelect={setSelected} onResolve={resolve} nodeById={nodeById}
        />
      </div>

      <footer className="foot2">
        <span>{api.isLive ? `live · ${api.apiBase}` : "mock · bundled data"}</span>
        <span className="dim">POST /ingest → POST /detect → GET /graph · /conflicts → POST /resolve</span>
      </footer>
    </div>
  );
}
