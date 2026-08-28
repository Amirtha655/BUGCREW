import { useSystem } from "../state/SystemProvider";
import { Panel, Empty, PageHeader, DataTable, StatRow, StatTile } from "../components/ui";
import type { Column } from "../components/ui";
import { fmtCurrency, fmtPct, fmtPctPlain, pnlTone } from "../utils/format";
import { T, ASSET_NAME, assetTicker, MARKET_LABEL } from "../utils/vocab";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

interface Holding {
  asset: string;
  market: string;
  quantity: number;
  avgEntry: number;
  currentPrice: number;
  value: number;
  cost: number;
  pnl: number;
  pnlPct: number;
  share: number;
}

export default function Portfolio() {
  const { latest, history, status } = useSystem();
  const portfolio = latest?.portfolio;
  const start = status?.starting_capital ?? 100000;

  if (!portfolio) {
    return (
      <div className="page">
        <PageHeader title="Portfolio" description="What the system currently owns." />
        <Panel><Empty title="No portfolio data yet">Start the simulation to see holdings.</Empty></Panel>
      </div>
    );
  }

  const priceOf = (asset: string) =>
    latest?.trace.find((t) => t.asset === asset)?.event.price ?? 0;

  const holdings: Holding[] = Object.entries(portfolio.positions).map(([asset, pos]) => {
    const currentPrice = priceOf(asset) || pos.avg_entry_price;
    const value = pos.quantity * currentPrice;
    const cost = pos.quantity * pos.avg_entry_price;
    const pnl = value - cost;
    return {
      asset,
      market: latest?.trace.find((t) => t.asset === asset)?.market_type ?? "",
      quantity: pos.quantity,
      avgEntry: pos.avg_entry_price,
      currentPrice,
      value,
      cost,
      pnl,
      pnlPct: cost ? (pnl / cost) * 100 : 0,
      share: portfolio.portfolio_value ? (value / portfolio.portfolio_value) * 100 : 0,
    };
  });

  const totalPnl = portfolio.portfolio_value - start;
  const totalPnlPct = start ? (totalPnl / start) * 100 : 0;
  const unrealised = holdings.reduce((s, h) => s + h.pnl, 0);
  const investedPct = portfolio.portfolio_value ? (portfolio.total_exposure / portfolio.portfolio_value) * 100 : 0;

  const chartData = history.map((h) => ({ step: h.cycle, value: Math.round(h.portfolio.portfolio_value) }));

  const columns: Column<Holding>[] = [
    { key: "asset", header: "Asset", sortable: true, sortValue: (r) => r.asset,
      render: (r) => (
        <div>
          <div style={{ fontWeight: 600 }}>{ASSET_NAME[r.asset] ?? r.asset}</div>
          <div className="faint mono" style={{ fontSize: 11 }}>{assetTicker(r.asset)}</div>
        </div>
      ) },
    { key: "market", header: "Market", sortable: true, sortValue: (r) => r.market,
      render: (r) => <span className="muted">{MARKET_LABEL[r.market] ?? r.market}</span> },
    { key: "qty", header: "Units", align: "right", sortable: true, sortValue: (r) => r.quantity,
      render: (r) => <span className="num">{r.quantity.toFixed(3)}</span> },
    { key: "avg", header: "Bought at", align: "right", sortable: true, sortValue: (r) => r.avgEntry,
      render: (r) => <span className="num">{fmtCurrency(r.avgEntry, 2)}</span> },
    { key: "now", header: "Price now", align: "right", sortable: true, sortValue: (r) => r.currentPrice,
      render: (r) => <span className="num">{fmtCurrency(r.currentPrice, 2)}</span> },
    { key: "value", header: "Current value", align: "right", sortable: true, sortValue: (r) => r.value,
      render: (r) => <span className="num">{fmtCurrency(r.value)}</span> },
    { key: "pnl", header: "Gain / loss", align: "right", sortable: true, sortValue: (r) => r.pnl,
      render: (r) => (
        <span className={`num ${pnlTone(r.pnl)}`}>
          {r.pnl >= 0 ? "+" : ""}{fmtCurrency(r.pnl, 2)}
          <span style={{ fontSize: 11, marginLeft: 5, opacity: 0.85 }}>{fmtPct(r.pnlPct)}</span>
        </span>
      ) },
    { key: "share", header: "Share", align: "right", sortable: true, sortValue: (r) => r.share,
      render: (r) => <span className="num muted">{fmtPctPlain(r.share)}</span> },
  ];

  return (
    <div className="page">
      <PageHeader
        title="Portfolio"
        description="What the system owns right now, and how those holdings are performing."
      />

      <StatRow cols={5}>
        <StatTile term={T.portfolioValue} value={fmtCurrency(portfolio.portfolio_value)}
          delta={`${totalPnl >= 0 ? "+" : ""}${fmtCurrency(totalPnl)} (${fmtPct(totalPnlPct)})`}
          deltaTone={pnlTone(totalPnl)} />
        <StatTile term={T.availableCash} value={fmtCurrency(portfolio.cash)}
          note={`${fmtPctPlain(100 - investedPct)} of the portfolio`} />
        <StatTile term={T.amountInvested} value={fmtCurrency(portfolio.total_exposure)}
          note={`${fmtPctPlain(investedPct)} of the portfolio`} />
        <StatTile label="Unrealised Gain / Loss" value={<span className={pnlTone(unrealised)}>{unrealised >= 0 ? "+" : ""}{fmtCurrency(unrealised, 2)}</span>}
          note="On positions still open" />
        <StatTile label="Locked-in Gain / Loss" value={<span className={pnlTone(portfolio.realized_pnl)}>{portfolio.realized_pnl >= 0 ? "+" : ""}{fmtCurrency(portfolio.realized_pnl, 2)}</span>}
          note="From positions already closed" />
      </StatRow>

      <Panel title="Holdings" sub={`${holdings.length} open position${holdings.length === 1 ? "" : "s"}`} flush>
        <DataTable
          columns={columns}
          rows={holdings}
          rowKey={(r) => r.asset}
          minWidth={880}
          initialSort={{ key: "value", dir: "desc" }}
          emptyTitle="Nothing is currently held"
          emptyBody="All capital is sitting in cash. The system opens positions only when it finds an opportunity that passes the safety check."
        />
      </Panel>

      <Panel title="Portfolio value over time">
        {chartData.length < 2 ? (
          <Empty title="Chart builds as the system runs">Each point is one completed decision cycle.</Empty>
        ) : (
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={chartData} margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="2 3" vertical={false} />
              <XAxis dataKey="step" stroke="var(--text-faint)" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-faint)" fontSize={10} tickLine={false} axisLine={false}
                domain={["auto", "auto"]} width={62} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 4, fontSize: 12 }}
                labelStyle={{ color: "var(--text-faint)" }}
                formatter={(v) => [fmtCurrency(Number(v)), "Portfolio"]}
                labelFormatter={(l) => `Step ${l}`} />
              <ReferenceLine y={start} stroke="var(--text-faint)" strokeDasharray="3 3"
                label={{ value: "Starting capital", position: "insideTopLeft", fill: "var(--text-faint)", fontSize: 10 }} />
              <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={1.75} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Panel>
    </div>
  );
}
