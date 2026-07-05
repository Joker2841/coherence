import { W, H, CW, CH, hash, fmtTime, stringPath, wrapLabel } from "./lib.js";

export default function CaseBoard({ meta, phase, nodes, edges, conflicts, status, resolved, positions, pulse, cascade, selected, onSelectConflict }) {
  const disputed = new Set();
  conflicts.forEach((c) => {
    if (!resolved[c.id] && (c.type === "contradiction" || c.type === "semantic")) { disputed.add(c.a.id); disputed.add(c.b.id); }
  });
  const winners = new Set(Object.values(resolved));
  const selConflict = conflicts.find((c) => c.id === selected);
  const isSelEdge = (e) => selConflict && ((selConflict.a.id === e.source && selConflict.b.id === e.target) || (selConflict.a.id === e.target && selConflict.b.id === e.source));

  const st = (id) => status[id] || "active";
  const drawOrder = [...nodes].sort((a, b) => {
    const pr = (n) => (st(n.id) === "retracted" ? 0 : st(n.id) === "superseded" ? 1 : disputed.has(n.id) ? 3 : 2);
    return pr(a) - pr(b);
  });
  const openConflictFor = (id) => conflicts.find((c) => !resolved[c.id] && (c.a.id === id || c.b.id === id));

  return (
    <div className="board">
      <svg viewBox={`0 0 ${W} ${H}`} className="svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="felt" cx="42%" cy="30%" r="90%">
            <stop offset="0%" stopColor="#123a2b" /><stop offset="55%" stopColor="#0d2a1f" /><stop offset="100%" stopColor="#071710" />
          </radialGradient>
          <pattern id="weave" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="7" stroke="rgba(255,255,255,.018)" strokeWidth="1" />
          </pattern>
          <marker id="tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,1 L9,5 L0,9" fill="none" stroke="var(--amber)" strokeWidth="1.6" />
          </marker>
          <filter id="slip" x="-40%" y="-40%" width="180%" height="210%">
            <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" floodColor="#000" floodOpacity=".4" />
            <feDropShadow dx="0" dy="7" stdDeviation="9" floodColor="#000" floodOpacity=".4" />
          </filter>
          <radialGradient id="gRed"><stop offset="0%" stopColor="var(--red)" stopOpacity=".5" /><stop offset="72%" stopColor="var(--red)" stopOpacity="0" /></radialGradient>
          <radialGradient id="gGreen"><stop offset="0%" stopColor="var(--seal)" stopOpacity=".62" /><stop offset="72%" stopColor="var(--seal)" stopOpacity="0" /></radialGradient>
        </defs>

        <rect x="0" y="0" width={W} height={H} fill="url(#felt)" />
        <rect x="0" y="0" width={W} height={H} fill="url(#weave)" />
        <rect x="10" y="10" width={W - 20} height={H - 20} rx="10" fill="none" stroke="rgba(203,166,92,.22)" strokeWidth="1.5" />

        {phase === "detected" && edges.map((e) => {
          const pa = positions[e.source], pb = positions[e.target];
          if (!pa || !pb) return null;
          const gone = st(e.source) === "retracted" || st(e.target) === "retracted";
          const sp = stringPath(pa, pb); const sup = e.type === "supersedes"; const sel = isSelEdge(e);
          return (
            <g key={e.id} className={"str" + (gone ? " gone" : "")}>
              <path d={sp.d} className={"twine" + (sup ? " sup" : " con") + (sel ? " sel" : "")} fill="none" markerEnd={sup ? "url(#tip)" : undefined} />
              {!sup && (<>
                <circle cx={sp.x1} cy={sp.y1} r="3.4" className="pin" />
                <circle cx={sp.x2} cy={sp.y2} r="3.4" className="pin" />
              </>)}
            </g>
          );
        })}

        {phase === "detected" && nodes.map((n) => {
          const p = positions[n.id]; if (!p || st(n.id) === "retracted") return null;
          const red = disputed.has(n.id), teal = pulse === n.id;
          if (!red && !teal) return null;
          return <ellipse key={"g" + n.id} className={"glow" + (teal ? " teal" : " red")} cx={p.x} cy={p.y} rx="118" ry="82" fill={teal ? "url(#gGreen)" : "url(#gRed)"} />;
        })}

        {drawOrder.map((n) => {
          const p = positions[n.id]; if (!p) return null;
          const s = st(n.id);
          const red = disputed.has(n.id);
          const verified = phase === "detected" && s === "active" && !red && winners.has(n.id);
          const rot = ((hash(n.id) % 100) / 100 - 0.5) * 5.2;
          const stripe = red ? "var(--red)" : s === "superseded" ? "var(--amber)" : verified ? "var(--seal)" : "rgba(0,0,0,.14)";
          const cls = ["slip", s, red ? "disp" : "", verified ? "ver" : ""].join(" ");
          const dealIdx = nodes.findIndex((x) => x.id === n.id);
          return (
            <g key={n.id} className="pos" style={{ transform: `translate(${p.x}px,${p.y}px)` }}
               onClick={() => { const c = openConflictFor(n.id); if (c) onSelectConflict(c.id); }}>
              <g className={cls} transform={`rotate(${rot})`} style={{ animationDelay: `${dealIdx * 70}ms` }}>
                <rect className="paper" x={-CW / 2} y={-CH / 2} width={CW} height={CH} rx="5" filter="url(#slip)" />
                <rect x={-CW / 2 + 6} y={-CH / 2 + 5} width={CW - 12} height="4" rx="2" fill={stripe} className="stripe" />
                <text className="eye" x={-CW / 2 + 14} y={-CH / 2 + 24}>{n.subject}.{n.predicate}</text>
                {(() => { const L = wrapLabel(n.object); return L.length === 1
                  ? <text className="head" x={-CW / 2 + 14} y={2}>{L[0]}</text>
                  : <text className="head" x={-CW / 2 + 14} y={-6}>{L[0]}<tspan x={-CW / 2 + 14} dy="17">{L[1]}</tspan></text>; })()}
                <text className="foot" x={-CW / 2 + 14} y={CH / 2 - 13}>{n.source} · {fmtTime(n.time)}</text>
                {s === "superseded" && <text className="wm" x="0" y="6" textAnchor="middle">SUPERSEDED</text>}
                {s === "retracted" && (
                  <g className="stamp" transform="rotate(-13)">
                    <rect x="-58" y="-17" width="116" height="34" rx="4" fill="none" stroke="var(--red)" strokeWidth="2.4" />
                    <text x="0" y="7" textAnchor="middle">RETRACTED</text>
                  </g>
                )}
                {verified && (
                  <g className="seal" transform={`translate(${CW / 2 - 20},${-CH / 2 + 18}) rotate(-9)`}>
                    <circle r="17" fill="none" stroke="var(--seal)" strokeWidth="2" />
                    <text y="4" textAnchor="middle">✓</text>
                  </g>
                )}
              </g>
            </g>
          );
        })}

        {cascade && (() => {
          const beats = [
            { k: "c1", txt: `RETRACTED${cascade.source ? ` — ${cascade.source}` : ""}` },
            cascade.drop != null ? { k: "c2", txt: `trust ↓${cascade.drop}% · ${cascade.source}` } : null,
            { k: "c3", txt: "✓ cleared" },
          ].filter(Boolean);
          return (
            <g key={cascade.id} className="casc-g" style={{ transform: `translate(${cascade.x}px,${cascade.y}px)` }}>
              {beats.map((b, i) => (
                <text key={b.k} className={"casc " + b.k} x="0" y={-CH / 2 - 12} textAnchor="middle"
                      style={{ animationDelay: `${i * 0.9}s` }}>{b.txt}</text>
              ))}
            </g>
          );
        })()}
      </svg>

      {phase === "empty" && (
        <div className="overlay">
          <div className="ovc">
            <div className="ovtag">CASE No. {meta.no}</div>
            <div className="ovt">{meta.label}</div>
            <div className="ovb">{meta.blurb}</div>
            <div className="ovh">Deal the evidence — <b>Ingest</b>, then <b>Run detection</b>.</div>
          </div>
        </div>
      )}
      {phase === "ingested" && (
        <div className="overlay">
          <div className="ovc">
            <div className="ovtag">CASE No. {meta.no}</div>
            <div className="ovt">{meta.label}</div>
            <div className="ovb">Statements ingested into the graph.</div>
            <div className="ovh"><b>Run detection</b> to flag the contradictions.</div>
          </div>
        </div>
      )}

      <div className="legend">
        <span><i className="k red" />contradiction</span>
        <span><i className="k amb" />superseded</span>
        <span><i className="k seal" />verified</span>
        <span><i className="k vio" />LLM-detected</span>
      </div>
    </div>
  );
}
