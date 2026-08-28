import { useState } from "react";
import { useSystem } from "../state/SystemProvider";
import { Panel, DataTable, Badge, Empty, PageHeader, InfoLabel, StatRow, StatTile } from "../components/ui";
import type { Column } from "../components/ui";
import type { TraceEntry } from "../types";
import { fmtPct, fmtNum, fmtCurrency, pnlTone } from "../utils/format";
import {
  T, MARKET_LABEL, ASSET_NAME, activityLevel, tradabilityLevel,
  systemStance, regimeInfo, actionInfo, AGENT_LABEL,
} from "../utils/vocab";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";

export default function Markets() {
  const { latest, decisions } = useSystem();
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [marketFilter, setMarketFilter] = useState<string>("ALL");

  if (!latest) {
    return (
      <div className="page">
        <PageHeader title="Markets" description="Every market the system is currently watching." />
        <Panel><Empty title="Waiting for the first market update">Start the simulation to see live market data.</Empty></Panel>
      </div>
    );
  }

  const rows = latest.trace.filter((t) => {
    if (marketFilter !== "ALL" && t.market_type !== marketFilter) return false;
    if (!query) return true;
    const q = query.toLowerCase();
    return t.asset.toLowerCase().includes(q) || (ASSET_NAME[t.asset] ?? "").toLowerCase().includes(q);
  });

  const columns: Column<TraceEntry>[] = [
    {
      key: "asset", header: "Asset", sortable: true, sortValue: (r) => r.asset,
      render: (r) => (
        <div>
          <div style={{ fontWeight: 600 }}>{ASSET_NAME[r.asset] ?? r.asset}</div>
          <div className="faint mono" style={{ fontSize: 11 }}>{r.asset}</div>
        </div>
      ),
    },
    {
      key: "market", header: "Market", sortable: true, sortValue: (r) => r.market_type,
      render: (r) => <span className="muted">{MARKET_LABEL[r.market_type] ?? r.market_type}</span>,
    },
    {
      key: "price", header: "Price", align: "right", sortable: true, sortValue: (r) => r.event.price,
      render: (r) => <span className="num">{fmtNum(r.event.price)}</span>,
    },
    {
      key: "change", header: "Change", align: "right", sortable: true, sortValue: (r) => r.event.price_change_pct,
      render: (r) => (
        <span className={`num ${pnlTone(r.event.price_change_pct)}`}>{fmtPct(r.event.price_change_pct * 100)}</span>
      ),
    },
    {
      key: "activity",
      header: <InfoLabel term={T.priceActivity} />,
      sortable: true, sortValue: (r) => r.event.volatility,
      render: (r) => {
        const a = activityLevel(r.event.volatility);
        return <Badge tone={a.tone}>{a.label}</Badge>;
      },
    },
    {
      key: "tradability",
      header: <InfoLabel term={T.tradability} />,
      sortable: true, sortValue: (r) => r.event.liquidity,
      render: (r) => {
        const l = tradabilityLevel(r.event.liquidity);
        return <Badge tone={l.tone}>{l.label}</Badge>;
      },
    },
    {
      key: "condition", header: "Condition", sortable: true, sortValue: (r) => r.regime,
      render: (r) => {
        const g = regimeInfo(r.regime);
        return <span className="muted">{g.label}</span>;
      },
    },
    {
      key: "stance", header: "System View", sortable: true, sortValue: (r) => r.proposal.action,
      render: (r) => {
        const s = systemStance(r.proposal.action, r.execution.executed);
        return <Badge tone={s.tone}>{s.label}</Badge>;
      },
    },
  ];

  const sel = selected ? latest.trace.find((t) => t.asset === selected) ?? null : null;

  return (
    <div className="page">
      <PageHeader
        title="Markets"
        description="Every market the system watches, with its own read on how each one is behaving. Select a row for detail."
      />

      <Panel
        title="Watchlist"
        sub={`${rows.length} of ${latest.trace.length} shown`}
        flush
        actions={
          <>
            <input
              type="search"
              placeholder="Search asset…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: 150 }}
            />
            <div className="btn-group">
              {["ALL", "EQUITY", "FOREX", "COMMODITY"].map((m) => (
                <button
                  key={m}
                  className={`sm${marketFilter === m ? " on" : ""}`}
                  onClick={() => setMarketFilter(m)}
                >
                  {m === "ALL" ? "All" : MARKET_LABEL[m]}
                </button>
              ))}
            </div>
          </>
        }
      >
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(r) => r.asset}
          onRowClick={(r) => setSelected(r.asset === selected ? null : r.asset)}
          selectedKey={selected}
          minWidth={860}
          emptyTitle="No assets match this filter"
        />
      </Panel>

      {sel && <MarketDetail entry={sel} history={decisions.filter((d) => d.asset === sel.asset).slice(0, 40)} />}
    </div>
  );
}

