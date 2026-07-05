import { useState, useMemo } from "react";
import { Search, Play, RotateCcw, Zap, Gavel, History } from "lucide-react";
import * as api from "./api.js";
import { DATASETS } from "./data.js";
import { runLayout, clamp, W, H, CW, CH } from "./lib.js";
import CaseBoard from "./CaseBoard.jsx";
import ConflictLog from "./ConflictLog.jsx";
import TimeMachine from "./TimeMachine.jsx";
import LifecycleRail from "./LifecycleRail.jsx";

export default function App() {
  const [dsKey, setDsKey] = useState("doug");
  const [phase, setPhase] = useState("empty");        // empty | ingested | detected
  const [useLLM, setUseLLM] = useState(true);
  const [busy, setBusy] = useState(false);
  const [solving, setSolving] = useState(false);
  const [mode, setMode] = useState("case");           // case | time

  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [positions, setPositions] = useState({});
  const [status, setStatus] = useState({});           // id -> status
  const [resolved, setResolved] = useState({});        // conflictId -> winnerId
  const [sourceTrust, setSourceTrust] = useState({});  // source -> trust (0..1)
  const [recallLive, setRecallLive] = useState(null);  // live /recall answer, or null (client-side fallback)
  const [pulse, setPulse] = useState(null);
  const [cascade, setCascade] = useState(null);   // latest resolve narration
  const [selected, setSelected] = useState(null);

  const [banner, setBanner] = useState(null);
  const [mockFallback, setMockFallback] = useState(false);
  const effLive = api.isLive && !mockFallback;

  const meta = DATASETS[dsKey];
  const nodeById = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);

  const reset = () => {
    setPhase("empty"); setNodes([]); setEdges([]); setConflicts([]); setMetrics(null);
    setPositions({}); setStatus({}); setResolved({}); setSourceTrust({}); setRecallLive(null); setPulse(null); setCascade(null); setSelected(null); setMode("case");
  };
  const pick = (k) => { if (k !== dsKey && !busy && !solving) { setDsKey(k); reset(); } };

  // Try live; if the backend is unreachable, banner + fall back to mock.
  async function withFallback(op) {
    if (!api.isLive || mockFallback) return op(true);
    try { return await op(false); }
    catch (e) {
      setBanner(`Couldn't reach the backend at ${api.apiBase} (${e.message}). Showing mock data — start the backend or Sai's tunnel, then hit “Retry live”.`);
      setMockFallback(true);
      return op(true);
    }
  }
  const retryLive = () => { setMockFallback(false); setBanner(null); reset(); };

  const ingest = async () => {
    setBusy(true);
    try { await withFallback((f) => api.ingest(dsKey, f)); setPhase("ingested"); }
    finally { setBusy(false); }
  };

  const applyState = (d, relayout = false) => {
    setNodes(d.nodes); setEdges(d.edges); setConflicts(d.conflicts); setMetrics(d.metrics);
    const st = {}; d.nodes.forEach((n) => { st[n.id] = n.status || "active"; }); setStatus(st);
    // The backend /resolve marks only the conflict you POST; it doesn't cascade
    // to related conflicts that share a now-retracted claim. Fill that gap here:
    // a conflict is cleared once its losing claim has been retracted.
    const rmap = {};
    (d.conflicts || []).forEach((c) => {
      if (c.resolved && c.winner) { rmap[c.id] = c.winner; return; }
      if (c.winner) {                                   // supersession: winner is known
        const loser = c.winner === c.a.id ? c.b.id : c.a.id;
        if (st[loser] === "retracted") rmap[c.id] = c.winner;
      } else {                                          // contradiction/semantic: infer from the retracted side
        const aR = st[c.a.id] === "retracted", bR = st[c.b.id] === "retracted";
        if (aR && bR) rmap[c.id] = c.a.id;              // both gone -> shown as MOOT
        else if (aR) rmap[c.id] = c.b.id;
        else if (bR) rmap[c.id] = c.a.id;
      }
    });
    setResolved(rmap);
    const tr = {}; d.nodes.forEach((n) => { if (n.source != null && n.source_trust != null) tr[n.source] = n.source_trust; }); setSourceTrust(tr);
    setRecallLive(d.recall || null);
    // Lay out only when explicitly asked (a fresh detection) or on first fill;
    // resolves keep positions stable so the board doesn't reshuffle.
    setPositions((prev) => (relayout || !Object.keys(prev).length) ? runLayout(d.nodes, d.edges) : prev);
  };

  const detect = async () => {
    setBusy(true);
    try { const d = await withFallback((f) => api.detect(dsKey, useLLM, f)); setSelected(null); applyState(d, true); setPhase("detected"); }
    finally { setBusy(false); }
  };

  const driftLoser = (loser) => setPositions((prev) => {
    const lp = prev[loser] || { x: W / 2, y: H / 2 };
    const dx = lp.x - W / 2, dy = lp.y - H / 2, d = Math.hypot(dx, dy) || 1;
    return { ...prev, [loser]: {
      x: clamp(lp.x + (dx / d) * 86, CW / 2 + 16, W - CW / 2 - 16),
      y: clamp(lp.y + (dy / d) * 86, CH / 2 + 16, H - CH / 2 - 16),
    } };
  });

  const doLocalResolve = (conflict, winner, loser) => {
    setStatus((prev) => ({ ...prev, [loser]: "retracted", [winner]: "active" }));
    setResolved((prev) => {
      const next = { ...prev, [conflict.id]: winner };
      conflicts.forEach((c) => {
        if (next[c.id]) return;
        if (c.a.id === loser || c.b.id === loser) { const w = c.a.id === loser ? c.b.id : c.a.id; next[c.id] = c.winner || w; }
      });
      return next;
    });
    const src = nodeById[loser]?.source;
    if (src) setSourceTrust((prev) => ({ ...prev, [src]: Math.max(0, (prev[src] ?? 1) - 0.34) }));
    driftLoser(loser);
  };

  const resolve = async (conflict, chosenWinner) => {
    const winner = chosenWinner || conflict.winner || conflict.a.id;
    const loser = winner === conflict.a.id ? conflict.b.id : conflict.a.id;
    setPulse(winner); setTimeout(() => setPulse((p) => (p === winner ? null : p)), 1200);

    // cascade narration: capture the loser's source + pre-resolution trust so the
    // improve()/forget() beat is correct in live mode too.
    const loserSrc = nodeById[loser]?.source;
    const trustMoves = conflict.type === "contradiction" || conflict.type === "semantic";
    const oldTrust = loserSrc != null ? (sourceTrust[loserSrc] ?? 1) : null;
    const at = positions[loser];

    const d = await withFallback((f) => api.resolve({ conflictId: conflict.id, winnerId: winner, loserId: loser, dataset: dsKey }, f));
    if (d) { applyState(d); driftLoser(loser); } else { doLocalResolve(conflict, winner, loser); }

    let drop = null;
    if (trustMoves && loserSrc != null) {
      const nt = d ? (d.nodes || []).find((n) => n.id === loser)?.source_trust : (oldTrust ?? 1) - 0.34;
      drop = nt != null && oldTrust != null ? Math.max(0, Math.round((oldTrust - nt) * 100)) : 34;
    }
    if (at) setCascade({ id: Date.now(), x: at.x, y: at.y, source: loserSrc, drop });

    if (selected === conflict.id) setSelected(null);
  };

  const solveCase = async () => {
    if (solving || busy || phase !== "detected") return;
    setSolving(true);
    const retracted = new Set(
      Object.entries(resolved).map(([cid, w]) => { const c = conflicts.find((x) => x.id === cid); return c ? (w === c.a.id ? c.b.id : c.a.id) : null; }).filter(Boolean)
    );
    const resolvedMap = { ...resolved };
    const steps = [];
    for (const c of conflicts) {
      if (resolvedMap[c.id]) continue;
      const winner = c.winner || c.a.id;
      const loser = winner === c.a.id ? c.b.id : c.a.id;
      if (retracted.has(loser)) { resolvedMap[c.id] = winner; continue; }
      steps.push({ c, winner }); retracted.add(loser); resolvedMap[c.id] = winner;
      conflicts.forEach((cc) => { if (!resolvedMap[cc.id] && (cc.a.id === loser || cc.b.id === loser)) { const w = cc.a.id === loser ? cc.b.id : cc.a.id; resolvedMap[cc.id] = w; } });
    }
    for (let i = 0; i < steps.length; i++) {
      await new Promise((r) => setTimeout(r, i === 0 ? 150 : 700));
      await resolve(steps[i].c, steps[i].winner);
    }
    setSolving(false);
  };

  // client-side recall (fallback + mock): active claims for the case's question
  const recall = useMemo(() => {
    const { subject, predicate } = meta.recall;
    return nodes.filter((n) => n.subject === subject && n.predicate === predicate && (status[n.id] || "active") === "active");
  }, [nodes, status, meta]);

  const allResolved = phase === "detected" && conflicts.length > 0 && Object.keys(resolved).length === conflicts.length;
  const solved = allResolved; // SOLVED = every flagged discrepancy has been cleared
  const statusWord = phase === "empty" ? "—" : phase === "ingested" ? "OPEN" : solved ? "SOLVED" : "OPEN";
  const pct = (x) => Math.round((x || 0) * 100);

  // answer cell: once SOLVED, show the reconciled answer; before that, show the
  // current belief — a temporal "leading" value, or "conflicting" when truly ambiguous.
  let ansClass = "muted", ansText = "";
  if (phase === "empty") ansText = "ingest to open the case";
  else if (phase === "ingested") ansText = "run detection…";
  else if (solved) {
    ansClass = "ok";
    ansText = recallLive?.answer || (recall.length === 1 ? recall[0].object : "resolved");
  } else {
    const conflicted = recallLive ? recallLive.conflicted : recall.length !== 1;
    const answer = recallLive ? recallLive.answer : (recall.length === 1 ? recall[0].object : null);
    const nCand = recallLive ? recallLive.candidates?.length : recall.length;
    if (conflicted || !answer) { ansClass = "bad"; ansText = (nCand > 1 ? nCand + " " : "") + "conflicting accounts"; }
    else { ansClass = "lead"; ansText = "leading: " + answer; }
  }

  return (
    <div className="coh">
      <header className="bar">
        <div className="brand">
          <span className="suit">♠</span>
          <div className="bwrap">
            <div className="logo">COHERENCE</div>
            <div className="sub">memory integrity · case board{effLive ? " · live" : ""}</div>
          </div>
        </div>

        <div className="controls">
          <div className="seg">
            {Object.keys(DATASETS).map((k) => (
              <button key={k} className={"segbtn" + (k === dsKey ? " on" : "")} onClick={() => pick(k)}>{k === "doug" ? "Case 01" : "Case 02"}</button>
            ))}
          </div>
          <button className="btn" onClick={ingest} disabled={busy || solving || phase !== "empty"}><Play size={13} />Ingest</button>
          <button className="btn go" onClick={detect} disabled={busy || solving || phase === "empty"}><Search size={13} />Run detection</button>
          {phase === "detected" && !solved && (
            <button className="btn solve" onClick={solveCase} disabled={solving || busy}><Gavel size={13} />Solve case</button>
          )}
          <button className={"toggle" + (useLLM ? " on" : "")} onClick={() => !busy && !solving && setUseLLM((v) => !v)}><Zap size={12} />LLM {useLLM ? "on" : "off"}</button>
          <button className={"btn tt" + (mode === "time" ? " on" : "")} onClick={() => phase === "detected" && setMode((m) => (m === "time" ? "case" : "time"))} disabled={phase !== "detected"} title="Replay what the memory believed over time"><History size={13} />{mode === "time" ? "Case board" : "Time-travel"}</button>
          <button className="btn ico" onClick={reset} title="New case"><RotateCcw size={13} /></button>
          {busy && <span className="spin" title="working" />}
        </div>

        {phase === "detected" && metrics && (
          <div className="stats">
            <b className={pct(metrics.precision) >= 100 ? "" : "w"}>{pct(metrics.precision)}%</b><span>prec</span>
            <b className={pct(metrics.recall) >= 100 ? "" : "w"}>{pct(metrics.recall)}%</b><span>rec</span>
            <b>{metrics.tp}<i>/{meta.truth}</i></b><span>flagged</span>
          </div>
        )}
      </header>

      {banner && (
        <div className="banner">
          <span>{banner}</span>
          <div className="bactions">
            <button onClick={retryLive}>Retry live</button>
            <button className="bx" onClick={() => setBanner(null)}>×</button>
          </div>
        </div>
      )}

      {mode === "case" ? (
        <>
          <LifecycleRail phase={phase} solved={solved} />
          <div className="cover">
            <div className="cno">CASE No. {meta.no}</div>
            <div className="ctitle">{meta.label}</div>
            <div className="cright">
              <span className="qq">{meta.recall.query}</span>
              <span key={statusWord} className={"stat " + statusWord.toLowerCase()}>{statusWord}</span>
              <span key={ansClass} className={"ans " + ansClass}>{ansText}</span>
            </div>
          </div>

          <div className="body">
            <CaseBoard
              meta={meta} phase={phase} nodes={nodes} edges={edges} conflicts={conflicts}
              status={status} resolved={resolved} positions={positions} pulse={pulse} cascade={cascade}
              selected={selected} onSelectConflict={setSelected}
            />
            <ConflictLog
              phase={phase} conflicts={conflicts} resolved={resolved} selected={selected}
              onSelect={setSelected} onResolve={resolve} nodeById={nodeById} sourceTrust={sourceTrust} status={status}
            />
          </div>
        </>
      ) : (
        <TimeMachine nodes={nodes} positions={positions} meta={meta} />
      )}

      <footer className="foot2">
        <span>{effLive ? `live · ${api.apiBase}` : "mock · bundled data"}</span>
        <span className="dim">POST /ingest → POST /detect → GET /graph · /conflicts · /recall → POST /resolve</span>
      </footer>
    </div>
  );
}