import { Link } from "react-router-dom";
import { useSystem } from "../state/SystemProvider";
import { Panel, StatRow, StatTile, Badge, Empty, PageHeader } from "../components/ui";
import { PipelineFlow } from "../components/PipelineFlow";
import { fmtCurrency, fmtPct, fmtPctPlain, fmtTime, pnlTone } from "../utils/format";
import { T, regimeInfo, actionInfo, ASSET_NAME, AGENT_LABEL, humanize } from "../utils/vocab";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

const KIND_TONE: Record<string, string> = {
  MARKET: "violet", AGENT: "blue", RISK: "amber",
  CAPITAL: "blue", EXECUTION: "green", OUTCOME: "gray", ADAPTATION: "amber", SYSTEM: "gray",
};

export default function Overview() {
  const { latest, history, status, activity, focus, decisions } = useSystem();

  const portfolio = latest?.portfolio;
  const start = status?.starting_capital ?? 100000;
  const pnl = portfolio ? portfolio.portfolio_value - start : 0;
  const pnlPct = start ? (pnl / start) * 100 : 0;
  const investedPct = portfolio && portfolio.portfolio_value
    ? (portfolio.total_exposure / portfolio.portfolio_value) * 100
    : 0;
  const regime = regimeInfo(latest?.overall_regime ?? "NORMAL");

  const chartData = history.map((h) => ({ step: h.cycle, value: Math.round(h.portfolio.portfolio_value) }));
  const recentActivity = activity.slice(-9).reverse();

  const focusOutcome = focus
    ? decisions.find((d) => d.asset === focus.asset && d.executed && d.outcome_status === "EVALUATED") ?? null
    : null;

  if (!latest) {
    return (
      <div className="page">
        <PageHeader
          title="Overview"
          description="Live status of the autonomous trading system."
        />
        <Panel>
          <Empty title="The system is not running yet">
            Open <Link to="/settings">Settings</Link> or use the simulation controls to choose a
            scenario and press Start. The system will then begin observing the market and making
            its own decisions.
          </Empty>
        </Panel>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        title="Overview"
        description="What the system is seeing, deciding and doing right now."
      />

      <div className="sim-banner">
        <b>PAPER TRADING</b>
        <span>Every trade shown here is simulated. No real money or real market orders are involved.</span>
      </div>

      <StatRow cols={5}>
        <StatTile term={T.portfolioValue} value={fmtCurrency(portfolio!.portfolio_value)}
          delta={`${pnl >= 0 ? "+" : ""}${fmtCurrency(pnl)} (${fmtPct(pnlPct)})`}
          deltaTone={pnlTone(pnl)} />
        <StatTile term={T.availableCash} value={fmtCurrency(portfolio!.cash)}
          note="Ready to invest" />
        <StatTile term={T.amountInvested} value={fmtCurrency(portfolio!.total_exposure)}
          note={`${portfolio!.open_position_count} open position${portfolio!.open_position_count === 1 ? "" : "s"}`} />
        <StatTile term={T.moneyAtRisk} value={fmtPctPlain(investedPct)}
          note={investedPct > 60 ? "High share invested" : investedPct > 30 ? "Moderate share invested" : "Conservative"} />
        <StatTile label="System Status"
          value={<span style={{ fontSize: 15 }}>{status?.emergency_stop ? "Halted" : status?.running ? "Running" : "Paused"}</span>}
          note={status?.emergency_stop ? "Emergency stop is on" : `Step ${latest.cycle}`} />
      </StatRow>

      <Panel
        title="Current Market Condition"
        sub={<>Technical term: market regime</>}
        actions={<Badge tone={regime.tone}>{regime.label}</Badge>}
      >
        <div style={{ fontSize: 13.5, lineHeight: 1.55 }}>{regime.explain}</div>
        <div className="sep" />
        <div className="row wrap" style={{ gap: 18 }}>
          {latest.trace.slice(0, 6).map((t) => (
            <div key={t.asset} style={{ minWidth: 108 }}>
              <div className="faint" style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                {ASSET_NAME[t.asset] ?? t.asset}
              </div>
              <div className="num" style={{ fontSize: 13.5, fontWeight: 600 }}>
                {t.event.price.toFixed(2)}{" "}
                <span className={pnlTone(t.event.price_change_pct)} style={{ fontSize: 11.5, fontWeight: 500 }}>
                  {fmtPct(t.event.price_change_pct * 100)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.15fr) minmax(0, 1fr)", gap: 14 }} className="ov-grid">
        <Panel
          title="Current Autonomous Decision"
          sub={focus ? `${ASSET_NAME[focus.asset] ?? focus.asset}` : undefined}
          actions={<Link to="/decisions"><button className="sm">Full history</button></Link>}
        >
          {focus ? (
            <>
              <StatRow cols={3}>
                <StatTile label="Handled by" small
                  value={<span style={{ fontSize: 13 }}>{AGENT_LABEL[focus.market_type]}</span>} />
                <StatTile label="Proposed action" small
                  value={<Badge tone={actionInfo(focus.proposal.action).tone}>{actionInfo(focus.proposal.action).label}</Badge>} />
                <StatTile term={T.confidence} small
                  value={`${(focus.proposal.confidence * 100).toFixed(0)}%`} />
              </StatRow>
              <div style={{ height: 12 }} />
              <PipelineFlow entry={focus} outcome={focusOutcome} />
              <div style={{ height: 12 }} />
              <div className="callout">
                <div className="callout-label">
                  Reasoning — {focus.proposal.ai_provider_used === "groq" ? "written by the language model" : "generated by the rule engine"}
                </div>
                {humanize(focus.proposal.reasoning)}
              </div>
            </>
          ) : (
            <Empty title="No decision yet">The system has not completed a decision cycle.</Empty>
          )}
        </Panel>

        <div className="stack">
          <Panel title="Portfolio Value" sub={`${chartData.length} step${chartData.length === 1 ? "" : "s"}`}>
            {chartData.length < 2 ? (
              <Empty title="Chart builds as the system runs">
                Each point is one completed decision cycle.
              </Empty>
            ) : (
              <ResponsiveContainer width="100%" height={148}>
                <LineChart data={chartData} margin={{ top: 5, right: 6, left: -14, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="2 3" vertical={false} />
                  <XAxis dataKey="step" stroke="var(--text-faint)" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-faint)" fontSize={10} tickLine={false} axisLine={false}
                    domain={["auto", "auto"]} width={58}
                    tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                  <Tooltip
                    contentStyle={{ background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 4, fontSize: 12 }}
                    labelStyle={{ color: "var(--text-faint)" }}
                    formatter={(v) => [fmtCurrency(Number(v)), "Portfolio"]}
                    labelFormatter={(l) => `Step ${l}`}
                  />
                  <ReferenceLine y={start} stroke="var(--text-faint)" strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={1.75} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
            <div className="faint" style={{ fontSize: 11, marginTop: 5 }}>
              Dotted line marks the starting capital of {fmtCurrency(start)}.
            </div>
          </Panel>

          <Panel
            title="Live Activity"
            actions={<Link to="/activity"><button className="sm">View all</button></Link>}
          >
            {recentActivity.length === 0 ? (
              <Empty title="No activity recorded yet">
                Events appear here as the system observes, decides and acts.
              </Empty>
            ) : (
              <div className="log">
                {recentActivity.map((e) => (
                  <div className="log-row" key={e.id}>
                    <span className="t">{fmtTime(e.timestamp)}</span>
                    <span className="kind-cell"><Badge tone={KIND_TONE[e.kind]}>{e.kind}</Badge></span>
                    <span className="msg">{e.message}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      <style>{`
        @media (max-width: 1150px) {
          .ov-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
