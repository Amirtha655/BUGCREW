import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, Empty, PageHeader, DataTable, StatRow, StatTile, Meter, InfoLabel } from "../components/ui";
import type { Column } from "../components/ui";
import type { DecisionRow } from "../types";
import { fmtCurrency, fmtPctPlain, fmtTime } from "../utils/format";
import { T, ASSET_NAME, verdictInfo, actionInfo, humanize } from "../utils/vocab";

export default function Risk() {
  const { latest, status, decisions } = useSystem();
  const limits = status?.risk_limits;
  const portfolio = latest?.portfolio;

  const interventions = decisions.filter((d) => d.risk_verdict !== "APPROVE");

  const columns: Column<DecisionRow>[] = [
    { key: "time", header: "Time", width: "78px",
      render: (r) => <span className="faint num" style={{ fontSize: 11 }}>{fmtTime(r.timestamp)}</span> },
    { key: "asset", header: "Asset",
      render: (r) => <span style={{ fontWeight: 600 }}>{ASSET_NAME[r.asset] ?? r.asset}</span> },
    { key: "action", header: "AI proposed",
      render: (r) => (
        <span>
          <Badge tone={actionInfo(r.action).tone}>{actionInfo(r.action).label}</Badge>{" "}
          <span className="num muted">{r.proposed_allocation > 0 ? fmtCurrency(r.proposed_allocation) : ""}</span>
        </span>
      ) },
    { key: "verdict", header: "Safety check",
      render: (r) => <Badge tone={verdictInfo(r.risk_verdict).tone}>{verdictInfo(r.risk_verdict).label}</Badge> },
    { key: "final", header: "Allowed", align: "right",
      render: (r) => <span className="num">{r.final_allocation > 0 ? fmtCurrency(r.final_allocation) : "Nothing"}</span> },
    { key: "reason", header: "Reason",
      render: (r) => <span className="muted" style={{ fontSize: 12 }}>{humanize(r.risk_reasons.split("; ")[0])}</span> },
  ];

  const investedPct = portfolio && portfolio.portfolio_value
    ? (portfolio.total_exposure / portfolio.portfolio_value) * 100 : 0;
  const maxInvestedPct = (limits?.max_portfolio_exposure_pct ?? 0.8) * 100;
  const usagePct = maxInvestedPct ? (investedPct / maxInvestedPct) * 100 : 0;

  const sessionPnlPct = portfolio && status
    ? ((portfolio.portfolio_value - status.starting_capital) / status.starting_capital) * 100 : 0;
  const lossLimitPct = (limits?.max_daily_loss_pct ?? 0.05) * 100;
  const lossUsedPct = sessionPnlPct < 0 ? Math.min(100, (Math.abs(sessionPnlPct) / lossLimitPct) * 100) : 0;

  return (
    <div className="page">
      <PageHeader
        title="Risk Controls"
        description="The AI can propose anything. It cannot act on its own. Every proposal is checked here first against fixed safety rules, and this check can shrink a trade or refuse it outright."
      />

      <Panel title="How this works">
        <div className="ba">
          <div className="ba-card">
            <div className="ba-label">Step 1 — The AI proposes</div>
            <div className="ba-value" style={{ fontSize: 13.5 }}>An agent suggests a trade</div>
            <div className="ba-note">Based on its reading of prices, news and past performance. This is only a suggestion.</div>
          </div>
          <div className="ba-arrow">→</div>
          <div className="ba-card">
            <div className="ba-label">Step 2 — The safety check decides</div>
            <div className="ba-value" style={{ fontSize: 13.5 }}>Approve, reduce, or block</div>
            <div className="ba-note">Fixed rules written in code, not by the AI. The AI has no way to overrule or bypass them.</div>
          </div>
        </div>
      </Panel>

      {limits && (
        <Panel title="Safety limits currently in force">
          <StatRow cols={5}>
            <StatTile term={T.maxSingleTrade} value={fmtCurrency(limits.max_single_trade)} />
            <StatTile term={T.maxAssetExposure} value={fmtPctPlain(limits.max_asset_exposure_pct * 100, 0)}
              note="of portfolio, per asset" />
            <StatTile term={T.maxPortfolioExposure} value={fmtPctPlain(limits.max_portfolio_exposure_pct * 100, 0)} />
            <StatTile term={T.maxDailyLoss} value={fmtPctPlain(limits.max_daily_loss_pct * 100, 0)}
              note="then new buying stops" />
            <StatTile term={T.minLiquidity} value={limits.min_liquidity_score.toFixed(2)}
              note="below this, no buying" />
          </StatRow>
        </Panel>
      )}

      {portfolio && limits && (
        <div className="grid-2">
          <Panel title="How much of the allowance is being used">
            <div style={{ marginBottom: 14 }}>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 12.5 }}>
                  <InfoLabel term={T.moneyAtRisk} override="Share of money invested" />
                </span>
                <span className="num" style={{ fontSize: 12.5 }}>
                  {fmtPctPlain(investedPct)} of {fmtPctPlain(maxInvestedPct, 0)} allowed
                </span>
              </div>
              <Meter pct={usagePct} tone={usagePct > 85 ? "red" : usagePct > 60 ? "amber" : "green"} />
            </div>

            <div>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 12.5 }}>
                  <InfoLabel term={T.maxDailyLoss} override="Loss allowance used" />
                </span>
                <span className="num" style={{ fontSize: 12.5 }}>
                  {lossUsedPct > 0 ? `${lossUsedPct.toFixed(0)}% used` : "None used"}
                </span>
              </div>
              <Meter pct={lossUsedPct} tone={lossUsedPct > 80 ? "red" : lossUsedPct > 50 ? "amber" : "green"} />
              <div className="faint" style={{ fontSize: 11, marginTop: 4 }}>
                If the session loses {fmtPctPlain(lossLimitPct, 0)}, the system stops opening new positions.
              </div>
            </div>
          </Panel>

          <Panel title="Money committed per asset" sub="Each must stay under the single-asset limit">
            {Object.keys(portfolio.exposure_by_asset).length === 0 ? (
              <Empty title="Nothing invested right now">All capital is currently held as cash.</Empty>
            ) : (
              Object.entries(portfolio.exposure_by_asset).map(([asset, value]) => {
                const pct = portfolio.portfolio_value ? (value / portfolio.portfolio_value) * 100 : 0;
                const cap = limits.max_asset_exposure_pct * 100;
                const used = cap ? (pct / cap) * 100 : 0;
                return (
                  <div key={asset} style={{ marginBottom: 11 }}>
                    <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12.5 }}>{ASSET_NAME[asset] ?? asset}</span>
                      <span className="num muted" style={{ fontSize: 12 }}>
                        {fmtCurrency(value)} · {fmtPctPlain(pct)} of {fmtPctPlain(cap, 0)}
                      </span>
                    </div>
                    <Meter pct={used} tone={used > 100 ? "amber" : "blue"} />
                  </div>
                );
              })
            )}
            {Object.entries(portfolio.exposure_by_asset).some(
              ([, v]) => portfolio.portfolio_value && (v / portfolio.portfolio_value) * 100 > limits.max_asset_exposure_pct * 100
            ) && (
              <div className="faint" style={{ fontSize: 11, marginTop: 8, lineHeight: 1.5 }}>
                One holding is above its limit. The limit is applied when a trade is placed, so a
                position can drift above it afterwards if its price rises. The system will not buy
                more of it, but it does not force a sale purely to get back under the line.
              </div>
            )}
          </Panel>
        </div>
      )}

      <Panel
        title="Times the safety check stepped in"
        sub={`${interventions.length} intervention${interventions.length === 1 ? "" : "s"}`}
        flush
      >
        <DataTable
          columns={columns}
          rows={interventions.slice(0, 60)}
          rowKey={(r) => String(r.id)}
          minWidth={860}
          emptyTitle="No interventions yet"
          emptyBody="Every proposal so far has been within the safety limits. When one is not, it will be shown here with the reason."
        />
      </Panel>
    </div>
  );
}
