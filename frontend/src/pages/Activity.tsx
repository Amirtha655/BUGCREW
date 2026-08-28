import { useState } from "react";
import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, Empty, PageHeader } from "../components/ui";
import type { ActivityKind } from "../types";
import { fmtTime } from "../utils/format";
import { ASSET_NAME } from "../utils/vocab";

const KINDS: { key: ActivityKind; label: string; tone: string; help: string }[] = [
  { key: "MARKET", label: "Market", tone: "violet", help: "Something changed in the market" },
  { key: "AGENT", label: "Agent", tone: "blue", help: "A specialist agent proposed something" },
  { key: "RISK", label: "Safety", tone: "amber", help: "The safety check ran" },
  { key: "CAPITAL", label: "Capital", tone: "blue", help: "Money was assigned to a trade" },
  { key: "EXECUTION", label: "Execution", tone: "green", help: "A trade was placed" },
  { key: "OUTCOME", label: "Outcome", tone: "gray", help: "A finished trade was graded" },
  { key: "ADAPTATION", label: "Adaptation", tone: "amber", help: "The system changed its own settings" },
];

const TONE: Record<string, string> = Object.fromEntries(KINDS.map((k) => [k.key, k.tone]));

export default function Activity() {
  const { activity } = useSystem();
  const [active, setActive] = useState<Set<ActivityKind>>(new Set());
  const [query, setQuery] = useState("");

  const toggle = (k: ActivityKind) => {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k); else next.add(k);
      return next;
    });
  };

  const filtered = activity
    .filter((e) => (active.size === 0 ? true : active.has(e.kind)))
    .filter((e) => {
      if (!query) return true;
      const q = query.toLowerCase();
      return e.message.toLowerCase().includes(q) || (e.asset ?? "").toLowerCase().includes(q);
    })
    .slice()
    .reverse();

  return (
    <div className="page">
      <PageHeader
        title="Activity Log"
        description="A running record of everything the system observed, decided and did, in the order it happened."
      />

      <Panel
        title="System events"
        sub={`${filtered.length} shown`}
        actions={
          <>
            <input
              type="search"
              placeholder="Search events…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: 170 }}
            />
            {active.size > 0 && (
              <button className="sm" onClick={() => setActive(new Set())}>Clear filters</button>
            )}
          </>
        }
      >
        <div className="row wrap" style={{ gap: 5, marginBottom: 12 }}>
          {KINDS.map((k) => (
            <button
              key={k.key}
              className={`sm${active.has(k.key) ? " on" : ""}`}
              title={k.help}
              onClick={() => toggle(k.key)}
              style={active.has(k.key) ? { background: "var(--surface-3)", fontWeight: 600 } : undefined}
            >
              {k.label}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <Empty title={activity.length === 0 ? "No activity recorded yet" : "No events match this filter"}>
            {activity.length === 0
              ? "Start the simulation and every step the system takes will be logged here."
              : "Try clearing the filters or the search box."}
          </Empty>
        ) : (
          <div className="log">
            {filtered.map((e) => (
              <div className="log-row" key={e.id}>
                <span className="t">{fmtTime(e.timestamp)}</span>
                <span className="kind-cell">
                  <Badge tone={TONE[e.kind] ?? "gray"}>{KINDS.find((k) => k.key === e.kind)?.label ?? e.kind}</Badge>
                </span>
                <span className="msg">
                  {e.message}
                  {e.asset && (
                    <span className="faint" style={{ fontSize: 11, marginLeft: 6 }}>
                      · {ASSET_NAME[e.asset] ?? e.asset} · step {e.cycle}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
