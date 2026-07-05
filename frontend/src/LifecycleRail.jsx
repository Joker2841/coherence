import { Fingerprint, ScanSearch, Wand2, MessageSquare } from "lucide-react";

// The always-on Cognee lifecycle HUD: remember -> detect -> improve -> recall.
// Every on-screen action maps to one of these four operations, so a first-time
// viewer can see *which* memory step is firing at any moment.
const STAGES = [
  { key: "remember", Icon: Fingerprint,   label: "Remember", op: "cognee.add",       hint: "statements enter the graph" },
  { key: "detect",   Icon: ScanSearch,    label: "Detect",   op: "memify",           hint: "contradictions flagged" },
  { key: "improve",  Icon: Wand2,         label: "Improve",  op: "improve · forget", hint: "loser retracted, trust reweighted" },
  { key: "recall",   Icon: MessageSquare, label: "Recall",   op: "cognee.search",    hint: "one coherent answer" },
];
const ORDER = STAGES.map((s) => s.key);

// Derive each stage's state (pending | active | done) from the app's own phase.
// One stage is "active" at a time — that's the beat the audience should watch.
function stageStates(phase, solved) {
  if (phase === "empty")    return { remember: "active", detect: "pending", improve: "pending", recall: "pending" };
  if (phase === "ingested") return { remember: "done",   detect: "active",  improve: "pending", recall: "pending" };
  if (!solved)              return { remember: "done",   detect: "done",    improve: "active",  recall: "pending" };
  return                           { remember: "done",   detect: "done",    improve: "done",    recall: "done" };
}

export default function LifecycleRail({ phase, solved }) {
  const st = stageStates(phase, solved);
  const activeIdx = ORDER.findIndex((k) => st[k] === "active");
  const doneCount = ORDER.filter((k) => st[k] === "done").length;
  const fillIdx = activeIdx === -1 ? doneCount - 1 : activeIdx;      // fill up to the current stage
  const pct = Math.max(0, Math.min(1, fillIdx / (ORDER.length - 1)));

  return (
    <div className="rail" role="list" aria-label="Cognee memory lifecycle">
      <div className="rail-inner">
        <div className="rail-track">
          <div className="rail-fill" style={{ width: `${pct * 100}%` }} />
        </div>
        {STAGES.map(({ key, Icon, label, op, hint }) => (
          <div key={key} className={"rail-stage " + st[key]} role="listitem" title={hint}>
            <div className="rail-node"><Icon size={14} strokeWidth={2} /></div>
            <div className="rail-label">{label}</div>
            <div className="rail-op">{op}</div>
          </div>
        ))}
      </div>
    </div>
  );
}