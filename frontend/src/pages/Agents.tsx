import { useMemo, useState } from "react";
import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, PageHeader, DataTable, Meter } from "../components/ui";
import type { Column } from "../components/ui";
import type { DecisionRow } from "../types";
import { fmtCurrency, fmtTime, pnlTone } from "../utils/format";
import {
  AGENT_LABEL, AGENT_SCOPE, MARKET_LABEL, ASSET_NAME,
  actionInfo, verdictInfo, strategyLabel, regimeInfo, humanize,
} from "../utils/vocab";

const MARKETS = ["EQUITY", "FOREX", "COMMODITY"];

/**
 * Agents page.
 *
 * All six assets update every cycle, which makes it hard to follow any single
 * specialist while it is running. So this page has a focus mode: pick one
 * agent and every section below narrows to it, and optionally narrow again to
 * one of its assets. "All agents" restores the comparison view.
 */
export default function Agents() {
  const { latest, decisions } = useSystem();
  const [focus, setFocus] = useState<string>("ALL");
  const [asset, setAsset] = useState<string | null>(null);

  const focused = focus !== "ALL";

  /** Changing agent clears any asset narrowing, which belonged to the old agent. */
  const selectAgent = (m: string) => {
    setFocus((prev) => (prev === m ? "ALL" : m));
    setAsset(null);
  };

  const visibleMarkets = focused ? [focus] : MARKETS;

  const tableRows = useMemo(() => {
    let rows = decisions;
    if (focused) rows = rows.filter((d) => d.market_type === focus);
    if (asset) rows = rows.filter((d) => d.asset === asset);
    return rows;
  }, [decisions, focus, asset, focused]);

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
        actions={
          <div className="btn-group">
            <button className={`sm${!focused ? " on" : ""}`} onClick={() => { setFocus("ALL"); setAsset(null); }}>
              All agents
            </button>
            {MARKETS.map((m) => (
              <button key={m} className={`sm${focus === m ? " on" : ""}`} onClick={() => selectAgent(m)}>
                {MARKET_LABEL[m]}
              </button>
            ))}
          </div>
        }
      />

      {focused && (
        <div className="focus-bar">
          <span className="dot green pulse" />
          <span>
            Watching the <strong>{AGENT_LABEL[focus]}</strong> only
            {asset && <> · narrowed to <strong>{ASSET_NAME[asset] ?? asset}</strong></>}
          </span>
          <button className="sm spacer" onClick={() => { setFocus("ALL"); setAsset(null); }}>
            Show all agents
          </button>
        </div>
      )}

      {/* ---- agent summary cards (also the switcher) ---- */}
      <div className={focused ? "" : "grid-3"}>
        {visibleMarkets.map((m) => {
          const live = latest?.trace.filter((t) => t.market_type === m) ?? [];
          const acting = live.filter((t) => !["HOLD", "WAIT"].includes(t.proposal.action)).length;
          const mine = decisions.filter((d) => d.market_type === m);
          const evaluated = mine.filter((d) => d.outcome_status === "EVALUATED");
          const wins = evaluated.filter((d) => d.pnl > 0).length;

          return (
            <button
              type="button"
              className={`agent-card selectable${focus === m ? " selected" : ""}`}
              key={m}
              onClick={() => selectAgent(m)}
              title={focus === m ? "Show all agents" : `Focus on the ${AGENT_LABEL[m]}`}
            >
              <div className="agent-name">
                <span className={`dot ${latest ? "green pulse" : "gray"}`} />
                {AGENT_LABEL[m]}
                {focus === m && <Badge tone="green">Focused</Badge>}
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
            </button>
          );
        })}
      </div>

      {/* ---- what the agent(s) are looking at right now ---- */}
      {latest && (
        <Panel
          title={focused ? `What the ${AGENT_LABEL[focus]} is looking at right now` : "What each agent is looking at right now"}
          sub={focused ? "Click an asset to narrow further" : "Pick an agent above to see one at a time"}
        >
          <div className="stack">
            {visibleMarkets.map((m) => {
              const live = latest.trace.filter((t) => t.market_type === m);
              if (live.length === 0) return null;
              return (
                <div key={m}>
                  {!focused && (
                    <div className="row" style={{ gap: 8, marginBottom: 6 }}>
                      <strong style={{ fontSize: 12.5 }}>{AGENT_LABEL[m]}</strong>
                      <span className="faint" style={{ fontSize: 11 }}>{MARKET_LABEL[m]} markets</span>
                    </div>
                  )}
                  <div className={focused ? "stack" : "grid-2"}>
                    {live.map((t) => {
                      const act = actionInfo(t.proposal.action);
                      const reg = regimeInfo(t.regime ?? latest.overall_regime);
                      const isNarrowed = asset === t.asset;
                      const dimmed = focused && asset !== null && !isNarrowed;
                      return (
                        <button
                          type="button"
                          key={t.asset}
                          className={`asset-focus-card${isNarrowed ? " selected" : ""}${dimmed ? " dimmed" : ""}`}
                          onClick={() => focused && setAsset(isNarrowed ? null : t.asset)}
                          disabled={!focused}
                        >
                          <div className="row" style={{ gap: 8 }}>
                            <strong style={{ fontSize: 12.5 }}>{ASSET_NAME[t.asset] ?? t.asset}</strong>
                            <Badge tone={act.tone}>{act.label}</Badge>
                            <span className="spacer num faint" style={{ fontSize: 11 }}>
                              {(t.proposal.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>

                          <Meter pct={t.proposal.confidence * 100} tone={act.tone} />

                          <div className="row wrap" style={{ gap: 6, marginTop: 7 }}>
                            <Badge tone={reg.tone}>{reg.label}</Badge>
                            <span className="faint" style={{ fontSize: 11 }}>
                              {strategyLabel(t.proposal.strategy_tag)}
                            </span>
                          </div>

                          {focused && (
                            <>
                              <div className="sep" />
                              <div className="asset-reason">{humanize(t.proposal.reasoning)}</div>
                              {t.proposal.factors.length > 0 && (
                                <ul className="factor-list">
                                  {t.proposal.factors.slice(0, 3).map((f, i) => (
                                    <li key={i}>{humanize(f)}</li>
                                  ))}
                                </ul>
                              )}
                              <div className="kv">
                                <span className="k">Safety check</span>
                                <span className="v">
                                  <Badge tone={verdictInfo(t.risk_verdict.verdict).tone}>
                                    {verdictInfo(t.risk_verdict.verdict).label}
                                  </Badge>
                                </span>
                              </div>
                            </>
                          )}

                          {!focused && (
                            <div className="faint" style={{ fontSize: 11, marginTop: 6 }}>
                              {t.proposal.factors[0]}
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* ---- decision history ---- */}
      <Panel
        title={asset ? `${ASSET_NAME[asset] ?? asset} decisions` : focused ? `${AGENT_LABEL[focus]} decisions` : "Recent agent decisions"}
        sub={`${tableRows.length} recorded`}
        flush
      >
        <DataTable
          columns={columns}
          rows={tableRows.slice(0, 60)}
          rowKey={(r) => String(r.id)}
          minWidth={720}
          emptyTitle="No decisions recorded yet"
          emptyBody="Start the simulation and the agents will begin analysing the market."
        />
      </Panel>
    </div>
  );
}
