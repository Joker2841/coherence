import { fmtTime } from "./lib.js";

const METHOD = {
  supersession: "Same subject + predicate, newer timestamp wins — deterministic temporal rule, no LLM.",
  contradiction: "Same subject, predicate and time but different values — deterministic rule, no LLM.",
  semantic: "Different predicates that can't both hold — vector-gated, then confirmed by the LLM judge.",
};

export default function ConflictLog({ phase, conflicts, resolved, selected, onSelect, onResolve, nodeById, sourceTrust }) {
  const trust = (s) => sourceTrust[s];

  return (
    <aside className="log">
      <div className="lh">
        <span>Discrepancy log</span>
        {phase === "detected" && <span className="lc">{Object.keys(resolved).length}/{conflicts.length} cleared</span>}
      </div>

      {phase !== "detected" && <div className="lempty">Run detection to flag discrepancies.</div>}

      {phase === "detected" && conflicts.map((c) => {
        const done = !!resolved[c.id];
        const sel = selected === c.id;
        const na = nodeById[c.a.id], nb = nodeById[c.b.id];
        return (
          <div key={c.id} className={"entry " + c.type + (done ? " done" : "") + (sel ? " sel" : "")} onClick={() => onSelect(sel ? null : c.id)}>
            <div className="etop">
              <span className={"badge " + c.type}>{c.type}</span>
              <span className={"badge by " + c.by}>{c.by === "llm" ? "AI judge" : "rule"}</span>
              <span className="cf">{Math.round((c.conf ?? 0) * 100)}%</span>
            </div>
            <div className="ev">{c.verdict}</div>
            <div className="acc">
              <span className={"slipchip" + (done && resolved[c.id] !== c.a.id ? " out" : done ? " keep" : "")}>{c.a.object}<em> {c.a.source}</em></span>
              <span className="x">×</span>
              <span className={"slipchip" + (done && resolved[c.id] !== c.b.id ? " out" : done ? " keep" : "")}>{c.b.object}<em> {c.b.source}</em></span>
            </div>

            {sel && (
              <div className="audit">
                <div className="aq">WHY FLAGGED</div>
                <div className="aclaim">
                  <span className="who">{c.a.source}{trust(c.a.source) != null && trust(c.a.source) < 1 && <b className="trust"> reliability {trust(c.a.source).toFixed(2)}</b>}</span>
                  <span className="atime">{fmtTime(na?.time)}</span>
                </div>
                <div className="atext">“{na?.text || c.a.object}”</div>
                <div className="aclaim">
                  <span className="who">{c.b.source}{trust(c.b.source) != null && trust(c.b.source) < 1 && <b className="trust"> reliability {trust(c.b.source).toFixed(2)}</b>}</span>
                  <span className="atime">{fmtTime(nb?.time)}</span>
                </div>
                <div className="atext">“{nb?.text || c.b.object}”</div>
                <div className="amethod">{METHOD[c.type]}</div>
              </div>
            )}

            {!done ? (
              c.type === "supersession" ? (
                <button className="act full" onClick={(e) => { e.stopPropagation(); onResolve(c); }}>
                  Retract stale · keep <b>{nodeById[c.winner]?.object || "newest"}</b>
                </button>
              ) : (
                <div className="actrow">
                  <button className="act" onClick={(e) => { e.stopPropagation(); onResolve(c, c.a.id); }}>Trust {c.a.source}</button>
                  <button className="act" onClick={(e) => { e.stopPropagation(); onResolve(c, c.b.id); }}>Trust {c.b.source}</button>
                </div>
              )
            ) : (
              <div className="cleared">CLEARED · kept <b>{nodeById[resolved[c.id]]?.object || "survivor"}</b>, loser forgotten</div>
            )}
          </div>
        );
      })}
    </aside>
  );
}
