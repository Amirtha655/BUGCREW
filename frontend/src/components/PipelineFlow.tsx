import type { TraceEntry, DecisionRow } from "../types";
import { Badge } from "./ui";
import { fmtCurrency, fmtPct, fmtNum } from "../utils/format";
import { actionInfo, verdictInfo, regimeInfo, AGENT_LABEL, MARKET_LABEL, ASSET_NAME, strategyLabel, humanize } from "../utils/vocab";

interface Stage {
  stage: string;
  headline: string;
  detail?: string;
  tone?: string;
  badge?: string;
  pending?: boolean;
}

/**
 * Renders one decision as the sequence of steps the system actually took.
 * This is the clearest expression of the autonomous loop: every stage shown
 * here corresponds to a real backend component that ran for this decision.
 */
export function PipelineFlow({ entry, outcome }: { entry: TraceEntry; outcome?: DecisionRow | null }) {
  const act = actionInfo(entry.proposal.action);
  const verdict = verdictInfo(entry.risk_verdict.verdict);
  const regime = regimeInfo(entry.regime);
  const name = ASSET_NAME[entry.asset] ?? entry.asset;

  const move = entry.event.price_change_pct * 100;
  const eventHeadline = entry.event.news.length
    ? entry.event.news[0]
    : `${name} ${move >= 0 ? "up" : "down"} ${Math.abs(move).toFixed(2)}% at ${fmtNum(entry.event.price)}`;

  const stages: Stage[] = [
    {
      stage: "Market change",
      headline: eventHeadline,
      detail: `Conditions read as "${regime.label}". ${regime.explain}`,
      tone: regime.tone,
    },
    {
      stage: "Market identified",
      headline: MARKET_LABEL[entry.market_type] ?? entry.market_type,
      detail: "The router picks which specialist should handle this asset.",
      tone: "blue",
    },
    {
      stage: "Agent selected",
      headline: AGENT_LABEL[entry.market_type] ?? "Agent",
      detail: `Analysis approach: ${strategyLabel(entry.proposal.strategy_tag)}.`,
      tone: "blue",
    },
    {
      stage: "Analysis",
      headline: humanize(entry.proposal.factors[0] ?? "No strong signal found"),
      detail: humanize(entry.proposal.factors.slice(1).join(" · ")) || undefined,
      tone: "gray",
    },
    {
      stage: "Proposed action",
      headline: act.label,
      detail: `${act.explain} Confidence ${(entry.proposal.confidence * 100).toFixed(0)}%.`,
      badge: act.label,
      tone: act.tone,
    },
    {
      stage: "Safety check",
      headline: verdict.label,
      detail: humanize(entry.risk_verdict.reasons.join(" · ")) || verdict.explain,
      badge: verdict.label,
      tone: verdict.tone,
    },
    {
      stage: "Money assigned",
      headline: entry.allocation.final_allocation > 0 ? fmtCurrency(entry.allocation.final_allocation) : "None",
      detail:
        entry.allocation.final_allocation > 0
          ? humanize(entry.allocation.reasoning[0])
          : "No new money was committed for this decision.",
      tone: entry.allocation.final_allocation > 0 ? "blue" : "gray",
    },
    {
      stage: "Execution",
      headline: entry.execution.executed
        ? `${fmtNum(entry.execution.execution_quantity ?? 0, 3)} units at ${fmtNum(entry.execution.execution_price ?? 0)}`
        : "No trade placed",
      detail: entry.execution.executed
        ? `Simulated fill. Fee ${fmtCurrency(entry.execution.transaction_cost ?? 0, 2)}, price slippage ${((entry.execution.slippage_pct ?? 0) * 100).toFixed(3)}%.`
        : entry.execution.note,
      tone: entry.execution.executed ? "blue" : "gray",
    },
  ];

  if (outcome && outcome.outcome_status === "EVALUATED") {
    const good = outcome.pnl >= 0;
    stages.push({
      stage: "Result",
      headline: `${good ? "Gain" : "Loss"} of ${fmtCurrency(Math.abs(outcome.pnl), 2)}`,
      detail: `Expected ${fmtPct(outcome.expected_return_pct)}, actually ${fmtPct(outcome.actual_return_pct)}.`,
      tone: good ? "green" : "red",
    });
  } else if (entry.execution.executed) {
    stages.push({
      stage: "Result",
      headline: "Being monitored",
      detail: "The system checks back a few steps later to see how this trade actually performed.",
      tone: "gray",
      pending: true,
    });
  }

  return (
    <ol className="pipeline">
      {stages.map((s, i) => (
        <li key={i} className={s.pending ? "pending" : ""}>
          <span className={`node ${s.tone ?? "gray"}`} />
          <div className="pipeline-body">
            <div className="pipeline-stage">{s.stage}</div>
            <div className="pipeline-headline">
              {s.headline}
              {s.badge && <Badge tone={s.tone}>{s.badge}</Badge>}
            </div>
            {s.detail && <div className="pipeline-detail">{s.detail}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}
