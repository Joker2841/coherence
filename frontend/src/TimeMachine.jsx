import { useState, useEffect, useMemo } from "react";
import { Play, Pause } from "lucide-react";
import { W, H, CW, CH, hash, stringPath, wrapLabel } from "./lib.js";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const parse = (s) => new Date(s).getTime();
function fmtFull(ms) {
  const d = new Date(ms);
  let h = d.getHours(); const ap = h >= 12 ? "PM" : "AM"; h = h % 12 || 12;
  return `${MONTHS[d.getMonth()]} ${d.getDate()} · ${h}:${String(d.getMinutes()).padStart(2, "0")} ${ap}`;
}
const shortT = (ms) => { const d = new Date(ms); let h = d.getHours(); const ap = h >= 12 ? "p" : "a"; h = h % 12 || 12; return `${MONTHS[d.getMonth()]} ${d.getDate()} ${h}${ap}`; };

export default function TimeMachine({ nodes, positions, meta }) {
  const times = useMemo(() => nodes.map((n) => parse(n.time)).filter((t) => !isNaN(t)), [nodes]);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 1;
  const span = tMax - tMin || 1;
  const [time, setTime] = useState(tMax);
  const [playing, setPlaying] = useState(false);

  useEffect(() => { setTime(tMax); setPlaying(false); }, [tMax, tMin]);

  // auto-play sweep from start to end (~7s)
  useEffect(() => {
    if (!playing) return;
    let raf;
    const startWall = performance.now();
    const startVal = time >= tMax ? tMin : time;
    const dist = tMax - startVal || 1;
    const step = (now) => {
      const p = Math.min(1, (now - startWall) / 7000);
      setTime(startVal + dist * p);
      if (p < 1) raf = requestAnimationFrame(step); else setPlaying(false);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  // belief for the case's question at `time`
  const belief = useMemo(() => {
    const { subject, predicate } = meta.recall;
    const known = nodes.filter((n) => n.subject === subject && n.predicate === predicate && parse(n.time) <= time);
    if (!known.length) return { state: "none" };
    const maxT = Math.max(...known.map((n) => parse(n.time)));
    const cur = known.filter((n) => parse(n.time) === maxT);
    return cur.length > 1 ? { state: "conflict", claims: cur } : { state: "confident", claim: cur[0] };
  }, [nodes, time, meta]);

  // per-node timeline status + current conflict pairs
  const { statusById, pairs } = useMemo(() => {
    const st = {}; const pairs = []; const groups = {};
    nodes.forEach((n) => { const k = n.subject + "." + n.predicate; if (!groups[k]) groups[k] = []; groups[k].push(n); });
    Object.values(groups).forEach((g) => {
      const known = g.filter((n) => parse(n.time) <= time);
      if (!known.length) { g.forEach((n) => (st[n.id] = "future")); return; }
      const maxT = Math.max(...known.map((n) => parse(n.time)));
      const cur = known.filter((n) => parse(n.time) === maxT);
      g.forEach((n) => {
        if (parse(n.time) > time) st[n.id] = "future";
        else if (parse(n.time) === maxT) st[n.id] = cur.length > 1 ? "conflict" : "current";
        else st[n.id] = "past";
      });
      for (let i = 0; i < cur.length; i++) for (let j = i + 1; j < cur.length; j++) pairs.push([cur[i].id, cur[j].id]);
    });
    return { statusById: st, pairs };
  }, [nodes, time]);

  const distinctTimes = useMemo(() => [...new Set(times)].sort((a, b) => a - b), [times]);
  const pctOf = (t) => ((t - tMin) / span) * 100;

  const beliefText = belief.state === "none" ? "no record yet"
    : belief.state === "conflict" ? belief.claims.map((c) => c.object).join("  vs  ")
    : belief.claim.object;
  const beliefClass = belief.state === "conflict" ? "conflict" : belief.state === "confident" ? "ok" : "none";

  return (
    <div className="tm">
      <div className="tm-belief">
        <span className="tm-q">{meta.recall.query}</span>
        <span className="tm-clock">{fmtFull(time)}</span>
        <span className={"tm-ans " + beliefClass}>
          {belief.state === "conflict" && <em>conflicted — </em>}{beliefText}
        </span>
      </div>

      <div className="tm-board">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="tfelt" cx="42%" cy="30%" r="90%">
              <stop offset="0%" stopColor="#123a2b" /><stop offset="55%" stopColor="#0d2a1f" /><stop offset="100%" stopColor="#071710" />
            </radialGradient>
            <filter id="tshadow" x="-30%" y="-30%" width="160%" height="180%">
              <feDropShadow dx="0" dy="4" stdDeviation="5" floodColor="#000" floodOpacity=".4" />
            </filter>
            <radialGradient id="tRed"><stop offset="0%" stopColor="var(--red)" stopOpacity=".5" /><stop offset="72%" stopColor="var(--red)" stopOpacity="0" /></radialGradient>
            <radialGradient id="tGrn"><stop offset="0%" stopColor="var(--seal)" stopOpacity=".38" /><stop offset="72%" stopColor="var(--seal)" stopOpacity="0" /></radialGradient>
          </defs>
          <rect x="0" y="0" width={W} height={H} fill="url(#tfelt)" />
          <rect x="10" y="10" width={W - 20} height={H - 20} rx="10" fill="none" stroke="rgba(203,166,92,.22)" strokeWidth="1.5" />

          {pairs.map(([a, b], i) => {
            const pa = positions[a], pb = positions[b]; if (!pa || !pb) return null;
            return <path key={i} d={stringPath(pa, pb).d} className="tm-edge" fill="none" />;
          })}

          {nodes.map((n) => {
            const p = positions[n.id]; if (!p) return null;
            const s = statusById[n.id];
            if (s !== "conflict" && s !== "current") return null;
            return <ellipse key={"g" + n.id} cx={p.x} cy={p.y} rx="110" ry="78" fill={s === "conflict" ? "url(#tRed)" : "url(#tGrn)"} className={s === "conflict" ? "tm-glow red" : "tm-glow"} />;
          })}

          {nodes.map((n) => {
            const p = positions[n.id]; if (!p) return null;
            const s = statusById[n.id] || "future";
            const rot = ((hash(n.id) % 100) / 100 - 0.5) * 5.2;
            const stripe = s === "conflict" ? "var(--red)" : s === "current" ? "var(--seal)" : s === "past" ? "var(--amber)" : "rgba(0,0,0,.14)";
            return (
              <g key={n.id} style={{ transform: `translate(${p.x}px,${p.y}px)` }}>
                <g className={"tslip " + s} transform={`rotate(${rot})`}>
                  <rect className="paper" x={-CW / 2} y={-CH / 2} width={CW} height={CH} rx="5" filter="url(#tshadow)" />
                  <rect x={-CW / 2 + 6} y={-CH / 2 + 5} width={CW - 12} height="4" rx="2" fill={stripe} />
                  <text className="eye" x={-CW / 2 + 14} y={-CH / 2 + 24}>{n.subject}.{n.predicate}</text>
                  {(() => { const L = wrapLabel(n.object); return L.length === 1
                    ? <text className="head" x={-CW / 2 + 14} y={2}>{L[0]}</text>
                    : <text className="head" x={-CW / 2 + 14} y={-6}>{L[0]}<tspan x={-CW / 2 + 14} dy="17">{L[1]}</tspan></text>; })()}
                  <text className="foot" x={-CW / 2 + 14} y={CH / 2 - 13}>{n.source}</text>
                </g>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="tm-scrub">
        <button className="tm-play" onClick={() => setPlaying((v) => !v)} title={playing ? "Pause" : "Play"}>
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <div className="tm-track">
          <input type="range" min={tMin} max={tMax} step={Math.max(1, Math.round(span / 500))} value={time}
            onChange={(e) => { setPlaying(false); setTime(Number(e.target.value)); }} />
          <div className="tm-ticks">
            {distinctTimes.map((t) => (
              <span key={t} className="tm-tick" style={{ left: pctOf(t) + "%" }}><i /><b>{shortT(t)}</b></span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}