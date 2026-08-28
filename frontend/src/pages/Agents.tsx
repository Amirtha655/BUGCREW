import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, PageHeader, DataTable, StatRow, StatTile } from "../components/ui";
import type { Column } from "../components/ui";
import type { DecisionRow } from "../types";
import { fmtCurrency, fmtTime, pnlTone } from "../utils/format";
import {
  AGENT_LABEL, AGENT_SCOPE, MARKET_LABEL, ASSET_NAME,
  actionInfo, verdictInfo, strategyLabel,
} from "../utils/vocab";

const MARKETS = ["EQUITY", "FOREX", "COMMODITY"];

export default function Agents() {
  const { latest, decisions } = useSystem();

  const columns: Column<DecisionRow>[] = [
    { key: "time", header: "Time", width: "78px", render: (r) => <span className="faint num" style={{ fontSize: 11 }}>{fmtTime(r.timestamp)}</span> },
    {
      key: "asset", header: "Asset",
      render: (r) => <span style={{ fontWeight: 600 }}>{ASSET_NAME[r.asset] ?? r.asset}</span>,
    },
    {
      key: "action", header: "Proposed",
      render: (r) => <Badge tone={actionInfo(r.action).tone}>{actionInfo(r.action).label}</Badge>,
    },
    {
      key: "conf", header: "Confidence", align: "right",
      render: (r) => <span className="num">{(r.confidence * 100).toFixed(0)}%</span>,
    },
    {
      key: "verdict", header: "Safety Check",
      render: (r) => <Badge tone={verdictInfo(r.risk_verdict).tone}>{verdictInfo(r.risk_verdict).label}</Badge>,
    },
    {
      key: "result", header: "Result", align: "right",
      render: (r) =>
        r.outcome_status === "EVALUATED" ? (
          <span className={`num ${pnlTone(r.pnl)}`}>{r.pnl >= 0 ? "+" : ""}{fmtCurrency(r.pnl, 2)}</span>
        ) : r.executed ? (
          <span className="faint">Monitoring</span>
        ) : (
          <span className="faint">—</span>
        ),
    },
  ];

  return (
    <div className="page">
      <PageHeader
        title="Agents"
        description="The system does not use one general model. Each market type is handled by its own specialist, because the signals that matter in currencies are different from those in shares or commodities."
      />

      <div className="grid-3">
        {MARKETS.map((m) => {
          const live = latest?.trace.filter((t) => t.market_type === m) ?? [];
          const acting = live.filter((t) => !["HOLD", "WAIT"].includes(t.proposal.action)).length;
          const mine = decisions.filter((d) => d.market_type === m);
          const evaluated = mine.filter((d) => d.outcome_status === "EVALUATED");
          const wins = evaluated.filter((d) => d.pnl > 0).length;

          return (
            <div className="agent-card" key={m}>
              <div className="agent-name">
                <span className={`dot ${latest ? "green pulse" : "gray"}`} />
                {AGENT_LABEL[m]}
              </div>
              <div className="agent-scope">{AGENT_SCOPE[m]}</div>
              <div className="sep" />
              <div className="kv"><span className="k">Assets watched</span><span className="v">{live.length}</span></div>
              <div className="kv"><span className="k">Wants to act now</span><span className="v">{acting}</span></div>
              <div className="kv"><span className="k">Decisions made</span><span className="v">{mine.length}</span></div>
              <div className="kv">
                <span className="k">Completed trades</span>
                <span className="v">
                  {evaluated.length > 0 ? `${wins}/${evaluated.length} profitable` : "None yet"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {latest && (
        <Panel title="What each agent is looking at right now">
          <div className="stack">
            {MARKETS.map((m) => {
              const live = latest.trace.filter((t) => t.market_type === m);
              if (live.length === 0) return null;
              return (
                <div key={m}>
                  <div className="row" style={{ gap: 8, marginBottom: 6 }}>
                    <strong style={{ fontSize: 12.5 }}>{AGENT_LABEL[m]}</strong>
                    <span className="faint" style={{ fontSize: 11 }}>{MARKET_LABEL[m]} markets</span>
                  </div>
                  <StatRow cols={live.length}>
                    {live.map((t) => {
                      const act = actionInfo(t.proposal.action);
                      return (
                        <StatTile
                          key={t.asset}
                          label={ASSET_NAME[t.asset] ?? t.asset}
                          small
                          value={<Badge tone={act.tone}>{act.label}</Badge>}
                          note={
                            <>
                              {(t.proposal.confidence * 100).toFixed(0)}% confidence ·{" "}
                              {strategyLabel(t.proposal.strategy_tag)}
                              <br />
                              {t.proposal.factors[0]}
                            </>
                          }
                        />
                      );
                    })}
                  </StatRow>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      <Panel title="Recent agent decisions" sub={`${decisions.length} recorded`} flush>
        <DataTable
          columns={columns}
          rows={decisions.slice(0, 60)}
          rowKey={(r) => String(r.id)}
          minWidth={720}
          emptyTitle="No decisions recorded yet"
          emptyBody="Start the simulation and the agents will begin analysing the market."
        />
      </Panel>
    </div>
  );
}
