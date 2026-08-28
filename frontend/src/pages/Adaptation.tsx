import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, Empty, PageHeader, DataTable, StatRow, StatTile, Meter, InfoLabel } from "../components/ui";
import type { Column } from "../components/ui";
import type { StrategyLeaderboardRow } from "../types";
import { fmtCurrency, fmtPctPlain, fmtTime } from "../utils/format";
import { T, regimeInfo, strategyLabel, humanize } from "../utils/vocab";

function parseTriple(v: string): [number, number, number] {
  const p = v.split(",").map((x) => parseFloat(x.trim()));
  return [p[0] ?? 1, p[1] ?? 1, p[2] ?? 1];
}

export default function Adaptation() {
  const { latest, adaptations } = useSystem();

  const currentRegime = latest?.overall_regime ?? "NORMAL";
  const state = latest?.adaptive_states?.[currentRegime];
  const regime = regimeInfo(currentRegime);
  const board = latest?.strategy_leaderboard ?? [];
  const mostRecent = adaptations[0];

  const columns: Column<StrategyLeaderboardRow>[] = [
    { key: "strategy", header: "Approach", sortable: true, sortValue: (r) => r.strategy_tag,
      render: (r) => <span>{strategyLabel(r.strategy_tag)}</span> },
    { key: "regime", header: "Market condition", sortable: true, sortValue: (r) => r.regime,
      render: (r) => <Badge tone={regimeInfo(r.regime).tone}>{regimeInfo(r.regime).label}</Badge> },
    { key: "trades", header: "Completed trades", align: "right", sortable: true, sortValue: (r) => r.total_trades,
      render: (r) => <span className="num">{r.total_trades}</span> },
    { key: "rate", header: <InfoLabel term={T.successRate} />, align: "right", sortable: true, sortValue: (r) => r.success_rate,
      render: (r) => (
        <span className={`num ${r.success_rate >= 0.5 ? "pos" : "neg"}`}>{fmtPctPlain(r.success_rate * 100, 0)}</span>
      ) },
    { key: "pnl", header: "Total result", align: "right", sortable: true, sortValue: (r) => r.total_pnl,
      render: (r) => (
        <span className={`num ${r.total_pnl >= 0 ? "pos" : "neg"}`}>
          {r.total_pnl >= 0 ? "+" : ""}{fmtCurrency(r.total_pnl, 2)}
        </span>
      ) },
  ];

  return (
    <div className="page">
      <PageHeader
        title="Adaptation"
        description="The system does not keep running the same strategy regardless of results. It reviews how its recent trades actually performed and adjusts its own behaviour — becoming more cautious after losses, and easing back once results recover."
      />

      {mostRecent ? (
        <Panel title="Most recent change the system made to itself" sub={fmtTime(mostRecent.timestamp)}>
          <div className="ba">
            <div className="ba-card">
              <div className="ba-label">Before</div>
              <div className="ba-value">
                {(() => { const [c, s] = parseTriple(mostRecent.old_value); return `${c.toFixed(2)}× / ${s.toFixed(2)}×`; })()}
              </div>
              <div className="ba-note">Confidence and trade-size settings before the change.</div>
            </div>
            <div className="ba-arrow">→</div>
            <div className="ba-card">
              <div className="ba-label">After</div>
              <div className="ba-value">
                {(() => { const [c, s] = parseTriple(mostRecent.new_value); return `${c.toFixed(2)}× / ${s.toFixed(2)}×`; })()}
              </div>
              <div className="ba-note">Applied to every decision made from the next cycle onward.</div>
            </div>
          </div>
          <div style={{ height: 12 }} />
          <div className="callout">
            <div className="callout-label">Why it changed</div>
            {humanize(mostRecent.reasoning)}
          </div>
          <div className="kv" style={{ marginTop: 8 }}>
            <span className="k">What triggered the review</span>
            <span className="v">{humanize(mostRecent.trigger)}</span>
          </div>
        </Panel>
      ) : (
        <Panel title="System adjustments">
          <Empty title="No adjustments made yet">
            The system needs at least three completed trades in the same market condition before it
            will change its own settings. Run the "Strategy Underperformance" scenario to see this happen.
          </Empty>
        </Panel>
      )}

      {state && (
        <Panel
          title="Current settings"
          sub={`Applied while conditions are "${regime.label}"`}
          actions={<Badge tone={regime.tone}>{regime.label}</Badge>}
        >
          <StatRow cols={3}>
            <StatTile term={T.confidenceMultiplier} value={`${state.confidence_multiplier.toFixed(2)}×`}
              note={state.confidence_multiplier < 1 ? "Reduced after poor results" : "At full strength"} />
            <StatTile term={T.sizeMultiplier} value={`${state.size_multiplier.toFixed(2)}×`}
              note={state.size_multiplier < 1 ? "Trades are being made smaller" : "Normal trade sizes"} />
            <StatTile term={T.riskFactor} value={`${state.risk_tightening_factor.toFixed(2)}×`}
              note={state.risk_tightening_factor < 1 ? "Safety limits tightened" : "Standard safety limits"} />
          </StatRow>

          <div style={{ height: 14 }} />
          {[
            { label: "Confidence setting", v: state.confidence_multiplier },
            { label: "Trade size setting", v: state.size_multiplier },
            { label: "Safety limit setting", v: state.risk_tightening_factor },
          ].map((m) => (
            <div key={m.label} style={{ marginBottom: 10 }}>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 12.5 }}>{m.label}</span>
                <span className="num muted" style={{ fontSize: 12 }}>{m.v.toFixed(2)}× of normal</span>
              </div>
              <Meter pct={m.v * 100} tone={m.v < 0.7 ? "red" : m.v < 0.95 ? "amber" : "green"} />
            </div>
          ))}
          <div className="faint" style={{ fontSize: 11, marginTop: 6 }}>
            A value of 1.00× means normal behaviour. Lower values mean the system has deliberately
            held itself back after disappointing results.
          </div>
        </Panel>
      )}

      <Panel title="What the system has learned so far"
        sub="Grouped by approach and market condition" flush>
        <DataTable
          columns={columns}
          rows={board}
          rowKey={(r) => `${r.strategy_tag}-${r.regime}`}
          minWidth={740}
          initialSort={{ key: "trades", dir: "desc" }}
          emptyTitle="No completed trades to learn from yet"
          emptyBody="Once trades finish and their results are known, the system records which approaches worked in which conditions and uses that when sizing future decisions."
        />
      </Panel>

      <Panel title="History of system adjustments" sub={`${adaptations.length} recorded`}>
        {adaptations.length === 0 ? (
          <Empty title="No adjustments recorded yet" />
        ) : (
          <div className="log">
            {adaptations.map((a) => {
              const [oc, os] = parseTriple(a.old_value);
              const [nc, ns] = parseTriple(a.new_value);
              const tightened = nc < oc;
              return (
                <div className="log-row" key={a.id}>
                  <span className="t">{fmtTime(a.timestamp)}</span>
                  <span className="kind-cell">
                    <Badge tone={tightened ? "amber" : "green"}>{tightened ? "Tightened" : "Eased"}</Badge>
                  </span>
                  <span className="msg">
                    {humanize(a.reasoning)}
                    <br />
                    <span className="faint" style={{ fontSize: 11 }}>
                      Confidence {oc.toFixed(2)}× → {nc.toFixed(2)}×, trade size {os.toFixed(2)}× → {ns.toFixed(2)}×
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
