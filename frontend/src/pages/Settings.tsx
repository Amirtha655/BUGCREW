import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, PageHeader, StatRow, StatTile } from "../components/ui";
import { SimulationControls } from "../components/SimulationControls";
import { fmtCurrency, fmtPctPlain } from "../utils/format";
import { T } from "../utils/vocab";

export default function Settings() {
  const { status, latest, busy, control } = useSystem();
  const limits = status?.risk_limits;
  const stopped = status?.emergency_stop ?? false;
  const usingLLM = latest?.trace.some((t) => t.proposal.ai_provider_used === "groq") ?? false;

  return (
    <div className="page">
      <PageHeader
        title="Settings"
        description="Simulation controls, safety limits and system configuration."
      />

      <div className="grid-2">
        <SimulationControls />

        <div className="stack">
          <Panel
            title="Emergency Stop"
            actions={<Badge tone={stopped ? "red" : "green"}>{stopped ? "Active" : "Off"}</Badge>}
          >
            <p style={{ margin: "0 0 11px", fontSize: 12.5, lineHeight: 1.55 }}>
              Immediately blocks the system from opening any new position, whatever the agents
              propose. Positions already held can still be closed, so the system can exit safely
              rather than being frozen into a losing trade.
            </p>
            <button
              className={stopped ? "primary" : "danger"}
              disabled={busy}
              onClick={() => control.emergencyStop(!stopped)}
            >
              {stopped ? "Resume normal operation" : "Activate emergency stop"}
            </button>
          </Panel>

          <Panel title="Decision engine">
            <div className="kv">
              <span className="k">Numeric decisions</span>
              <span className="v">Rule-based scoring engine</span>
            </div>
            <div className="kv">
              <span className="k">Written explanations</span>
              <span className="v">
                {usingLLM ? "Groq language model" : "Built-in templates"}
              </span>
            </div>
            <div className="kv">
              <span className="k">Configured provider</span>
              <span className="v mono">{status?.ai_provider ?? "—"}</span>
            </div>
            <p style={{ margin: "11px 0 0", fontSize: 12, lineHeight: 1.55, color: "var(--text-muted)" }}>
              The language model never chooses the action, the confidence or the amount of money.
              Those are computed by deterministic code so every decision is reproducible and can be
              audited. The model only turns that finished decision into readable English. If it is
              unavailable, the system falls back to built-in wording and keeps running.
            </p>
          </Panel>
        </div>
      </div>

      {limits && (
        <Panel title="Safety limits" sub="Enforced by the risk check on every proposal">
          <StatRow cols={4}>
            <StatTile term={T.maxSingleTrade} value={fmtCurrency(limits.max_single_trade)} />
            <StatTile term={T.maxAssetExposure} value={fmtPctPlain(limits.max_asset_exposure_pct * 100, 0)} />
            <StatTile term={T.maxPortfolioExposure} value={fmtPctPlain(limits.max_portfolio_exposure_pct * 100, 0)} />
            <StatTile term={T.maxDailyLoss} value={fmtPctPlain(limits.max_daily_loss_pct * 100, 0)} />
          </StatRow>
          <div style={{ height: 12 }} />
          <StatRow cols={4}>
            <StatTile term={T.minLiquidity} value={limits.min_liquidity_score.toFixed(2)} />
            <StatTile label="Most Positions at Once" value={limits.max_position_count} />
            <StatTile label="High Activity Threshold" value={limits.high_volatility_threshold.toFixed(3)}
              note="Above this, trades are halved" />
            <StatTile label="Crisis Threshold" value={limits.crisis_volatility_threshold.toFixed(3)}
              note="Above this, buying stops" />
          </StatRow>
          <p style={{ margin: "12px 0 0", fontSize: 12, lineHeight: 1.55, color: "var(--text-muted)" }}>
            These values are configured in the backend and are deliberately not editable from the
            interface — the point of the safety check is that the trading system cannot loosen its
            own limits.
          </p>
        </Panel>
      )}

      <Panel title="About this system">
        <div className="kv"><span className="k">Mode</span><span className="v">Paper trading simulation</span></div>
        <div className="kv"><span className="k">Starting capital</span><span className="v">{fmtCurrency(status?.starting_capital ?? 0)}</span></div>
        <div className="kv"><span className="k">Decision cycle</span><span className="v">Every {status?.cycle_interval_seconds ?? 4}s while running</span></div>
        <div className="kv"><span className="k">Steps completed</span><span className="v">{status?.cycle ?? 0}</span></div>
        <p style={{ margin: "12px 0 0", fontSize: 12, lineHeight: 1.55, color: "var(--text-muted)" }}>
          All market data is simulated locally. No connection is made to any exchange, broker or
          market data provider, and no real money is involved at any point.
        </p>
      </Panel>
    </div>
  );
}
