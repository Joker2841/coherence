import * as d3 from "d3";

// Board coordinate space (SVG viewBox). Cards are placed in these units.
export const W = 960, H = 604, CW = 176, CH = 92;

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const hash = (s) => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; };

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
export function fmtTime(s) {
  if (!s) return "";
  const m = String(s).match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return String(s);
  const [, , Mo, D, H_, Mi] = m;
  let h = +H_; const ap = h >= 12 ? "PM" : "AM"; h = h % 12 || 12;
  return `${MONTHS[+Mo - 1]} ${+D} · ${h}:${Mi}${ap}`;
}

// Synchronous force layout: returns { id: {x, y} }. Small, curated graphs only.
export function runLayout(nodes, links) {
  const arr = nodes.map((n, i) => {
    const ang = (i / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2;
    return { ...n, x: W / 2 + Math.cos(ang) * 250, y: H / 2 + Math.sin(ang) * 160 };
  });
  const ln = (links || []).map((l) => ({ source: l.source, target: l.target }));
  const sim = d3.forceSimulation(arr)
    .force("charge", d3.forceManyBody().strength(-1250))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collide", d3.forceCollide().radius(102))
    .force("x", d3.forceX(W / 2).strength(0.05))
    .force("y", d3.forceY(H / 2).strength(0.08))
    .stop();
  if (ln.length) sim.force("link", d3.forceLink(ln).id((d) => d.id).distance(230).strength(0.3));
  for (let i = 0; i < 440; i++) sim.tick();
  const pos = {};
  arr.forEach((n) => { pos[n.id] = { x: clamp(n.x, CW / 2 + 16, W - CW / 2 - 16), y: clamp(n.y, CH / 2 + 16, H - CH / 2 - 16) }; });
  return pos;
}

// Quadratic string path with a gentle downward sag, plus its trimmed endpoints.
export function stringPath(pa, pb) {
  const dx = pb.x - pa.x, dy = pb.y - pa.y, d = Math.hypot(dx, dy) || 1;
  const ux = dx / d, uy = dy / d, off = 58;
  const x1 = pa.x + ux * off, y1 = pa.y + uy * off, x2 = pb.x - ux * off, y2 = pb.y - uy * off;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2 + Math.min(28, d * 0.1);
  return { d: `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`, x1, y1, x2, y2 };
}