function MarketDetail({ entry, history }: { entry: TraceEntry; history: ReturnType<typeof useSystem>["decisions"] }) {
  const a = activityLevel(entry.event.volatility);
  const l = tradabilityLevel(entry.event.liquidity);
  const act = actionInfo(entry.proposal.action);
  const priceSeries = [...history].reverse().map((d) => ({ step: d.cycle_number, price: d.price }));

  return (
    <Panel
      title={ASSET_NAME[entry.asset] ?? entry.asset}
      sub={`${MARKET_LABEL[entry.market_type]} · handled by ${AGENT_LABEL[entry.market_type]}`}
      actions={<Badge tone={act.tone}>{act.label}</Badge>}
    >
      <StatRow cols={4}>
        <StatTile label="Price" value={fmtNum(entry.event.price)}
          delta={fmtPct(entry.event.price_change_pct * 100)} deltaTone={pnlTone(entry.event.price_change_pct)} />
        <StatTile term={T.priceActivity} value={<Badge tone={a.tone}>{a.label}</Badge>}
          note={`Measured at ${entry.event.volatility.toFixed(3)}`} />
        <StatTile term={T.tradability} value={<Badge tone={l.tone}>{l.label}</Badge>}
          note={`Measured at ${entry.event.liquidity.toFixed(2)}`} />
        <StatTile term={T.confidence} value={`${(entry.proposal.confidence * 100).toFixed(0)}%`}
          note={`Proposed: ${act.label}`} />
      </StatRow>

      {entry.event.news.length > 0 && (
        <>
          <div style={{ height: 12 }} />
          <div className="callout">
            <div className="callout-label">Market event</div>
            {entry.event.news.map((n, i) => <div key={i}>{n}</div>)}
          </div>
        </>
      )}

      <div style={{ height: 12 }} />
      <div className="grid-2">
        <div>
          <div className="callout-label" style={{ marginBottom: 6 }}>What the agent sees</div>
          <ul className="reasons">
            {entry.proposal.factors.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
        <div>
          <div className="callout-label" style={{ marginBottom: 6 }}>What could go wrong</div>
          <ul className="reasons">
            {entry.proposal.risk_factors.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      </div>

      {priceSeries.length > 1 && (
        <>
          <div className="sep" />
          <div className="callout-label" style={{ marginBottom: 6 }}>Recent price</div>
          <ResponsiveContainer width="100%" height={110}>
            <LineChart data={priceSeries} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <YAxis stroke="var(--text-faint)" fontSize={10} tickLine={false} axisLine={false} domain={["auto", "auto"]} width={54} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 4, fontSize: 12 }}
                formatter={(v) => [fmtCurrency(Number(v), 2), "Price"]}
                labelFormatter={(l2) => `Step ${l2}`}
              />
              <Line type="monotone" dataKey="price" stroke="var(--accent)" strokeWidth={1.75} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </Panel>
  );
}
