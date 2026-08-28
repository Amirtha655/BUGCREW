import { useSystem } from "../state/SystemProvider";
import { Panel, Badge, PageHeader, DataTable, StatRow, StatTile, InfoLabel } from "../components/ui";
import type { Column } from "../components/ui";
import type { DecisionRow } from "../types";
import { fmtCurrency, fmtNum, fmtTime, pnlTone } from "../utils/format";
import { T, ASSET_NAME, actionInfo } from "../utils/vocab";

export default function Execution() {
  const { decisions } = useSystem();
  const trades = decisions.filter((d) => d.executed);

  const avgSlippage = trades.length
    ? trades.reduce((s, t) => s + t.slippage_pct, 0) / trades.length : 0;
  const totalFees = trades.reduce((s, t) => s + t.transaction_cost, 0);
  const totalTraded = trades.reduce((s, t) => s + t.execution_price * t.execution_quantity, 0);

  const columns: Column<DecisionRow>[] = [
    { key: "time", header: "Time", width: "78px", sortable: true, sortValue: (r) => r.timestamp,
      render: (r) => <span className="faint num" style={{ fontSize: 11 }}>{fmtTime(r.timestamp)}</span> },
    { key: "asset", header: "Asset", sortable: true, sortValue: (r) => r.asset,
      render: (r) => <span style={{ fontWeight: 600 }}>{ASSET_NAME[r.asset] ?? r.asset}</span> },
    { key: "action", header: "Action", sortable: true, sortValue: (r) => r.action,
      render: (r) => <Badge tone={actionInfo(r.action).tone}>{actionInfo(r.action).label}</Badge> },
    { key: "requested", header: "Requested", align: "right", sortable: true, sortValue: (r) => r.proposed_allocation,
      render: (r) => <span className="num muted">{r.proposed_allocation > 0 ? fmtCurrency(r.proposed_allocation) : "—"}</span> },
    { key: "used", header: "Actually used", align: "right", sortable: true, sortValue: (r) => r.final_allocation,
      render: (r) => <span className="num">{r.final_allocation > 0 ? fmtCurrency(r.final_allocation) : "—"}</span> },
    { key: "price", header: "Filled at", align: "right", sortable: true, sortValue: (r) => r.execution_price,
      render: (r) => <span className="num">{fmtCurrency(r.execution_price, 2)}</span> },
    { key: "units", header: "Units", align: "right", sortable: true, sortValue: (r) => r.execution_quantity,
      render: (r) => <span className="num">{fmtNum(r.execution_quantity, 3)}</span> },
    { key: "slip", header: <InfoLabel term={T.slippage} />, align: "right", sortable: true, sortValue: (r) => r.slippage_pct,
      render: (r) => <span className="num muted">{(r.slippage_pct * 100).toFixed(3)}%</span> },
    { key: "fee", header: <InfoLabel term={T.transactionCost} />, align: "right", sortable: true, sortValue: (r) => r.transaction_cost,
      render: (r) => <span className="num muted">{fmtCurrency(r.transaction_cost, 2)}</span> },
    { key: "status", header: "Status",
      render: (r) =>
        r.outcome_status === "EVALUATED" ? (
          <span className={`num ${pnlTone(r.pnl)}`}>{r.pnl >= 0 ? "+" : ""}{fmtCurrency(r.pnl, 2)}</span>
        ) : <Badge tone="blue">Monitoring</Badge> },
  ];

  return (
    <div className="page">
      <PageHeader
        title="Execution"
        description="Trades the system actually placed. These are simulated fills — the engine models a realistic price, a trading fee and a small gap between the intended and achieved price."
      />

      <div className="sim-banner">
        <b>SIMULATED FILLS</b>
        <span>No orders are sent to any exchange or broker. Prices, fees and slippage are modelled locally.</span>
      </div>

      <StatRow cols={4}>
        <StatTile label="Trades Placed" value={trades.length} note="Since this session began" />
        <StatTile label="Total Value Traded" value={fmtCurrency(totalTraded)} />
        <StatTile term={T.transactionCost} label="Fees Paid" value={fmtCurrency(totalFees, 2)} />
        <StatTile term={T.slippage} label="Average Slippage" value={`${(avgSlippage * 100).toFixed(3)}%`}
          note={avgSlippage < 0.002 ? "Good execution quality" : "Wider gaps in fast markets"} />
      </StatRow>

      <Panel title="Trade log" sub={`${trades.length} executed`} flush>
        <DataTable
          columns={columns}
          rows={trades.slice(0, 100)}
          rowKey={(r) => String(r.id)}
          minWidth={1020}
          emptyTitle="No trades placed yet"
          emptyBody="The system only trades when an opportunity passes the safety check. Proposals that were held, blocked or reduced to zero appear on the Decisions page."
        />
      </Panel>
    </div>
  );
}
