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

export default function TimeMachine({ nodes, positions, meta }) {
  // Advance by discrete memory events (distinct timestamps), not clock-time —
  // evenly spaced, so every state holds and every transition is visible.
  const events = useMemo(
    () => [...new Set(nodes.map((n) => parse(n.time)).filter((t) => !isNaN(t)))].sort((a, b) => a - b),
    [nodes]
  );
  const N = events.length;
  const [idx, setIdx] = useState(Math.max(0, N - 1));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);            // 0.5 | 1 | 2
  const dwell = 1400 / speed;

  useEffect(() => { setIdx(Math.max(0, N - 1)); setPlaying(false); }, [N]);

  // step-and-hold playback: hold each event for `dwell`, then advance
  useEffect(() => {
    if (!playing) return;
    if (idx >= N - 1) { setPlaying(false); return; }
    const t = setTimeout(() => setIdx((i) => Math.min(N - 1, i + 1)), dwell);
    return () => clearTimeout(t);
  }, [playing, idx, dwell, N]);

  const time = events[idx] ?? 0;

  // belief for the case's question at this moment
  const belief = useMemo(() => {
    const { subject, predicate } = meta.recall;
    const known = nodes.filter((n) => n.subject === subject && n.predicate === predicate && parse(n.time) <= time);
    if (!known.length) return { state: "none" };
    const maxT = Math.max(...known.map((n) => parse(n.time)));
    const cur = known.filter((n) => parse(n.time) === maxT);
    return cur.length > 1 ? { state: "conflict", claims: cur } : { state: "confident", claim: cur[0] };
  }, [nodes, time, meta]);

  // per-node status + current same-time conflict pairs
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

  const arriving = useMemo(() => nodes.filter((n) => parse(n.time) === time), [nodes, time]);

  // tick labels: show the date only when it changes, else just the time
  const labels = useMemo(() => events.map((t, i) => {
    const d = new Date(t); let h = d.getHours(); const ap = h >= 12 ? "p" : "a"; h = h % 12 || 12;
    const sameDay = i > 0 && new Date(events[i - 1]).toDateString() === d.toDateString();
    return sameDay ? `${h}${ap}` : `${MONTHS[d.getMonth()]} ${d.getDate()} ${h}${ap}`;
  }), [events]);
  const pctOf = (i) => (N > 1 ? (i / (N - 1)) * 100 : 50);

  const beliefText = belief.state === "none" ? "no record yet"
    : belief.state === "conflict" ? belief.claims.map((c) => c.object).join("  vs  ")
    : belief.claim.object;
  const beliefClass = belief.state === "conflict" ? "conflict" : belief.state === "confident" ? "ok" : "none";

  const play = () => { if (playing) { setPlaying(false); return; } if (idx >= N - 1) setIdx(0); setPlaying(true); };

  return (
    <div className="tm">
      <div className="tm-belief">
        <span className="tm-q">{meta.recall.query}</span>
        <span className="tm-clock">{fmtFull(time)}</span>
        <span className={"tm-ans " + beliefClass}>
          {belief.state === "conflict" && <em>conflicted — </em>}{beliefText}
        </span>
      </div>
      <div className="tm-arrive">
        <span className="tm-arrow">▸</span> recorded now:&nbsp;
        {arriving.length ? arriving.map((a, i) => (
          <span key={a.id}>{i > 0 && <span className="tm-dot">·</span>}<b>{a.source}</b> {a.object}</span>
        )) : <span className="tm-none">—</span>}
      </div>

      <div className="tm-board">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="tfelt" cx="42%" cy="30%" r="90%">
              <stop offset="0%" stopColor="#123a2b" /><stop offset="55%" stopColor="#0d2a1f" /><stop offset="100%" stopColor="#071710" />
            </radialGradient>
            <filter id="tshadow" x="-40%" y="-40%" width="180%" height="210%">
              <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" floodColor="#000" floodOpacity=".4" />
              <feDropShadow dx="0" dy="7" stdDeviation="9" floodColor="#000" floodOpacity=".4" />
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
        <div className="tm-speedbar">
          <span className="tm-speedlbl">speed</span>
          <div className="tm-speed">
            {[0.5, 1, 2].map((s) => (
              <button key={s} className={"spd" + (speed === s ? " on" : "")} onClick={() => setSpeed(s)}>{s}×</button>
            ))}
          </div>
        </div>
        <div className="tm-scrub-row">
          <button className="tm-play" onClick={play} title={playing ? "Pause" : "Play"}>
            {playing ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <div className="tm-track">
            <input type="range" min={0} max={Math.max(0, N - 1)} step={1} value={idx}
              onChange={(e) => { setPlaying(false); setIdx(Number(e.target.value)); }} />
            <div className="tm-ticks">
              {events.map((t, i) => (
                <span key={t} className={"tm-tick" + (i === idx ? " on" : "")} style={{ left: pctOf(i) + "%" }}><i /><b>{labels[i]}</b></span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
